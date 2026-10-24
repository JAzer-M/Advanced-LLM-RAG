import argparse
import hashlib
import json
import re
import time
import unicodedata
from pathlib import Path

from sentence_transformers import CrossEncoder

from evaluation.metrics import (
    average_precision_at_k,
    mean_average_precision_at_k,
    mean_reciprocal_rank_at_k,
    normalized_precision_at_k,
    overall_normalized_precision_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
)

from src.bm25_retriever import build_bm25_index, retrieve_bm25
import src.api_llm as api
from src.embedding import load_embedding_model
from src.evidence_gap import complete_evidence
from src.hybrid_retriever import reciprocal_rank_fusion
from src.knowledge_base import load_knowledge_base
from src.query_rewriter import rewrite_query
from src.query_decomposer import decompose_query
from src.reranker import rank_evidence, rerank_results, select_evidence
from src.retriever import retrieve


# ============================================================
# 1. Experiment configuration
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

QUESTIONS_PATH = PROJECT_DIR / "evaluation" / "questions.json"

FINAL_K = 10
CANDIDATE_K = 120
RRF_K = 60
RRF_TOP_K = 120

ENABLE_REWRITING = True
ENABLE_DECOMPOSITION = True

RERANKER_NAME = "BAAI/bge-reranker-base"
RERANKER_DEVICE = "cpu"


# ============================================================
# 2. Gold evidence and result ID utilities
# ============================================================

def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).lower().strip()


def get_gold_chunk_ids(question, chunks):
    """Map each (source, page, exact quote) to matching chunk IDs."""

    gold_ids = set()
    unmatched_quotes = []

    for evidence in question["gold_evidence"]:

        matches = []

        for index, chunk in enumerate(chunks):

            if (
                chunk["source"] == evidence["source"]
                and chunk["page"] == evidence["page"]
                and normalize_text(evidence["quote"])
                in normalize_text(chunk["text"])
            ):
                matches.append(chunk.get("chunk_id", index))

        if matches:
            gold_ids.update(matches)

        else:
            unmatched_quotes.append(evidence["quote"])

    return gold_ids, unmatched_quotes


def get_result_ids(results, candidates=None):
    """Preserve ranking; recover IDs if the reranker dropped chunk_id."""

    ids = []

    for result in results:

        if "chunk_id" in result:
            ids.append(result["chunk_id"])
            continue

        matches = [
            candidate["chunk_id"]
            for candidate in (candidates or [])
            if candidate["source"] == result["source"]
            and candidate["page"] == result["page"]
            and candidate["text"] == result["text"]
        ]

        if len(matches) != 1:
            raise ValueError("Cannot uniquely identify reranked chunk")

        ids.append(matches[0])

    return ids


def deduplicate_results(results):
    """
    Remove duplicate chunks while preserving their first occurrence.

    Use the same source/page/text identity as the main pipeline.
    """

    unique_results = []
    seen = set()

    for result in results:

        key = (result['source'], result['page'], result['text'])

        if key not in seen:
            seen.add(key)
            unique_results.append(result)

    return unique_results


# ============================================================
# 3. Retrieval helpers
# ============================================================

def retrieve_two_ways(
        query,
        embedding_model,
        index,
        chunks,
        bm25
):
    dense = retrieve(
        model=embedding_model,
        index=index,
        chunks=chunks,
        query=query,
        top_k=CANDIDATE_K,
    )

    sparse = retrieve_bm25(
        bm25=bm25,
        chunks=chunks,
        query=query,
        top_k=CANDIDATE_K,
    )

    return dense, sparse


def fuse_and_rerank(
        query,
        dense,
        sparse,
        reranker_model,
        extra_results=None
):
    """
    RRF first; rerank against the user's ORIGINAL question.
    """

    fused = reciprocal_rank_fusion(
        dense_results=dense,
        bm25_results=sparse,
        k=RRF_K,
        top_k=RRF_TOP_K,
        extra_results=extra_results,
    )

    reranked = rerank_results(
        query=query,
        candidates=fused,
        model=reranker_model,
        top_k=len(fused),
    )

    return fused, reranked


