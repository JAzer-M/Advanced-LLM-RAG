# 固定 RAG 的规则化补查：按论文来源覆盖和局部证据入选情况决定是否再检索。
# 它会实际检索/重排，但不调用 LLM 判断事实缺口；与 agent.py 的语义诊断分开。
# complete_evidence 返回 (最终证据, 逐轮轨迹)，补查轮数有上限且可提前停止。

"""Bounded source-scoped evidence completion; no generation or Gold input."""
from copy import deepcopy
import re
import time
from pathlib import Path

from src.bm25_retriever import retrieve_bm25
from src.hybrid_retriever import reciprocal_rank_fusion
from src.reranker import rerank_results, select_evidence
from src.retriever import retrieve


# 只从库中已有标题/文件名推导明确别名，供来源路由使用，不凭空识别新论文。
def named_sources(query, chunks):
    """Recognize only unambiguous names derivable from existing paper metadata."""
    papers = {c['source']: c.get('title', '') for c in chunks}
    aliases = {}
    stop_words = {'a', 'an', 'the', 'for', 'of', 'and', 'in', 'with', 'to', 'on'}
    for source, title in papers.items():
        words = [w for w in re.findall(r'[A-Za-z]+', title) if w.lower() not in stop_words]
        names = {title, title.split(':')[0]}
        names.update(''.join(w[0] for w in words[:n]) for n in (2, 3, 4) if len(words) >= n)
        stem = Path(source).stem
        if not re.fullmatch(r'\d{4}\.\d{4,5}v\d+', stem):
            names.add(stem)
        for name in names:
            if len(name.strip()) >= 2:
                aliases.setdefault(name.strip().casefold(), set()).add(source)
    matches = []
    for name, sources in aliases.items():
        if len(sources) == 1:
            match = re.search(r'(?<![\w-])' + re.escape(name) + r'(?![\w-])', query, re.I)
            if match:
                matches.append((match.start(), -len(name), next(iter(sources))))
    return list(dict.fromkeys(source for _, _, source in sorted(matches)))


# 生成来源覆盖任务，区分局部证据不足和候选已有但未入选；当前只处理明确跨篇题。
def plan_evidence_gap(query, global_ranking, local_evidence, selected, chunks, top_k):
    """Coverage signals are diagnostic heuristics, not proof of semantic support."""
    sources = named_sources(query, chunks)
    plan = {'requested_sources': sources, 'tasks': [], 'coverage': 'heuristic_only'}
    if len(sources) < 2:
        return plan
    source_by_id = {c['chunk_id']: c['source'] for c in chunks}
    selected_ids = {c['chunk_id'] for c in selected}
    tasks = []
    for item in local_evidence:
        matches = [s for s in named_sources(item['query'], chunks) if s in sources]
        if len(matches) == 1:
            tasks.append({'query': item['query'], 'source': matches[0], 'top_ids': item['top_ids']})
    for source in sources:
        if not any(t['source'] == source for t in tasks):
            tasks.append({'query': query, 'source': source, 'top_ids': []})
    seen = set()
    for task in tasks:
        key = task['source'], task['query']
        if key in seen:
            continue
        seen.add(key)
        matched = [cid for cid in task['top_ids'] if source_by_id[cid] == task['source']]
        retained = [cid for cid in matched if cid in selected_ids]
        excluded = [c['chunk_id'] for c in global_ranking[:top_k]
                    if c['source'] == task['source'] and c['chunk_id'] not in selected_ids]
        plan['tasks'].append({**task, 'source_matched_top_ids': matched,
                              'selected_top_ids': retained, 'excluded_global_ids': excluded,
                              'needs_retrieval': len(matched) < 2 or len(retained) < 2})
    plan['truncated_tasks'] = max(0, len(plan['tasks']) - 4)
    plan['tasks'] = plan['tasks'][:4]
    return plan


