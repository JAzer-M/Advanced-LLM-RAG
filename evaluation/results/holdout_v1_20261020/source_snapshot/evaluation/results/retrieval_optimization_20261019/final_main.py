"""Main entry point for the Advanced-LLM-RAG pipeline.

Current pipeline:
PDF chunks -> Dense + BM25 -> RRF -> optional query rewrite / HyDE /
query-decomposition retrieval -> deduplication -> Cross-Encoder reranking
-> evidence ledger + original context -> API answer generation.

Note:
- USE_HYDE is disabled based on the latest ON/OFF evaluation.
- Sub-query Top-3 evidence is prioritized within the same final Top-10 budget;
  the original RRF first hit is retained as a retrieval anchor, and final
  passages keep their original-query global order.
"""

from pathlib import Path

from sentence_transformers import CrossEncoder

from src.api_llm import generate_final_answer, load_settings
from src.bm25_retriever import build_bm25_index, retrieve_bm25
from src.citation_validation import repair_citations_once
from src.embedding import load_embedding_model
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

RETRIEVAL_TOP_K = 60
RRF_TOP_K = 60
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

def build_context(results):
    """Build a numbered context so the LLM can cite retrieved chunks."""
    context_parts = []

    for rank, result in enumerate(results, start=1):
        context_parts.append(
            f"[{rank}] Source: {result['source']} | "
            f"Page: {result['page']} | "
            f"Section: {result.get('section', 'None')}\n"
            f"{result['text']}"
        )

    return "\n\n".join(context_parts)


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
        "facts are supported, answer them directly.\n\n"
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
        "Do not repeat the same point or list unasked ablations and implementation details.\n\n"
        "Answer:"
    )


def build_evidence_context(chunks, results):
    """Preserve ranked raw passages and number any identity anchors consistently."""
    ledger = build_ledger(chunks, [r['chunk_id'] for r in results])
    raw_context = build_context(ledger['citation_registry'])
    guidance = render_guidance(ledger)
    context = f"Original passages:\n{raw_context}\n\nEvidence guidance:\n{guidance}" if guidance else raw_context
    return context, ledger


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main(query=None, kb_version=None):
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

    decomposition = decompose_query(query)
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
    )

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

    global_ranking, sub_query_evidence = rank_evidence(
        query, unique_candidates, sub_query_results, reranker_model, SUB_QUERY_EVIDENCE_K)
    retrieval_anchor_ids = [c['chunk_id'] for c in rrf_results[:1]]
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

    print("Selected Chunk IDs:", [r["chunk_id"] for r in results])
    print("Sub-Query Evidence Selection:", retrieval_diagnostics)
    print_ranked_results(
        results,
        title=f"Retrieved Top-{RERANK_TOP_K}",
    )

    # 8. Add evidence guidance without dropping the original ranked passages.
    context, ledger = build_evidence_context(chunks, results)
    prompt = build_prompt(query=query, context=context)

    print("\n=== Evidence: parsed facts and source quotations ===")
    print(render_complete(ledger)['answer'])
    print("\n=== Citation Sources ===")
    for number, chunk in enumerate(ledger['citation_registry'], 1):
        print(f"[{number}] {chunk['source']}, p.{chunk['page']} (chunk {chunk['chunk_id']})")

    # 9. Answer and any citation repair use the same configured API as decomposition.
    original_answer = generate_final_answer(prompt)
    citation_validation = repair_citations_once(
        query, context, original_answer, ledger['citation_registry'], generate_final_answer)
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


if __name__ == "__main__":
    main()