def decomposition_retrieve_and_rerank(
        query,
        decomposition,
        original_fused,
        embedding_model,
        index,
        chunks,
        bm25,
        reranker_model
):
    """
    Query Decomposition experiment.

    Strategy:

    Original Query
        -> Dense + BM25 -> RRF
        -> candidate pool

    Each Sub-Query
        -> Dense + BM25 -> RRF
        -> candidate pool

    Then deduplicate, rank globally and locally, and use the same
    evidence selection functions as main.py. Keep the global ranking
    available as a separate legacy control.
    """

    # 如果不需要 decomposition，
    # 直接使用原始 Hybrid + Reranker 的结果。
    if not decomposition["needs_decomposition"]:

        return (
            original_fused,
            None,
            None,
            None,
        )

    candidate_pool = list(original_fused)

    sub_query_details = []

    print("\n=== Query Decomposition Retrieval ===")

    for i, sub_query in enumerate(
        decomposition["sub_queries"],
        start=1
    ):

        print(f"\nSub-Query {i}: {sub_query}")

        sub_dense, sub_bm25 = retrieve_two_ways(
            sub_query,
            embedding_model,
            index,
            chunks,
            bm25,
        )

        sub_fused = reciprocal_rank_fusion(
            dense_results=sub_dense,
            bm25_results=sub_bm25,
            k=RRF_K,
            top_k=RRF_TOP_K,
        )

        candidate_pool.extend(sub_fused)

        sub_query_details.append({
            "query": sub_query,
            "dense": sub_dense,
            "bm25": sub_bm25,
            "rrf": sub_fused,
        })

        print(
            "Sub-Query RRF Top-5 IDs:",
            get_result_ids(sub_fused[:5])
        )

    print(
        "\nDecomposition Candidate Pool Before Deduplication:",
        len(candidate_pool)
    )

    unique_candidates = deduplicate_results(candidate_pool)

    print(
        "Decomposition Candidate Pool After Deduplication:",
        len(unique_candidates)
    )

    global_ranking, sub_query_evidence = rank_evidence(
        query, unique_candidates,
        [{'query': item['query'], 'results': item['rrf']} for item in sub_query_details],
        reranker_model)
    retrieval_anchor_ids = get_result_ids(original_fused[:1])
    reranked = select_evidence(global_ranking, sub_query_evidence, FINAL_K, retrieval_anchor_ids)

    return (
        unique_candidates,
        reranked,
        {**decomposition, 'global_ranking': global_ranking,
         'sub_query_evidence': sub_query_evidence,
         'retrieval_anchor_ids': retrieval_anchor_ids},
        sub_query_details,
    )


# ============================================================
# 4. Metrics and reporting
# ============================================================

def evaluate_retrieval(retrieved_ids, gold_ids, k=None):
    k = FINAL_K if k is None else k

    return {
        "precision": precision_at_k(
            retrieved_ids,
            gold_ids,
            k
        ),

        "normalized_precision": normalized_precision_at_k(retrieved_ids, gold_ids, k),

        "recall": recall_at_k(
            retrieved_ids,
            gold_ids,
            k
        ),

        "ap": average_precision_at_k(
            retrieved_ids,
            gold_ids,
            k
        ),

        "rr": reciprocal_rank_at_k(
            retrieved_ids,
            gold_ids,
            k
        ),
    }


def summarize_results(cases, k):
    if not cases:
        return {'questions': 0}
    return {'questions': len(cases),
            'precision': sum(precision_at_k(r, g, k) for r, g in cases) / len(cases),
            'normalized_precision': overall_normalized_precision_at_k(cases, k),
            'recall': sum(recall_at_k(r, g, k) for r, g in cases) / len(cases),
            'map': mean_average_precision_at_k(cases, k),
            'mrr': mean_reciprocal_rank_at_k(cases, k)}


