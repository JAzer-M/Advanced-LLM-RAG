# 阅读入口：命令行默认auto；Python main默认rag保留历史评估接口，mode可显式选择。
# Auto先走原RAG回答；明确缺口/引用失败再升级Agent，常规问题没有额外门控调用。
# _run_pipeline共用检索，_answer_with_agent复用agent.py；Agent运行单独留档。

"""Main entry point for the Advanced-LLM-RAG pipeline.

Current pipeline:
PDF chunks -> Dense + BM25 -> RRF -> optional query rewrite / HyDE /
query-decomposition retrieval -> deduplication -> Cross-Encoder reranking
-> evidence ledger + original context -> fixed RAG generation or bounded Agent/review.

Note:
- USE_HYDE is disabled based on the latest ON/OFF evaluation.
- Sub-query Top-3 evidence is prioritized within the same final Top-10 budget;
  the original RRF first hit is retained as a retrieval anchor, and final
  passages keep their original-query global order.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time

from sentence_transformers import CrossEncoder

from src import api_llm as api
from src.api_llm import generate_final_answer, load_settings
from src.bm25_retriever import build_bm25_index, retrieve_bm25
from src.citation_validation import repair_citations_once
from src.embedding import load_embedding_model
from src.evidence_gap import complete_evidence as supplement_evidence
from src.evidence_gap import named_sources
from src.hybrid_retriever import reciprocal_rank_fusion
from src.hyde import generate_hypothetical_document
from src.grounded_evidence import build_ledger, render_complete, render_guidance
from src.knowledge_base import load_knowledge_base
from src.query_decomposer import decompose_query
from src.query_rewriter import rewrite_query
from src.reranker import rank_evidence, select_evidence
from src.retriever import retrieve


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# This branch generates one rewritten query, then runs Dense + BM25 retrieval.
# The name is retained to avoid breaking evaluation scripts that import it.
USE_MULTI_QUERY = False

# Disabled because the latest production-aligned ON/OFF evaluation showed
# no meaningful overall retrieval improvement.
USE_HYDE = False

# User-selected bounded completion; coverage signals still control whether it runs.
USE_EVIDENCE_COMPLETION = True

# 候选 120、最终证据 10、子题局部 3 是不同预算；RRF_K=60 是秩平滑常数。
RETRIEVAL_TOP_K = 120
RRF_TOP_K = 120
RERANK_TOP_K = 10
SUB_QUERY_EVIDENCE_K = 3
RRF_K = 60

RERANKER_MODEL_NAME = "BAAI/bge-reranker-base"
RERANKER_DEVICE = "cpu"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def print_ranked_results(results, title, limit=None):
    """Print retrieved chunks in rank order."""
    displayed_results = results if limit is None else results[:limit]
    print(f"\n=== {title} ===")

    for rank, result in enumerate(displayed_results, start=1):
        print(f"\nRank: {rank}")
        print(f"Source: {result.get('source', 'Unknown')}")
        print(f"Page: {result.get('page', 'Unknown')}")
        print(f"Section: {result.get('section', 'None')}")
        print(f"Text: {result.get('text', '')}")


# 按来源、页码、正文去重；同一原文从多路检索命中时沿用首次出现的身份。
def deduplicate_candidates(candidates):
    """Deduplicate chunks while preserving their first-seen order."""
    unique_candidates = []
    seen = set()

    for result in candidates:
        key = (
            result["source"],
            result["page"],
            result["text"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique_candidates.append(result)

    return unique_candidates

# 这里的 [1]/[2] 是当前上下文的引用序号，不能当成库内 chunk_id。
def build_context(results):
    """Build a numbered context so the LLM can cite retrieved chunks."""
    context_parts = []

    for rank, result in enumerate(results, start=1):
        context_parts.append(
            f"[{rank}] Source: {result['source']} | "
            f"Page: {result['page']} | "
            f"Section: {result.get('section', 'None')}\n"
            + (f"Title: {result['title']}\n" if result.get('title')
               and result['title'].strip().casefold() not in result['source'].casefold() else '')
            + f"{result['text']}"
        )

    return "\n\n".join(context_parts)


# 生成提示将原文和作答约束交给 API；下方字符串是实际提示，修改会改变模型输入。
def build_prompt(query, context):
    """Create the grounded-answer prompt with citation requirements."""
    return (
        "You are an AI research assistant.\n\n"
        "Answer the user's question based only on the provided context.\n\n"
        "Rules:\n"
        "1. Do not invent information or introduce unsupported claims.\n"
        "2. Place citations immediately after the claims they support.\n"
        "3. Cite only context chunks that directly support each claim.\n"
        "4. Every citation must directly support the exact claim it follows. "
        "Mentioning the same topic is not sufficient evidence.\n"
        "5. Do not combine separate statements into a causal relationship "
        "unless the source explicitly establishes that relationship.\n"
        "6. Do not attribute technical claims to a paper unless the context "
        "directly supports those claims.\n"
        "7. If a claim cannot be directly supported, omit it or clearly state "
        "that the evidence is insufficient.\n"
        "8. Keep the answer focused on the question.\n\n"
        "9. A source filename identifies the document, not necessarily the model "
        "described in a passage. Check named subjects and the cited surrounding text.\n"
        "10. Evidence guidance supplements the original passages. Subject hints "
        "are rule-based; check them against the sources. For kernel H x W x C, "
        "H x W is the spatial size and C is channels per kernel; a kernel count "
        "is not a spatial size. Preserve layer numbers and configuration qualifiers.\n\n"
        "11. Respond in Simplified Chinese unless the question explicitly requests "
        "another language. Keep technical names in their original form.\n"
        "12. For unsupported parts of the question, state the missing evidence "
        "concisely. Do not substitute measurements from other hardware, datasets "
        "or settings, or append unrelated facts to a refusal. For an entirely "
        "unsupported Chinese question, begin with 当前证据不足 and explain what is missing "
        "in only one or two sentences, without any supplementary measurements.\n"
        "13. Answer only the scope actually requested. Missing unasked details "
        "are not grounds for an insufficiency warning. When the requested main "
        "facts are supported, answer them directly.\n"
        "14. Prioritize explicit subquestions, correct facts and citations, and "
        "conditions/units that change the conclusion. Add definitions or steps only "
        "when needed for the task. Optional background, stylistic preferences and "
        "unasked exceptions are not completeness requirements. Failure to retrieve "
        "a paper does not establish that the paper never reported a result.\n\n"
        "15. For a comparison, synthesize separately supported facts about the "
        "requested objects, citing each side. A literal sentence comparing both "
        "papers is NOT required. Different purposes, inputs or mechanisms can be "
        "contrasted from their respective descriptions. This does not establish "
        "causality or which method performs better. Do not call the comparison "
        "unsupported merely because no head-to-head experiment is provided.\n"
        "16. Lead with the main difference the user asked about. For a broad "
        "comparison, explain what each object does and its supported core approach; "
        "do not replace this with differences between versions of each object, "
        "benchmark tables or unasked numerical results.\n\n"
        f"Context:\n{context}\n\n"
        f"Question:\n{query}\n\n"
        # 放在原文之后，避免模型照抄原文中的概括而漏掉另一段的限定。
        "Before writing the final answer:\n"
        "- Synthesize the passages. Where a configuration exception is stated, "
        "describe the main pattern as mainly or predominantly and include the "
        "exception in the same sentence. Do not repeat an all/only statement "
        "that conflicts with that exception. An exception must change the same "
        "property; keep independent design choices separate.\n"
        "- For why questions, explain each supported mechanism. When comparing "
        "alternatives, explicitly state their supported equivalent property "
        "and quantities, rather than leaving the equivalence implicit in "
        "the phrase instead of.\n"
        "- Omit unnecessary background and names absent from the passages. "
        "Do not repeat the same point or list unasked ablations and implementation details.\n"
        "- For a broad difference-between question with no requested aspect, use "
        "3-5 sentences: lead with the purposes, then the supported core methods. "
        "Prefer primary-paper abstract/introductory definitions. Omit training/test "
        "hyperparameters and unasked performance caveats.\n\n"
        "Answer:"
    )


# 账本可补入主体识别所需的原文锚点，因此引用登记表可能比初选片段更多。
def build_evidence_context(chunks, results, query=None):
    """Preserve ranked raw passages and number any identity anchors consistently."""
    ledger = build_ledger(chunks, [r['chunk_id'] for r in results])
    # 无指定方面的跨篇概念比较，附上双方开头原文，避免只靠实验表格定义方法。
    # 最多两篇、每篇四段；保留原初选及编号，新增片段仍取自已校验知识库。
    question = (query or '').strip().rstrip('?？.。')
    overview = re.fullmatch(r'what (?:is|are) (?:the )?differences? between (.+)', question, re.I)
    if overview and not re.search(r'\b(?:in|on|for|using|under)\b', overview[1], re.I):
        sources = named_sources(question, chunks)
        if len(sources) == 2:
            seen = {c['chunk_id'] for c in ledger['citation_registry']}
            added = []
            for source in sources:
                for chunk in [c for c in chunks if c['source'] == source][:4]:
                    if chunk['chunk_id'] not in seen:
                        ledger['citation_registry'].append(chunk)
                        seen.add(chunk['chunk_id'])
                        added.append(chunk['chunk_id'])
            ledger['comparison_intro_ids'] = added
    raw_context = build_context(ledger['citation_registry'])
    guidance = render_guidance(ledger)
    context = f"Original passages:\n{raw_context}\n\nEvidence guidance:\n{guidance}" if guidance else raw_context
    return context, ledger


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

# 主调用链从这里开始；传入 kb_version 可固定实验库，返回字典供评估保存。
def _run_pipeline(query=None, kb_version=None, complete_evidence=None, completion_rounds=2,
                  agent_output=None, agent_call=None, agent_mode='agent', agent_allow_network=False):
    if completion_rounds not in (1, 2, 3):
        raise ValueError('completion_rounds must be 1, 2 or 3')
    # 1. Load the Semantic FAISS index and its corresponding chunks.
    project_dir = Path(__file__).resolve().parent
    print("LLM: proxy API | Model:", load_settings().get('model', 'not configured'))
    processed_dir = project_dir / "data" / "processed"
    index, chunks, knowledge_base = load_knowledge_base(processed_dir, kb_version)
    print("Knowledge Base:", knowledge_base['version'])
    embedding_model = load_embedding_model()

    print("Total Vectors:", index.ntotal)
    print("Vector Dimensions:", index.d)
    print("Total Chunks:", len(chunks))

    # 2. Read the user's question and decide whether to decompose it.
    query = input("Please enter your question: ").strip() if query is None else query.strip()
    if not query:
        print("Question cannot be empty.")
        return

    print("\nOriginal Query:", query)

    decomposition = (decompose_query(query, call=lambda prompt: agent_call(prompt, 'decompose'))
                     if agent_call else decompose_query(query))
    print("Decomposition:", decomposition)

    if decomposition["needs_decomposition"]:
        print("Sub-Queries:")
        for sub_query in decomposition["sub_queries"]:
            print("-", sub_query)

    # Build BM25 once and reuse it for the original and sub-queries.
    bm25 = build_bm25_index(chunks)

    # 3. Retrieve candidates for the original query using Dense + BM25.
    dense_results = retrieve(
        model=embedding_model,
        index=index,
        chunks=chunks,
        query=query,
        top_k=RETRIEVAL_TOP_K,
    )

    bm25_results = retrieve_bm25(
        bm25=bm25,
        chunks=chunks,
        query=query,
        top_k=RETRIEVAL_TOP_K,
    )

    # Freeze the original query's independent retrieval anchor before augmentation.
    # 在可选改写/HyDE 之前冻结原题首条，避免辅助查询改变必须保留的锚点。
    original_rrf_results = reciprocal_rank_fusion(
        dense_results=dense_results, bm25_results=bm25_results,
        k=RRF_K, top_k=RRF_TOP_K)
    retrieval_anchor_ids = [c['chunk_id'] for c in original_rrf_results[:1]]

    # 4. Collect optional additional retrieval lists.
    # RRF will fuse these lists with the original Dense + BM25 results.
    extra_results = []

    if USE_MULTI_QUERY:
        rewritten_query = rewrite_query(query).strip()
        print("Rewritten Query:", rewritten_query)

        if rewritten_query and rewritten_query != query:
            rewritten_dense_results = retrieve(
                model=embedding_model,
                index=index,
                chunks=chunks,
                query=rewritten_query,
                top_k=RETRIEVAL_TOP_K,
            )

            rewritten_bm25_results = retrieve_bm25(
                bm25=bm25,
                chunks=chunks,
                query=rewritten_query,
                top_k=RETRIEVAL_TOP_K,
            )

            extra_results.extend(
                [rewritten_dense_results, rewritten_bm25_results]
            )
        else:
            print(
                "Rewritten query is empty or unchanged; "
                "using the original query only."
            )

    if USE_HYDE:
        hypothetical_document = generate_hypothetical_document(query).strip()

        if not hypothetical_document:
            raise ValueError("HyDE generated an empty hypothetical document.")

        print("\n=== Hypothetical Document ===")
        print(hypothetical_document)

        hyde_results = retrieve(
            model=embedding_model,
            index=index,
            chunks=chunks,
            query=hypothetical_document,
            top_k=RETRIEVAL_TOP_K,
        )

        extra_results.append(hyde_results)
        print("HyDE Retrieved Chunks:", len(hyde_results))

    print("Additional Retrieval Lists:", len(extra_results))
    print("HyDE Enabled:", USE_HYDE)

    # 5. Retrieve and fuse results for each decomposed sub-query.
    # 子问题只负责补充候选，最后统一按原始问题重排。
    sub_query_results = []

    if decomposition["needs_decomposition"]:
        for sub_query in decomposition["sub_queries"]:
            sub_dense_results = retrieve(
                model=embedding_model,
                index=index,
                chunks=chunks,
                query=sub_query,
                top_k=RETRIEVAL_TOP_K,
            )

            sub_bm25_results = retrieve_bm25(
                bm25=bm25,
                chunks=chunks,
                query=sub_query,
                top_k=RETRIEVAL_TOP_K,
            )

            sub_rrf_results = reciprocal_rank_fusion(
                dense_results=sub_dense_results,
                bm25_results=sub_bm25_results,
                k=RRF_K,
                top_k=RRF_TOP_K,
            )

            sub_query_results.append(
                {
                    "query": sub_query,
                    "results": sub_rrf_results,
                }
            )

            print_ranked_results(
                sub_rrf_results,
                title=f"Sub-Query: {sub_query} (RRF Top-5)",
                limit=5,
            )

    # 6. Fuse original-query Dense + BM25 with optional additional lists.
    rrf_results = reciprocal_rank_fusion(
        dense_results=dense_results,
        bm25_results=bm25_results,
        k=RRF_K,
        top_k=RRF_TOP_K,
        extra_results=extra_results,
    ) if extra_results else original_rrf_results

    # Add sub-query RRF results to the original-query candidate list.
    candidate_pool = list(rrf_results)
    for sub_query_result in sub_query_results:
        candidate_pool.extend(sub_query_result["results"])

    print("\nCandidate Pool Before Deduplication:", len(candidate_pool))

    unique_candidates = deduplicate_candidates(candidate_pool)
    print("Candidate Pool After Deduplication:", len(unique_candidates))

    if not unique_candidates:
        raise RuntimeError(
            "Retrieval returned no candidates. "
            "Check the index, chunks, and retriever configuration."
        )

    # 7. Rerank the complete candidate pool against the original query.
    reranker_model = CrossEncoder(
        RERANKER_MODEL_NAME,
        device=RERANKER_DEVICE,
    )

    # 同一请求内复用完全相同的模型/查询/原文分数，不减少候选、补查或证据预算。
    score_cache = {}
    global_ranking, sub_query_evidence = rank_evidence(
        query, unique_candidates, sub_query_results, reranker_model, SUB_QUERY_EVIDENCE_K,
        score_cache=score_cache)
    results = select_evidence(global_ranking, sub_query_evidence, RERANK_TOP_K,
                              retrieval_anchor_ids)
    retrieval_diagnostics = {
        'candidate_count': len(unique_candidates),
        'global_top_ids': [c['chunk_id'] for c in global_ranking[:RERANK_TOP_K]],
        'protected_ids': list(dict.fromkeys(item['top_ids'][0] for item in sub_query_evidence
                                           if item['top_ids'])),
        'sub_query_evidence': sub_query_evidence,
        'retrieval_anchor_ids': retrieval_anchor_ids,
    }
    # 此处调用固定规则补查；触发与停止不由 agent.py 的行动建议控制。
    completion_enabled = USE_EVIDENCE_COMPLETION if complete_evidence is None else complete_evidence
    if completion_enabled:
        results, completion = supplement_evidence(
            query, global_ranking, sub_query_evidence, retrieval_anchor_ids,
            embedding_model, index, chunks, bm25, reranker_model,
            top_k=RERANK_TOP_K, candidate_k=RETRIEVAL_TOP_K, max_rounds=completion_rounds,
            score_cache=score_cache)
        retrieval_diagnostics['evidence_completion'] = completion

    print("Selected Chunk IDs:", [r["chunk_id"] for r in results])
    print("Sub-Query Evidence Selection:", retrieval_diagnostics)
    print_ranked_results(
        results,
        title=f"Retrieved Top-{RERANK_TOP_K}",
    )

    # 8. Add evidence guidance without dropping the original ranked passages.
    context, ledger = build_evidence_context(chunks, results, query=query)

    print("\n=== Evidence: parsed facts and source quotations ===")
    print(render_complete(ledger)['answer'])
    print("\n=== Citation Sources ===")
    for number, chunk in enumerate(ledger['citation_registry'], 1):
        print(f"[{number}] {chunk['source']}, p.{chunk['page']} (chunk {chunk['chunk_id']})")

    initial = {'query': query, 'status': 'retrieval_completed', 'decomposition': decomposition,
               'knowledge_base': knowledge_base, 'retrieval_diagnostics': retrieval_diagnostics,
               'selected_ids': [r['chunk_id'] for r in results], 'context': context, 'ledger': ledger}
    if agent_output is not None:
        # 只初检一次，不生成固定RAG草稿；把同一批模型/索引交给Agent工具复用。
        resources = {'index': index, 'chunks': chunks, 'knowledge_base': knowledge_base,
                     'embedding_model': embedding_model, 'bm25': bm25, 'reranker_model': reranker_model}
        return _answer_with_agent(initial, resources, agent_output, agent_call, mode=agent_mode,
                                  allow_network=agent_allow_network)

    # 9. Answer and any citation repair use the same configured API as decomposition.
    # 实际生成调用；引用修复若触发，会额外消耗一次 API，相关性排序本身不调用生成 API。
    prompt = build_prompt(query=query, context=context)
    generate = (lambda text: generate_final_answer(text, call=lambda p: agent_call(p, 'answer'))
                if agent_call else generate_final_answer(text))
    try:
        original_answer = generate(prompt)
        citation_validation = repair_citations_once(
            query, context, original_answer, ledger['citation_registry'], generate)
    except Exception as exc:
        return {**initial, 'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'}
    answer = citation_validation['answer']
    print("\n=== Citation Structure Check (semantic support not verified) ===")
    print("Status:", citation_validation['status'])
    print("Initial:", {k: citation_validation['initial_check'][k]
                       for k in ('has_citations', 'invalid_numbers', 'malformed_markers')})
    if citation_validation['repair_attempted']:
        print("\n=== Original Answer Before Citation Repair ===")
        print(original_answer)
        print("Unresolved blocks:", citation_validation['unresolved_blocks'])
    print("Final structure passed:", citation_validation['final_check']['structure_passed'])
    print("\n=== Generated Answer (model draft; check against evidence) ===")
    print(answer)
    return {'query': query, 'decomposition': decomposition, 'knowledge_base': knowledge_base,
            'retrieval_diagnostics': retrieval_diagnostics,
            'selected_ids': [r['chunk_id'] for r in results],
            'context': context, 'prompt': prompt, 'ledger': ledger, 'answer': answer,
            'original_answer': original_answer, 'citation_validation': citation_validation}


def has_evidence_gap(query, answer):
    """保留真实缺口信号；未要求的同基准直接对比缺失不构成概念比较的缺口。"""
    text = answer
    quantitative = re.search(
        r'performance|benchmark|accuracy|scores?|faster|slower|better|speed|latency|throughput|'
        r'efficien|parameters?|cost|实测|性能|指标|基准|准确|分数|更好|更快|速度|耗时|延迟|吞吐|效率|参数量|成本|多少|几倍',
        query, re.I)
    if not quantitative and re.search(r'\b(?:difference|compare|comparison|differ)\b|比较|区别|差异', query, re.I):
        text = re.sub(
            r'(?:现有|当前)?(?:证据|上下文|资料|段落)(?:中)?(?:并)?(?:未提供|未给出|没有|缺少)'
            r'(?:二者|两者|双方)(?:在[^。；\n]{0,30}(?:上|中)的?)?(?:直接对比|直接比较)'
            r'(?:实验|结果|研究|数据)?(?:[。；]|(?=\n|$))',
            lambda match: '' if re.search(r'\[\d+\]', answer[:match.start()]) else match[0], answer)
    return bool(re.search(
        r'(?:证据|上下文|资料|段落).{0,50}(?:不足|未说明|未包含|未给出|未提供|无法确认|无法确定)'
        r'|(?:无法|不能).{0,30}(?:回答|比较|确定|核实)'
        r'|\binsufficient (?:evidence|information)\b'
        r'|\b(?:context|evidence|passages|sources)\b.{0,60}\b(?:does not|do not|cannot|lacks?|insufficient)\b',
        text, re.I))


def _answer_with_agent(initial, resources, output, call, mode='agent', allow_network=False):
    """把新初检原文白名单接入原循环/回答；返回实际最终引用，失败保持可见。"""
    import agent

    evidence, _ = agent.merge_evidence(initial['ledger']['citation_registry'], resources)
    chunks = resources['chunks']
    inventory = [{'source': source, 'title': next(c['title'] for c in chunks if c['source'] == source)}
                 for source in sorted({c['source'] for c in chunks})]
    cases = {'question': {'query': initial['query'], 'kb_version': initial['knowledge_base']['version'],
                          'evidence': evidence, 'inventory': inventory}}
    agent.save_json(output / 'retrieval.json', initial)
    hashes = {str(path): agent.digest(path) for path in (output / 'protocol.json', output / 'retrieval.json')}
    result = {**initial, 'mode': mode, 'status': 'failed', 'answer': None, 'run_dir': str(output),
              'initial_selected_ids': initial['selected_ids'],
              'agent': {'invoked': False, 'actions_executed': 0}}
    probe=None
    network_notice = ''
    if mode == 'auto':
        # 先做原RAG回答；常规问题没有额外规划/分类调用，明确缺口才升级。
        prompt=build_prompt(initial['query'],initial['context'])
        draft=call(prompt,'probe')['answer']
        checked=repair_citations_once(initial['query'],initial['context'],draft,
                 initial['ledger']['citation_registry'],lambda text:call(text,'probe')['answer'])
        probe={'original_answer':draft,'answer':checked['answer'],'citation_validation':checked}
        agent.save_json(output/'probe.json',probe)
        signals=[]
        if not checked['final_check']['structure_passed']:
            signals.append('citation_repair_failed')
        if has_evidence_gap(initial['query'], checked['answer']):
            signals.append('explicit_evidence_gap')
        route='agent' if signals else 'direct'
        routing={'route':route,'strategy':'rag_first','trigger_signals':signals,'gate_decision_calls':0,
                 'reason':'原RAG回答出现明确证据缺口或引用失败。' if signals else '原RAG回答未显示证据缺口，引用结构通过。'}
        result['routing']=routing
        agent.save_json(output/'routing.json',routing)
        if route=='direct':
            answer_dir=output/'answer';answer_dir.mkdir()
            agent.save_json(answer_dir/'direct.json',{**probe,'status':'completed','strategy':'rag_first_direct'})
            agent.save_json(answer_dir/'inputs.json',{'query':initial['query'],'passages':evidence})
            (answer_dir/'answer.md').write_text(checked['answer']+'\n',encoding='utf-8')
            result.update(status='completed',answer=checked['answer'],prompt=prompt,original_answer=draft,
                          citation_validation=checked,answer_strategy='rag_first_direct')
            print('\n=== Auto: RAG Direct Answer ===');print(result['answer'])
            return result

    def preserve_initial_answer():
        # 决策/复核失败保留可见失败，只用已完成且引用结构合格的初检回答降级交付。
        if probe and probe['citation_validation']['final_check']['structure_passed']:
            result.update(status='degraded',answer=(network_notice or '补查未完成，以下仅依据初检证据回答，仍保留原有缺口：')+'\n'+probe['answer'],
                          answer_strategy='initial_rag_after_agent_failure',
                          context=initial['context'],ledger=initial['ledger'],selected_ids=initial['selected_ids'],
                          fallback={'reason':result.get('error','Agent answer review failed.'),'agent_status':'failed'})
            agent.save_json(output/'fallback.json',result['fallback'])
            (output/'fallback.md').write_text(result['answer']+'\n',encoding='utf-8')
            print(result['answer'])
        return result

    decision_call = lambda prompt: call(prompt, 'decision')
    decision = agent.run_diagnostics(cases, output / 'loop', hashes, resources=resources, max_actions=3,
                                     call=decision_call)
    loop = json.loads((output / 'loop' / 'question.json').read_text())
    result['agent'].update(invoked=True,decision_summary=decision,halt_reason=loop.get('halt_reason'),
                           actions_executed=loop['actions_executed'])
    result['actions'] = [{'tool': step['action']['type'], 'status': step['status'], 'action': step['action']}
                         for step in loop.get('steps', [])]
    if decision['completed_cases'] != 1:
        result['error'] = loop.get('error', 'Agent decision did not complete.')
        print('Agent failed:', result['error'])
        return preserve_initial_answer()
    if allow_network and loop.get('halt_reason') == 'model_stop':
        # 先完成本地缺口判断，再以独立预算补一篇外部原文；无需先付本地答案生成成本。
        from src.arxiv_evidence import run_arxiv_followup
        network = run_arxiv_followup(Path(__file__).resolve().parent, output / 'loop' / 'question.json',
                                     output / 'network', resources, call)
        result['network'] = {k: v for k, v in network.items() if k not in {'answer', 'passages', 'assessment'}}
        result['actions'].extend(network['actions'])
        if network['status'] == 'completed':
            passages = network['passages']
            result.update(status='completed', answer=network['answer'], answer_strategy='arxiv_evidence_reviewed',
                          selected_ids=[p['chunk_id'] for p in passages], context=build_context(passages),
                          ledger={'citation_registry': passages})
            print('\n=== Agent: arXiv Evidence Answer ===');print(result['answer'])
            return result
        if network['status'] == 'failed':
            result['error'] = network['error']
            failure = network.get('failure', {})
            kind = failure.get('kind')
            if kind not in {'rate_limited', 'timeout', 'http_error', 'transport_error'}:
                return preserve_initial_answer()
            # 获取失败与论文未报告是两回事；仍可用已校验的本地原文完成有限回答。
            trace = failure['trace']
            cause = {'rate_limited': 'arXiv请求受到限流（HTTP 429）', 'timeout': 'arXiv请求超时',
                     'http_error': f"arXiv请求失败（HTTP {trace.get('http_status')}）",
                     'transport_error': 'arXiv连接失败'}[kind]
            network_notice = cause + '，补查未完成。尚未取得所需原文，暂时无法核实；不能据此判断论文是否报告了所问内容。'
            delay = trace.get('retry_after_seconds')
            if delay is not None:
                network_notice += f'服务端提示至少等待{delay}秒后再尝试，本轮未自动重试。'
            else:
                network_notice += '服务端未提供有效等待时间，本轮未自动重试。'
            network_notice += '\n以下仅依据本地证据回答，仍保留未核实的需求：'
            result.update(answer_status='source_unavailable', stop_reason=f'external_{kind}')
            if probe and probe['citation_validation']['final_check']['structure_passed']:
                return preserve_initial_answer()
    answer = agent.run_answer(Path(__file__).resolve().parent, output / 'loop' / 'question.json',
                              output / 'answer', call=lambda prompt: call(prompt, 'answer'),
                              source_unavailable=bool(network_notice))
    result['agent']['answer_summary'] = answer
    record = json.loads((output / 'answer' / 'question.json').read_text())
    payload = json.loads((output / 'answer' / 'inputs.json').read_text())
    result.update(selected_ids=[p['chunk_id'] for p in payload['passages']],
                  context=build_context(payload['passages']), ledger={'citation_registry': payload['passages']})
    if record['status'] == 'completed':
        result['answer'] = record['result']['answer']
        result['status'] = 'completed' if answer['answer_status'] != 'review_failed' else 'failed'
        if result['status'] == 'failed':
            result['answer_status'] = answer['answer_status']
        else:
            result.setdefault('answer_status', answer['answer_status'])
    else:
        result['error'] = record['error']
    if network_notice and result['status'] == 'completed':
        result.update(status='degraded', answer=network_notice+'\n'+result['answer'],
                      answer_strategy='local_evidence_after_network_failure',
                      fallback={'reason': result['error'], 'network_status': 'failed',
                                'local_answer_status': answer['answer_status']})
        agent.save_json(output/'fallback.json', result['fallback'])
        (output/'fallback.md').write_text(result['answer']+'\n', encoding='utf-8')
    if result['status']=='failed' and mode=='auto':
        return preserve_initial_answer()
    print('\n=== Agent Answer ===')
    print(result['answer'] if result['answer'] is not None else result['error'])
    print('Run directory:', output)
    return result


def _record_call(prompt, phase, calls, output=None):
    """三模式共用实际调用账本；先记录再发送，截断/传输失败不重试。"""
    import agent
    entry = {'number': len(calls) + 1, 'phase': phase, 'prompt': prompt, 'status': 'running',
             'started_at_utc': datetime.now(timezone.utc).isoformat()}
    calls.append(entry)
    if output is not None:
        agent.save_json(output / 'actual_chat_calls.json', calls)
    started = time.perf_counter()
    try:
        response = api.chat_completion(prompt)
        if response.get('finish_reason') != 'stop':
            raise api.IncompleteResponseError(response)
        entry.update(status='completed', response=response)
        return response
    except Exception as exc:
        entry.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        if isinstance(exc, api.IncompleteResponseError):
            entry['response'] = exc.response
        raise
    finally:
        entry['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        if output is not None:
            agent.save_json(output / 'actual_chat_calls.json', calls)


def _finish_result(result, calls):
    """统一可展示结果；完成处理不等于事实正确，拒答和来源不可用另列answer_status。"""
    result.setdefault('mode', 'rag')
    result.setdefault('status', 'completed')
    checked = result.get('citation_validation', {}).get('final_check', {})
    if result['mode'] == 'rag' and checked and not checked['structure_passed']:
        result.update(status='failed', answer_status='citation_failed', stop_reason='citation_check_failed',
                      answer='回答引用未通过校验，本轮无法交付可靠的事实性答案。')
    result.setdefault('answer_status', result.get('network', {}).get('answer_status') or
                      result.get('agent', {}).get('answer_summary', {}).get('answer_status') or
                      ('unavailable' if result['status'] == 'failed' else 'not_reviewed'))
    result.setdefault('stop_reason', 'processing_failed' if result['status'] == 'failed' else
                      result.get('agent', {}).get('halt_reason') or result.get('answer_strategy', 'rag_answer'))
    if not result.get('answer'):
        result['answer'] = '本轮处理未完成，暂时无法核实答案。具体错误已保留在运行记录中。'
    result.setdefault('ledger', {'citation_registry': []})
    result.setdefault('selected_ids', [])
    result.setdefault('actions', [])
    result.setdefault('network', {'status': 'not_requested', 'http_tool_calls': 0, 'papers_read': 0})
    usage = [c.get('response', {}).get('usage') for c in calls]
    result['api_summary'] = {'attempts': len(calls),
        'failed_attempts': sum(c['status'] != 'completed' for c in calls), 'automatic_retries': 0,
        'usage_missing_calls': [c['number'] for c, u in zip(calls, usage) if u is None],
        'reported_usage': {key: sum((u or {}).get(key, 0) for u in usage)
                           for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}}
    return result


def main(query=None, kb_version=None, complete_evidence=None, completion_rounds=2,
         mode='rag', output_dir=None, allow_network=False):
    """函数默认RAG；显式联网时Agent/Auto最多14/16模型请求，另最多两次公网工具。"""
    if type(allow_network) is not bool:
        raise ValueError('allow_network must be a boolean.')
    if mode not in {'rag', 'agent', 'auto'}:
        raise ValueError('mode must be rag, agent or auto.')
    if mode == 'rag':
        if allow_network:
            raise ValueError('arXiv followup requires mode=agent or auto; fixed RAG remains the baseline.')
        if output_dir is not None:
            raise ValueError('output_dir is for Agent/Auto run logs; use mode=agent or auto.')
        if completion_rounds not in (1, 2, 3):
            raise ValueError('completion_rounds must be 1, 2 or 3')
        calls = []
        try:
            result = _run_pipeline(query, kb_version, complete_evidence, completion_rounds,
                                   agent_call=lambda prompt, phase: _record_call(prompt, phase, calls))
            if result is None:
                return None
        except Exception as exc:
            result = {'query': query, 'mode': 'rag', 'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'}
        return _finish_result(result, calls)
    import agent
    from src.agent_tools import SEARCH_KB_VERSION

    if kb_version not in (None, SEARCH_KB_VERSION):
        raise ValueError(f'Agent tools currently require kb_version={SEARCH_KB_VERSION}.')
    if completion_rounds not in (1, 2, 3) or USE_MULTI_QUERY or USE_HYDE:
        raise ValueError('Agent entry requires completion_rounds 1/2/3 and rewrite/HyDE disabled.')
    query = input('Please enter your question: ').strip() if query is None else query.strip()
    if not query:
        print('Question cannot be empty.')
        return
    project = Path(__file__).resolve().parent
    output = (Path(output_dir) if output_dir is not None else project / 'logs' / f'{mode}_runs' /
              datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new empty output directory; existing runs are preserved, not rerun.')
    output.mkdir(parents=True, exist_ok=True)
    public = {key: api.load_settings().get(key) for key in ('base_url', 'model', 'chat_options')}
    limits = {'decompose': 1, 'decision': agent.MAX_API_CALLS, 'answer': agent.MAX_ANSWER_CALLS}
    if allow_network:
        from src.arxiv_evidence import MAX_NETWORK_DECISIONS
        limits['network'] = MAX_NETWORK_DECISIONS
    if mode=='auto':
        limits['probe']=2  # 原RAG初稿及最多一次引用修复；与升级后的回答复核独立记账。
    protocol = {'stage': f'fresh main {mode} run', 'mode': mode, 'query': query, 'allow_network': allow_network,
                'kb_version': SEARCH_KB_VERSION, 'api_public_settings': public,
                'completion_rounds': completion_rounds, 'complete_evidence': complete_evidence,
                'stage_call_limits': limits, 'max_actual_attempts': sum(limits.values()),
                'automatic_retries': 0, 'max_tool_actions': agent.MAX_LOOP_ACTIONS,
                'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
                'source_hashes': {str(p.relative_to(project)): agent.digest(p) for p in
                    [Path(__file__).resolve(), Path(agent.__file__).resolve(), *sorted((project / 'src').glob('*.py'))]}}
    # 独占创建协议，避免两个进程误用同一空目录；任何请求之前先留下运行身份。
    with (output / 'protocol.json').open('x', encoding='utf-8') as file:
        json.dump(protocol, file, ensure_ascii=False, indent=2)
    calls = []
    agent.save_json(output / 'actual_chat_calls.json', calls)

    def audited_call(prompt, phase):
        if len(calls) >= sum(limits.values()) or sum(c['phase'] == phase for c in calls) >= limits[phase]:
            raise RuntimeError('Main Agent call budget exhausted; no retry.')
        if {key: api.load_settings().get(key) for key in public} != public:
            raise RuntimeError('API options changed after this run was frozen.')
        return _record_call(prompt, phase, calls, output)

    result = {'query': query, 'mode': mode, 'status': 'running', 'run_dir': str(output)}
    try:
        result = _run_pipeline(query, SEARCH_KB_VERSION, complete_evidence, completion_rounds,
                               agent_output=output, agent_call=audited_call, agent_mode=mode,
                               agent_allow_network=allow_network)
    except Exception as exc:
        # 输入/配置校验仍在请求前抛出；运行时故障返回可展示结果，CLI照常非零。
        if (output / 'retrieval.json').is_file():
            result.update(json.loads((output / 'retrieval.json').read_text()))
        result.update(status='failed', error=f'{type(exc).__name__}: {exc}')
    finally:
        _finish_result(result, calls)
        agent.save_json(output / 'result.json', result)
    return result


def cli():
    parser = argparse.ArgumentParser(description='Paper QA: evidence-gated Auto, fixed RAG or bounded Agent.')
    parser.add_argument('query', nargs='?', help='Question; omit to enter it interactively')
    parser.add_argument('--mode', choices=('rag', 'agent', 'auto'), default='auto')
    parser.add_argument('--kb-version', help='Explicit KB; Agent/Auto use the verified eight-paper version')
    parser.add_argument('--output-dir', type=Path, help='New empty Agent/Auto audit directory')
    parser.add_argument('--allow-network', action='store_true', help='Allow one bounded arXiv followup after a local missing-source stop')
    args = parser.parse_args()
    result = main(args.query, kb_version=args.kb_version, mode=args.mode, output_dir=args.output_dir,
                  allow_network=args.allow_network)
    if result is not None and result.get('status') in {'failed','degraded'}:
        if result['status'] == 'failed':
            print(result.get('answer', '本轮处理未完成。'))
        print('停止原因：', result.get('stop_reason', 'processing_failed'))
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