# 保留基线已入选的局部证据，再按任务检索并在同一最终 K 内重新选择。
def complete_evidence(query, global_ranking, local_evidence, retrieval_anchor_ids,
                      embedding_model, index, chunks, bm25, reranker_model,
                      top_k=10, candidate_k=60, max_rounds=1):
    """Deepen the same scoped searches for up to three passes, with early stops."""
    if max_rounds not in (1, 2, 3):
        raise ValueError('max_rounds must be 1, 2 or 3')
    started = time.perf_counter()
    baseline = select_evidence(global_ranking, local_evidence, top_k, retrieval_anchor_ids)
    local_ids = {cid for item in local_evidence for cid in item['top_ids']}
    retained_local_ids = [c['chunk_id'] for c in baseline if c['chunk_id'] in local_ids]
    trace = plan_evidence_gap(query, global_ranking, local_evidence, baseline, chunks, top_k)
    trace.update(rounds=0, supplement_queries=0, max_rounds=max_rounds,
                 completed_passes=0, round_history=[],
                 selected_ids_before=[c['chunk_id'] for c in baseline],
                 retained_local_ids=retained_local_ids)
    tasks = trace['tasks']
    if not tasks or not any(t['needs_retrieval'] or t['excluded_global_ids'] for t in tasks):
        trace.update(stop_reason='not_explicit_cross_paper' if not tasks else 'no_coverage_signal',
                     selected_ids_after=trace['selected_ids_before'],
                     elapsed_seconds=round(time.perf_counter() - started, 6))
        return baseline, trace

    source_counts = {}
    for chunk in chunks:
        source_counts[chunk['source']] = source_counts.get(chunk['source'], 0) + 1
    seen_searches = set()
    all_new_ids = []
    selected = baseline
    for round_index in range(1, max_rounds + 1):
        pass_started = time.perf_counter()
        # 后轮只加深同批任务的候选深度，最终 top_k 保持不变。
        depth = candidate_k * round_index
        if round_index > 1 and all((t['query'], t['source'], min(depth, source_counts[t['source']]))
                                   in seen_searches for t in tasks):
            trace['stop_reason'] = 'repeated_search_plan'
            break
        candidates = {c['chunk_id']: c for c in global_ranking}
        identities = {(c['source'], c['page'], c['text']): c for c in global_ranking}
        pass_queries = 0
        for task in tasks:
            effective_depth = min(depth, source_counts[task['source']])
            signature = task['query'], task['source'], effective_depth
            task['effective_depth'] = effective_depth
            task['search_performed'] = False
            if (task['needs_retrieval'] or round_index > 1) and signature not in seen_searches:
                # 先在完整返回列表里筛选目标论文，再截断候选，避免目标来源被其他论文挤掉。
                # Exact small-corpus search; filter the paper BEFORE truncating.
                dense = retrieve(embedding_model, index, chunks, task['query'], top_k=len(chunks))
                sparse = retrieve_bm25(bm25, chunks, task['query'], top_k=len(chunks))
                scoped_dense = [c for c in dense if c['source'] == task['source']][:effective_depth]
                scoped_sparse = [c for c in sparse if c['source'] == task['source']][:effective_depth]
                scoped = reciprocal_rank_fusion(scoped_dense, scoped_sparse, top_k=effective_depth)
                seen_searches.add(signature)
                pass_queries += 1
                task['retrieved_ids'] = [c['chunk_id'] for c in scoped]
                task['search_performed'] = True
            elif signature in seen_searches:
                continue
            else:
                scoped = [c for c in global_ranking if c['source'] == task['source']][:depth]
            canonical = []
            for chunk in scoped:
                key = chunk['source'], chunk['page'], chunk['text']
                chunk = identities.setdefault(key, chunk)
                candidates.setdefault(chunk['chunk_id'], chunk)
                if chunk['chunk_id'] not in {c['chunk_id'] for c in canonical}:
                    canonical.append(chunk)
            task['scoped_top_ids'] = [c['chunk_id'] for c in rerank_results(
                task['query'], canonical, reranker_model, top_k=3, include_source=True)]

        existing_ids = {c['chunk_id'] for c in global_ranking}
        new_candidates = [c for cid, c in candidates.items() if cid not in existing_ids]
        new_ranking = rerank_results(query, new_candidates, reranker_model,
                                     top_k=len(new_candidates), include_source=True)
        merged = sorted([*global_ranking, *new_ranking], key=lambda c: -c['rerank_score'])
        scoped_evidence = [{'query': t['query'], 'top_ids': t['scoped_top_ids']} for t in tasks]
        selected = select_evidence(merged, [*local_evidence, *scoped_evidence], top_k,
                                   retrieval_anchor_ids, protected_ids=retained_local_ids)
        new_ids = [c['chunk_id'] for c in new_candidates]
        all_new_ids.extend(new_ids)
        trace['rounds'] += bool(pass_queries)
        trace['supplement_queries'] += pass_queries
        trace['round_history'].append({
            'round': round_index, 'candidate_depth': depth, 'supplement_queries': pass_queries,
            'new_candidate_ids': new_ids, 'merged_candidate_ids': [c['chunk_id'] for c in merged],
            'selected_ids': [c['chunk_id'] for c in selected], 'tasks': deepcopy(tasks),
            'elapsed_seconds': round(time.perf_counter() - pass_started, 6)})
        trace['completed_passes'] += 1
        global_ranking = merged
        trace.update(merged_candidate_ids=[c['chunk_id'] for c in merged],
                     new_candidate_ids=all_new_ids,
                     selected_ids_after=[c['chunk_id'] for c in selected])
        # 第二轮起没有新增候选就停止；重复有效计划也会在本轮检索前提前停止。
        if round_index > 1 and not new_ids:
            trace['stop_reason'] = 'no_new_candidates'
            break
    else:
        trace['stop_reason'] = ('single_round_budget_exhausted' if trace['rounds'] else
                                'selection_repaired_without_search') if max_rounds == 1 else 'round_budget_exhausted'
    trace['elapsed_seconds'] = round(time.perf_counter() - started, 6)
    return selected, trace


# 兼容旧的一轮入口；实际实现复用上方有界循环。
def complete_evidence_once(query, global_ranking, local_evidence, retrieval_anchor_ids,
                           embedding_model, index, chunks, bm25, reranker_model,
                           top_k=10, candidate_k=60):
    """Keep the original one-pass entry point and budget for existing callers."""
    return complete_evidence(query, global_ranking, local_evidence, retrieval_anchor_ids,
                             embedding_model, index, chunks, bm25, reranker_model,
                             top_k=top_k, candidate_k=candidate_k, max_rounds=1)