def print_overall_metrics(name, cases, k=None):
    k = FINAL_K if k is None else k

    if not cases:

        print(f"\n=== Overall {name} Evaluation ===")
        print("No valid test cases")
        return

    mean_precision = sum(
        precision_at_k(
            retrieved,
            gold,
            k
        )
        for retrieved, gold in cases
    ) / len(cases)

    mean_recall = sum(
        recall_at_k(
            retrieved,
            gold,
            k
        )
        for retrieved, gold in cases
    ) / len(cases)

    print(f"\n=== Overall {name} Evaluation ===")

    print(
        "Evaluated Questions:",
        len(cases)
    )

    print(
        f"Mean Precision@{k}: "
        f"{mean_precision:.4f}"
    )

    print(
        f"Overall Normalized Precision@{k}: "
        f"{overall_normalized_precision_at_k(cases, k):.4f}"
    )

    print(
        f"Mean Recall@{k}: "
        f"{mean_recall:.4f}"
    )

    print(
        f"MAP@{k}: "
        f"{mean_average_precision_at_k(cases, k):.4f}"
    )

    print(
        f"MRR@{k}: "
        f"{mean_reciprocal_rank_at_k(cases, k):.4f}"
    )


def record_results(
        methods,
        gold_ids,
        test_cases,
        k=None
):
    k = FINAL_K if k is None else k

    for name, retrieved_ids in methods.items():

        scores = evaluate_retrieval(
            retrieved_ids,
            gold_ids,
            k
        )

        test_cases[name].append(
            (
                retrieved_ids,
                gold_ids
            )
        )

        print(f"\n=== {name} ===")

        print(
            "Retrieved IDs:",
            retrieved_ids
        )

        print(
            f"Precision@{k}: "
            f"{scores['precision']:.4f}"
        )

        print(
            f"Normalized Precision@{k}: "
            f"{scores['normalized_precision']:.4f}"
        )

        print(
            f"Recall@{k}: "
            f"{scores['recall']:.4f}"
        )

        print(
            f"AP@{k}: "
            f"{scores['ap']:.4f}"
        )

        print(
            f"RR@{k}: "
            f"{scores['rr']:.4f}"
        )


# ============================================================
# 5. Main evaluation
# ============================================================

