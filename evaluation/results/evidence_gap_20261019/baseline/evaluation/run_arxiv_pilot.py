"""Offline, original-query retrieval pilot; no decomposition or generation API calls."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sentence_transformers import CrossEncoder

import main as pipeline
from src.bm25_retriever import build_bm25_index, retrieve_bm25
from src.embedding import load_embedding_model
from src.hybrid_retriever import reciprocal_rank_fusion
from src.knowledge_base import load_knowledge_base
from src.reranker import rerank_results
from src.retriever import retrieve


def normalized(text):
    return ''.join(unicodedata.normalize('NFKC', text).casefold().split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kb-version', required=True)
    parser.add_argument('--questions', type=Path, default=ROOT / 'evaluation/arxiv_pilot_questions.json')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    index, chunks, metadata = load_knowledge_base(ROOT / 'data/processed', args.kb_version)
    questions = json.loads(args.questions.read_text(encoding='utf-8'))
    tracked = [Path(__file__).resolve(), ROOT / 'main.py', args.questions,
               *sorted((ROOT / 'src').glob('*.py')),
               *(Path(metadata[k]) for k in ('index_path', 'chunks_path', 'manifest_path'))]
    hashes = {p.resolve(): hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}
    print('Loading cached CPU embedding and reranker once', flush=True)
    embedding = load_embedding_model()
    reranker = CrossEncoder(pipeline.RERANKER_MODEL_NAME, device=pipeline.RERANKER_DEVICE)
    bm25 = build_bm25_index(chunks)
    report = {'mode': __doc__, 'api_calls': 0, 'knowledge_base': metadata,
              'source_chunks': dict(Counter(c['source'] for c in chunks)),
              'retrieval_top_k': pipeline.RETRIEVAL_TOP_K,
              'rrf_top_k': pipeline.RRF_TOP_K, 'rrf_k': pipeline.RRF_K,
              'rerank_top_k': pipeline.RERANK_TOP_K,
              'code_and_inputs_sha256': {
                  str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): sha
                  for p, sha in hashes.items()},
              'questions': []}
    for question in questions:
        started = time.perf_counter()
        dense = retrieve(embedding, index, chunks, question['question'], pipeline.RETRIEVAL_TOP_K)
        sparse = retrieve_bm25(bm25, chunks, question['question'], pipeline.RETRIEVAL_TOP_K)
        fused = reciprocal_rank_fusion(dense, sparse, k=pipeline.RRF_K, top_k=pipeline.RRF_TOP_K)
        ranked = rerank_results(question['question'], fused, reranker,
                                top_k=pipeline.RERANK_TOP_K, include_source=True)
        stages = {'dense': dense, 'bm25': sparse, 'rrf': fused, 'rerank': ranked}
        evidence = []
        for gold in question.get('gold_evidence', []):
            matching = {c['chunk_id'] for c in chunks
                        if c['source'] == gold['source'] and c['page'] == gold['page']
                        and normalized(gold['quote']) in normalized(c['text'])}
            evidence.append({**gold, 'matching_chunk_ids': sorted(matching),
                             'ranks': {name: [i for i, c in enumerate(results, 1)
                                              if c['chunk_id'] in matching]
                                       for name, results in stages.items()}})
        entry = {'id': question['id'], 'query': question['question'], 'type': question['type'],
                 'elapsed_seconds': round(time.perf_counter() - started, 2),
                 'candidate_counts': {name: len(values) for name, values in stages.items()},
                 'gold': evidence, 'top10': ranked,
                 'all_gold_locatable': all(g['matching_chunk_ids'] for g in evidence) if evidence else None,
                 'all_gold_in_top10': all(g['ranks']['rerank'] for g in evidence) if evidence else None}
        report['questions'].append(entry)
        (args.output_dir / 'retrieval.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(entry['id'], 'gold locatable', entry['all_gold_locatable'],
              'all gold Top-10', entry['all_gold_in_top10'],
              'seconds', entry['elapsed_seconds'], flush=True)
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == sha for p, sha in hashes.items())
    lines = ['# 五篇 arXiv 论文：离线检索先导实验', '',
             '仅原问题 Dense + BM25 → RRF Top-60 → BGE Top-10；不调用分解或生成 API。',
             'Gold 短引命中只表示证据定位，完整语义支持另行人工检查。手工小样本不代表总体准确率。', '',
             '| 题目 | 类型 | Gold 可定位 | 全部 Gold 进入 Top-10 | 秒 |',
             '| --- | --- | --- | --- | --- |']
    for entry in report['questions']:
        lines.append(f"| {entry['id']} | {entry['type']} | {entry['all_gold_locatable']} | "
                     f"{entry['all_gold_in_top10']} | {entry['elapsed_seconds']} |")
    for entry in report['questions']:
        lines.extend(['', f"## {entry['id']}：{entry['query']}", ''])
        lines.extend(f"- [{i}] {c['source']}，PDF p.{c['page']}，chunk {c['chunk_id']}"
                     for i, c in enumerate(entry['top10'], 1))
    (args.output_dir / 'retrieval.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