def auxiliary_queries(question, cache, calls, output_dir):
    """Cache query transformations; neither Gold nor answers enter prompts."""
    qid, query = question['id'], question['question']
    if cache is not None:
        saved = cache.get(qid)
        if saved is None or saved['query'] != query:
            raise ValueError(f'Auxiliary cache does not match question {qid}')
        return saved
    original_chat = api.chat_completion

    def audited_chat(prompt, *args, **kwargs):
        call = {'question_id': qid, 'prompt': prompt}
        calls.append(call)
        started = time.perf_counter()
        try:
            response = original_chat(prompt, *args, **kwargs)
            call['response'] = response
            return response
        except Exception as exc:
            call['error'] = f'{type(exc).__name__}: {exc}'
            if isinstance(exc, api.IncompleteResponseError):
                call['response'] = exc.response
            raise
        finally:
            call['elapsed_seconds'] = round(time.perf_counter() - started, 3)
            if output_dir:
                (output_dir / 'api_calls.json').write_text(
                    json.dumps(calls, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    try:
        api.chat_completion = audited_chat
        decomposition = decompose_query(query)
        rewritten = rewrite_query(query).strip() or query
        return {'query': query, 'decomposition': decomposition, 'rewritten_query': rewritten}
    finally:
        api.chat_completion = original_chat


def query_mode_name(mode, cap):
    return f'Pipeline {mode} ({cap} rounds)'


def evaluate_query_modes(query, auxiliary, dense, sparse, base_fused, base_ranking,
                         local_evidence, sub_details, base_completion, completion_caps,
                         embedding, index, chunks, bm25, reranker, top_k=None):
    """Replay main.py's optional query lists, retaining real passages as evidence.

    Decomposed queries are identical in all four modes. Their complete RRF lists
    enter every candidate pool, so their local Top-3 rankings can be reused.
    Gold is deliberately absent from this interface.
    """
    top_k = FINAL_K if top_k is None else top_k
    anchors = get_result_ids(base_fused[:1])
    rewritten = auxiliary['rewritten_query']
    rewrite_lists = list(retrieve_two_ways(rewritten, embedding, index, chunks, bm25)) if (
        rewritten and rewritten != query) else []
    hyde_results = retrieve(embedding, index, chunks, auxiliary['hypothetical_document'], top_k=CANDIDATE_K)
    methods, traces = {}, {}
    for mode, extra in [('base', []), ('rewrite', rewrite_lists), ('hyde', [hyde_results]),
                         ('both', [*rewrite_lists, hyde_results])]:
        started = time.perf_counter()
        fused = base_fused if mode == 'base' else reciprocal_rank_fusion(
            dense, sparse, k=RRF_K, top_k=RRF_TOP_K, extra_results=extra)
        candidates = deduplicate_results([*fused, *(c for item in (sub_details or []) for c in item['rrf'])])
        ranking = base_ranking if mode == 'base' else rerank_results(
            query, candidates, reranker, top_k=len(candidates))
        selected = select_evidence(ranking, local_evidence, top_k, anchors)
        methods[query_mode_name(mode, 0)] = get_result_ids(selected)
        completion = None
        if completion_caps:
            if mode == 'base':
                completion = base_completion
            else:
                _, completion = complete_evidence(
                    query, ranking, local_evidence, anchors, embedding, index, chunks, bm25, reranker,
                    top_k=top_k, candidate_k=CANDIDATE_K, max_rounds=max(completion_caps))
            for cap in completion_caps:
                history = [r for r in completion['round_history'] if r['round'] <= cap]
                methods[query_mode_name(mode, cap)] = history[-1]['selected_ids'] if history else get_result_ids(selected)
        traces[mode] = {'top_k': top_k, 'rrf_ids': get_result_ids(fused), 'candidate_ids': get_result_ids(candidates),
                        'global_ranking_ids': get_result_ids(ranking), 'retrieval_anchor_ids': anchors,
                        'selected_ids_before': get_result_ids(selected), 'evidence_completion': completion,
                        'mode_processing_seconds': round(time.perf_counter() - started, 6)}
    return methods, traces


def main():
    global FINAL_K, CANDIDATE_K, RRF_TOP_K, ENABLE_REWRITING, ENABLE_DECOMPOSITION
    parser = argparse.ArgumentParser(description='按当前或指定知识库版本评价检索。')
    parser.add_argument('--kb-version')
    parser.add_argument('--questions', type=Path, default=QUESTIONS_PATH,
                        help='题目 JSON；默认保留已有六题')
    parser.add_argument('--top-k', type=int, nargs='+', default=[10],
                        help='最终证据条数，可同时对比 5 10 20；默认 10')
    parser.add_argument('--candidate-k', type=int, default=120,
                        help='每路检索和 RRF 候选预算；默认与主流程相同为 120')
    parser.add_argument('--output-dir', type=Path, help='保存逐题指标、阶段排名及辅助查询')
    parser.add_argument('--auxiliary-cache', type=Path, help='复用同一问题的分解/改写，不调用 API')
    parser.add_argument('--no-auxiliary', action='store_true', help='禁用分解/改写，只评估原问题')
    parser.add_argument('--complete-evidence', action='store_true',
                        help='额外评估限定论文的补检索；各 top-k 独立选证据，原方法保留')
    parser.add_argument('--completion-rounds', type=int, nargs='+', choices=(1, 2, 3), default=[1],
                        help='补查轮数上限，例如 1 3；一次运行复用同一轮次轨迹')
    parser.add_argument('--query-ablation', action='store_true',
                        help='追加主流程对齐的 base/rewrite/HyDE/both 对照；须用含 HyDE 的冻结缓存')
    args = parser.parse_args()
    ks = sorted(set(args.top_k))
    if min(ks) <= 0 or args.candidate_k < max(ks):
        parser.error('top-k 必须大于零，candidate-k 必须不小于最大 top-k。')
    if not args.complete_evidence and args.completion_rounds != [1]:
        parser.error('completion-rounds 需要同时指定 --complete-evidence。')
    FINAL_K, CANDIDATE_K, RRF_TOP_K = max(ks), args.candidate_k, args.candidate_k
    ENABLE_REWRITING = ENABLE_DECOMPOSITION = not args.no_auxiliary
    questions = json.loads(args.questions.read_text(encoding='utf-8'))
    if len({q['id'] for q in questions}) != len(questions):
        parser.error('题目 ID 不能重复。')
    cache = json.loads(args.auxiliary_cache.read_text(encoding='utf-8')) if args.auxiliary_cache else None
    if args.query_ablation:
        if args.no_auxiliary or cache is None:
            parser.error('query-ablation 需要 auxiliary-cache 并启用辅助查询。')
        for question in questions:
            if not question.get('gold_evidence'):
                continue
            saved = cache.get(question['id'], {})
            if (saved.get('query') != question['question'] or not isinstance(saved.get('rewritten_query'), str)
                    or not isinstance(saved.get('hypothetical_document'), str)
                    or not saved['hypothetical_document'].strip()):
                parser.error(f"查询增强缓存不完整：{question['id']}")
    if cache is not None and not args.no_auxiliary:
        for question in questions:
            if question.get('gold_evidence') and (question['id'] not in cache
                    or cache[question['id']]['query'] != question['question']):
                parser.error(f"辅助查询缓存与题目不匹配：{question['id']}")
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if (args.output_dir / 'results.json').exists():
            parser.error('结果目录已有 results.json；请使用新目录保留旧结果。')
    started = time.perf_counter()
    index, chunks, knowledge_base = load_knowledge_base(PROJECT_DIR / 'data/processed', args.kb_version)
    tracked = [Path(__file__), PROJECT_DIR / 'main.py', args.questions,
               PROJECT_DIR / 'evaluation/metrics.py', *sorted((PROJECT_DIR / 'src').glob('*.py')),
               *(Path(knowledge_base[key]) for key in ('index_path', 'chunks_path'))]
    if knowledge_base['manifest_path']:
        tracked.append(Path(knowledge_base['manifest_path']))
    if args.auxiliary_cache:
        tracked.append(args.auxiliary_cache)
    report = {'status': 'running', 'knowledge_base': knowledge_base,
              'configuration': {'top_k': ks, 'candidate_k': CANDIDATE_K, 'rrf_k': RRF_K,
                                'auxiliary_enabled': not args.no_auxiliary,
                                'auxiliary_cache': str(args.auxiliary_cache) if args.auxiliary_cache else None,
                                'evidence_completion_enabled': args.complete_evidence,
                                'completion_rounds': sorted(set(args.completion_rounds)),
                                'query_ablation': args.query_ablation,
                                'normalized_precision': 'Per question H/min(K,G); aggregate sum(H)/sum(min(K,G)); no-Gold skipped',
                                'scoring': 'Original Gold chunks and metric formulas; no answers or LLM judge'},
              'input_sha256': {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked},
              'questions': [], 'api_calls': [], 'metrics': {}}
    generated_auxiliary = {}

    def save_report():
        if args.output_dir:
            (args.output_dir / 'results.json').write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    anchor_name = 'Hybrid + Reranker + RRF Anchor'
    names = ['Dense', 'BM25', 'Hybrid', 'Hybrid + Reranker', anchor_name]
    coverage_name = 'Decomposition + Hybrid + Reranker'
    no_anchor_name = 'Decomposition + Coverage (no RRF anchor)'
    legacy_name = 'Decomposition + Global Reranker (legacy)'
    if not args.no_auxiliary:
        names += ['Rewritten Hybrid + Reranker', 'Multi-Query + Reranker', coverage_name,
                  no_anchor_name, legacy_name]
    completion_names = {cap: 'Evidence Completion (one round)' if cap == 1 else
                         f'Evidence Completion (up to {cap} rounds)'
                         for cap in sorted(set(args.completion_rounds))}
    if args.complete_evidence:
        names.extend(completion_names.values())
    if args.query_ablation:
        names.extend(query_mode_name(mode, cap) for mode in ('base', 'rewrite', 'hyde', 'both')
                     for cap in ([0, *completion_names] if args.complete_evidence else [0]))
    test_cases = {k: {name: [] for name in names} for k in ks}
    save_report()
    print('Questions:', args.questions, 'Knowledge Base:', knowledge_base['version'])
    print('Candidate budget:', CANDIDATE_K, 'Final evidence budgets:', ks)
    try:
        embedding = load_embedding_model()
        bm25 = build_bm25_index(chunks)
        reranker = CrossEncoder(RERANKER_NAME, device=RERANKER_DEVICE)
        for question in questions:
            qid, query = question['id'], question['question']
            print('\nQuestion ID:', qid, 'Question:', query, flush=True)
            if not question.get('gold_evidence'):
                report['questions'].append({'id': qid, 'status': 'skipped_no_gold'})
                save_report()
                print('No Gold: skipped, not counted as correct.')
                continue
            gold_ids, unmatched = get_gold_chunk_ids(question, chunks)
            if unmatched or not gold_ids:
                raise ValueError(f'Incomplete Gold mapping for {qid}: {unmatched}')
            auxiliary = auxiliary_queries(question, cache, report['api_calls'], args.output_dir) if (
                not args.no_auxiliary) else {'query': query,
                    'decomposition': {'needs_decomposition': False, 'sub_queries': []},
                    'rewritten_query': query}
            generated_auxiliary[qid] = auxiliary
            if args.output_dir:
                (args.output_dir / 'auxiliary.json').write_text(
                    json.dumps(generated_auxiliary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            question_started = time.perf_counter()
            dense, sparse = retrieve_two_ways(query, embedding, index, chunks, bm25)
            fused, ranking = fuse_and_rerank(query, dense, sparse, reranker)
            methods = {'Dense': get_result_ids(dense), 'BM25': get_result_ids(sparse),
                       'Hybrid': get_result_ids(fused), 'Hybrid + Reranker': get_result_ids(ranking)}
            stages = {'dense': dense, 'bm25': sparse, 'rrf': fused, 'global_reranker': ranking}
            info, details = None, []
            if not args.no_auxiliary:
                candidates, selected, info, details = decomposition_retrieve_and_rerank(
                    query, auxiliary['decomposition'], fused, embedding, index, chunks, bm25, reranker)
                if info:
                    methods[coverage_name] = get_result_ids(selected)
                    methods[legacy_name] = get_result_ids(info['global_ranking'])
                    stages.update(decomposition_pool=candidates,
                                  decomposition_global=info['global_ranking'])
                else:
                    methods[coverage_name] = methods[legacy_name] = get_result_ids(ranking)
                rewritten = auxiliary['rewritten_query']
                if rewritten == query:
                    rewrite_ranking = multi_ranking = ranking
                else:
                    rd, rb = retrieve_two_ways(rewritten, embedding, index, chunks, bm25)
                    _, rewrite_ranking = fuse_and_rerank(query, rd, rb, reranker)
                    _, multi_ranking = fuse_and_rerank(query, dense, sparse, reranker, extra_results=[rd, rb])
                methods['Rewritten Hybrid + Reranker'] = get_result_ids(rewrite_ranking)
                methods['Multi-Query + Reranker'] = get_result_ids(multi_ranking)
            completions_by_k = {}
            extra_methods_by_k = {k: {} for k in ks}
            if args.complete_evidence:
                for k in ks:
                    completed, completion = complete_evidence(
                        query, info['global_ranking'] if info else ranking,
                        info['sub_query_evidence'] if info else [], get_result_ids(fused[:1]),
                        embedding, index, chunks, bm25, reranker,
                        top_k=k, candidate_k=CANDIDATE_K, max_rounds=max(completion_names))
                    completions_by_k[str(k)] = completion
                    for cap, method_name in completion_names.items():
                        checkpoints = [r for r in completion['round_history'] if r['round'] <= cap]
                        extra_methods_by_k[k][method_name] = checkpoints[-1]['selected_ids'] if checkpoints else get_result_ids(completed)
            entry = {'id': qid, 'query': query, 'status': 'completed', 'gold_ids': sorted(gold_ids),
                     'auxiliary': auxiliary, 'retrieval_seconds': round(time.perf_counter() - question_started, 3),
                     'stage_ids': {name: get_result_ids(items) for name, items in stages.items()},
                     'stage_gold_ranks': {name: {str(g): next((i for i,c in enumerate(items,1)
                                                              if c['chunk_id']==g), None) for g in sorted(gold_ids)}
                                          for name,items in stages.items()},
                     'sub_query_evidence': info['sub_query_evidence'] if info else [],
                     'subquery_stages': [{'query': item['query'],
                                          'ids': {name: get_result_ids(item[name]) for name in ('dense','bm25','rrf')}}
                                         for item in (details or [])], 'metrics_by_k': {}}
            if completions_by_k:
                entry['evidence_completion_by_k'] = completions_by_k
                entry['evidence_completion'] = completions_by_k[str(FINAL_K)]
            if args.query_ablation:
                mode_traces_by_k = {}
                for k in ks:
                    augmented_methods, mode_traces = evaluate_query_modes(
                        query, auxiliary, dense, sparse, fused,
                        info['global_ranking'] if info else ranking,
                        info['sub_query_evidence'] if info else [], details, completions_by_k.get(str(k)),
                        list(completion_names) if args.complete_evidence else [],
                        embedding, index, chunks, bm25, reranker, top_k=k)
                    extra_methods_by_k[k].update(augmented_methods)
                    mode_traces_by_k[str(k)] = mode_traces
                entry['query_modes_by_k'] = mode_traces_by_k
                entry['query_modes'] = mode_traces_by_k[str(FINAL_K)]
            for k in ks:
                methods_k = {name: ids[:k] for name,ids in methods.items()}
                methods_k.update(extra_methods_by_k[k])
                anchor_ids = get_result_ids(fused[:1])
                methods_k[anchor_name] = get_result_ids(select_evidence(ranking, [], k, anchor_ids))
                if info:
                    methods_k[coverage_name] = get_result_ids(select_evidence(
                        info['global_ranking'], info['sub_query_evidence'], k, anchor_ids))
                    methods_k[no_anchor_name] = get_result_ids(select_evidence(
                        info['global_ranking'], info['sub_query_evidence'], k))
                elif not args.no_auxiliary:
                    methods_k[coverage_name] = methods_k[anchor_name]
                    methods_k[no_anchor_name] = get_result_ids(ranking[:k])
                print(f'\n=== Final evidence budget: {k} ===')
                record_results(methods_k, gold_ids, test_cases[k], k)
                entry['metrics_by_k'][str(k)] = {name: {'retrieved_ids': ids,
                    **evaluate_retrieval(ids, gold_ids, k)} for name,ids in methods_k.items()}
            report['questions'].append(entry)
            save_report()
        for k,cases_by_method in test_cases.items():
            report['metrics'][str(k)] = {}
            for name,cases in cases_by_method.items():
                print_overall_metrics(name, cases, k)
                report['metrics'][str(k)][name] = summarize_results(cases, k)
        report['status'] = 'completed'
    except Exception as exc:
        report.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        report['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        report['api_call_count'] = len(report['api_calls'])
        report['usage'] = {key: sum((call.get('response', {}).get('usage') or {}).get(key, 0)
                                   for call in report['api_calls'])
                           for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
        report['inputs_unchanged'] = all(hashlib.sha256(Path(name).read_bytes()).hexdigest() == sha
                                         for name,sha in report['input_sha256'].items())
        save_report()


if __name__ == '__main__':
    main()
