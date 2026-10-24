"""Freeze inputs, inventory every data PDF, and publish an exact union of verified pairs."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    import faiss
    import numpy as np
    import pymupdf
    from src.knowledge_base import create_version, load_knowledge_base
    assert not (OUT / 'protocol.json').exists(), 'Preserve frozen experiment inputs.'
    tracked = [ROOT / 'main.py', ROOT / 'llm.py', ROOT / 'PROGRESS.md', ROOT / 'README.md',
               ROOT / 'evaluation/run_evaluation.py', ROOT / 'evaluation/metrics.py',
               ROOT / 'api.local.json', ROOT / 'data/processed/active_kb.json',
               *sorted((ROOT / 'src').glob('*.py')), *sorted((ROOT / 'tests').glob('*.py')),
               *sorted((ROOT / 'evaluation').glob('*questions*.json')),
               *sorted((ROOT / 'data/processed/versions').glob('*/*')),
               *sorted((ROOT / 'data').rglob('*.pdf'))]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in tracked if p.is_file()}
    if (OUT / 'baseline_hashes.json').exists():
        frozen = json.loads((OUT / 'baseline_hashes.json').read_text())
        assert all(hashes[name] == digest for name, digest in frozen.items())
    else:
        save(OUT / 'baseline_hashes.json', hashes)
    for p in tracked:
        if p.suffix in ('.py', '.md'):
            target = OUT / 'baseline' / p.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, target)
    versions = ['semantic-mac-20261019', 'arxiv-pilot-5-20261019']
    pairs = [load_knowledge_base(ROOT / 'data/processed', v) for v in versions]
    source_hashes = {}
    for version in versions:
        manifest = json.loads((ROOT / f'data/processed/versions/{version}/manifest.json').read_text())
        assert manifest['build']['embedding_model'] == 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
        assert manifest['build']['normalized_embeddings']
        source_hashes.update(manifest['build']['source_pdfs'])
    inventory, seen = [], set()
    for p in sorted((ROOT / 'data').rglob('*.pdf')):
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        assert source_hashes[p.name] == digest, f'PDF changed: {p}'
        assert digest not in seen, 'Deduplicate identical PDFs before including them.'
        seen.add(digest)
        with pymupdf.open(p) as doc:
            inventory.append({'path': str(p.relative_to(ROOT)), 'source': p.name,
                              'sha256': digest, 'pages': len(doc)})
    assert len(inventory) == 8 and set(source_hashes) == {p['source'] for p in inventory}
    chunks, vectors, mapping = [], [], {}
    for index, original, metadata in pairs:
        assert index.d == 384 and type(index).__name__ == 'IndexFlatIP'
        offset = len(chunks)
        mapping[metadata['version']] = {str(c['chunk_id']): offset + c['chunk_id'] for c in original}
        chunks.extend({**c, 'chunk_id': offset + c['chunk_id']} for c in original)
        vectors.append(index.reconstruct_n(0, index.ntotal))
    assert {c['source'] for c in chunks} == {p['source'] for p in inventory}
    assert len({(c['source'], c['page'], c['text']) for c in chunks}) == len(chunks)
    embeddings = np.vstack(vectors)
    assert np.allclose(np.linalg.norm(embeddings, axis=1), 1, atol=1e-5)
    merged = faiss.IndexFlatIP(384)
    merged.add(embeddings)
    version = 'all-papers-8-20261020'
    with tempfile.TemporaryDirectory(dir=OUT) as directory:
        folder = Path(directory)
        faiss.write_index(merged, str(folder / 'faiss.index'))
        save(folder / 'chunks.json', chunks)
        if (ROOT / f'data/processed/versions/{version}').exists():
            saved_index, saved_chunks, _ = load_knowledge_base(ROOT / 'data/processed', version)
            assert saved_chunks == chunks and np.array_equal(saved_index.reconstruct_n(0, len(chunks)), embeddings)
        else:
            create_version(ROOT / 'data/processed', version, folder / 'faiss.index', folder / 'chunks.json',
                           {'kind': 'exact_union_of_verified_pairs', 'parent_versions': versions,
                            'embedding_model': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                            'normalized_embeddings': True, 'source_pdfs': source_hashes,
                            'note': 'No new parsing/chunking/embedding; vectors preserved exactly, IDs remapped.'})
    save(OUT / 'inventory.json', {'papers': inventory, 'paper_count': len(inventory),
                                'pages': sum(p['pages'] for p in inventory), 'chunk_count': len(chunks)})
    save(OUT / 'chunk_id_mapping.json', mapping)
    old, pilot = pairs[0][1], pairs[1][1]

    def gold(c, quote):
        assert unicodedata.normalize('NFKC', quote) in unicodedata.normalize('NFKC', c['text'])
        return {'source': c['source'], 'page': c['page'], 'quote': quote}

    def question(number, kind, text, refs, points):
        return {'id': f'a{number:02}', 'type': kind, 'cohort': 'new_all_papers', 'question': text,
                'gold_evidence': [gold(c, quote) for c, quote in refs], 'reference_points': points}

    single, cross = 'single_document', 'cross_document'
    new = [
        question(1, single, 'Where are residual connections and layer normalization placed relative to the encoder sub-layers in the Transformer?',
                 [(old[23], 'residual connection'), (old[23], 'LayerNorm(x + Sublayer(x))')],
                 ['Residual connection around each sub-layer, followed by layer normalization.']),
        question(2, single, 'How did ReLU affect training speed relative to saturating neurons in the DCNN paper?',
                 [(old[136], 'networks with ReLUs consistently learn several times faster')],
                 ['Networks with ReLU learn several times faster than equivalents with saturating neurons.']),
        question(3, single, 'Why does VGG configuration C include 1x1 convolutional layers, and what happens to the receptive field?',
                 [(old[247], 'increase the non- linearity of the decision function without affecting the receptive fields')],
                 ['Adds nonlinearity through rectification without changing receptive fields.']),
        question(4, single, 'Which indexing library and approximate nearest-neighbor structure are used for fast retrieval in the original RAG paper?',
                 [(pilot[383], 'using FAISS'), (pilot[383], 'Hierarchical Navigable Small World')], ['FAISS with HNSW approximation for MIPS.']),
        question(5, single, 'When does DPR encode and index all candidate passages, and which indexing library is used?',
                 [(pilot[32], 'index them using FAISS')], ['Passages are encoded and indexed offline using FAISS.']),
        question(6, single, 'Which token embeddings does the ColBERT document encoder remove after projection, and why?',
                 [(pilot[232], 'punctuation symbols')], ['Removes punctuation embeddings to reduce document embedding count.']),
        question(7, single, 'How does Self-RAG search over output segments and incorporate critique-token probabilities into segment scores?',
                 [(pilot[617], 'segment-level beam search'), (pilot[617], 'linear weighted sum')],
                 ['Segment beam search retains top-B continuations; adds a linear weighted sum of normalized critique probabilities.']),
        question(8, single, 'How does CRAG aggregate document confidence scores to classify an entire retrieval as Correct or Incorrect?',
                 [(pilot[892], 'at least one retrieved document'), (pilot[893], 'all retrieved documents are below the lower threshold')],
                 ['Correct if at least one exceeds upper threshold; Incorrect if all fall below lower threshold.']),
        question(9, cross, 'What output dimensionalities are used for Transformer sub-layers and embeddings, and for DPR question and passage vectors?',
                 [(old[24], 'dmodel = 512'), (pilot[32], 'd = 768')], ['Transformer 512; DPR 768.']),
        question(10, cross, 'What pooling window sizes and strides are used in DCNN and VGG, and which one uses overlapping pooling?',
                 [(old[147], 'a neighborhood of size z × z'), (old[153], 's = 2 and z = 3'),
                  (old[234], '2 × 2 pixel window, with stride 2')], ['DCNN 3x3 stride 2 overlapping; VGG 2x2 stride 2.']),
        question(11, cross, 'How does the original RAG paper index its Wikipedia document embeddings, and how can CRAG obtain evidence beyond a static corpus?',
                 [(pilot[383], 'build a single MIPS index using FAISS'), (pilot[852], 'large-scale web searches')],
                 ['RAG uses a FAISS HNSW MIPS index; CRAG adds web search for Incorrect/Ambiguous retrieval.']),
        question(12, cross, 'Do DPR and ColBERT share BERT weights between their question or query encoder and document encoder?',
                 [(pilot[32], 'two independent BERT'), (pilot[223], 'share a single BERT model')],
                 ['DPR uses independent encoders; ColBERT shares one BERT model with Q/D markers.']),
        question(13, cross, 'How are critique scores used to rank generated segments in Self-RAG, and how are confidence thresholds used to classify retrieval in CRAG?',
                 [(pilot[617], 'linear weighted sum'), (pilot[892], 'at least one retrieved document'),
                  (pilot[893], 'all retrieved documents are below the lower threshold')],
                 ['Self-RAG scores beam segments with critique probabilities; CRAG applies upper/lower confidence thresholds to retrieved documents.']),
        question(14, cross, 'How do DPR and the original RAG paper precompute and index passage or document representations for retrieval?',
                 [(pilot[32], 'index them using FAISS'), (pilot[383], 'compute an embedding for each document')],
                 ['Both encode passages/documents offline and index in FAISS; RAG specifies a HNSW approximation for MIPS.']),
        question(15, cross, 'Where is dropout applied in the Transformer and in the VGG training setup?',
                 [(old[67], 'output of each sub-layer'), (old[67], 'sums of the embeddings and the positional encodings'),
                  (old[254], 'first two fully-connected layers')],
                 ['Transformer sub-layer outputs and embedding plus position sums; VGG first two FC layers with ratio 0.5.']),
        question(16, cross, 'What batch sizes, momentum values, and weight-decay coefficients are used to train DCNN and VGG?',
                 [(old[175], 'batch size of 128 examples, momentum of 0.9, and weight decay of 0.0005'),
                  (old[254], 'batch size was set to 256, momentum to 0.9'), (old[254], '5·10−4')],
                 ['DCNN batch 128, VGG batch 256; both momentum 0.9 and weight decay 0.0005.']),
    ]
    questions = []
    for name in ['questions', 'arxiv_pilot_questions_en', 'arxiv_validation_questions_en', 'arxiv_next_questions_en']:
        for q in json.loads((ROOT / f'evaluation/{name}.json').read_text()):
            questions.append({**q, 'cohort': name})
    questions.extend(new)
    assert len({q['id'] for q in questions}) == len(questions)
    save(ROOT / 'evaluation/all_papers_questions_en.json', questions)
    protocol = {'date': '2026-10-20 Asia/Shanghai', 'kb_version': version,
                'corpus': {'papers': 8, 'pages': sum(p['pages'] for p in inventory), 'chunks': len(chunks)},
                'questions': {'answerable': 42, 'no_gold_skipped': 4, 'old': 26, 'new': 16,
                              'single': 26, 'cross': 16, 'language': 'English'},
                'query_modes': ['base', 'rewrite', 'hyde', 'both'], 'completion_caps': [0, 1, 2],
                'candidate_k': 60, 'final_k': 10,
                'metrics': ['precision', 'recall', 'map', 'mrr', 'full_gold_coverage', 'elapsed', 'API usage'],
                'auxiliary_calls': {'reuse_decomposition': 16, 'new_decomposition_max': 26,
                                    'rewrite': 42, 'hyde': 42, 'total_max': 110},
                'answer_probe': {'questions': ['p3', 'n07', 'a10', 'a12'],
                                 'conditions': ['base/0', 'both/2'], 'answer_calls': 8, 'repair_calls_max': 8},
                'total_api_call_cap': 126, 'automatic_retries': 0,
                'gates': {'overall_map_gain_min': 0.01, 'new_cross_recall_gain_min': 0.10,
                          'old_cohort_recall_drop_max': 0, 'old_map_mrr_drop_max': 0.01,
                          'answer_probe_strict_regressions_max': 0},
                'limits': ['Manual same-corpus validation; not blind or external benchmark.',
                           'Specified Gold coverage is not answer accuracy; preserve ambiguous n08.',
                           'No Gold/reference answers in runtime or transformation prompts.',
                           'No production default activation before evidence supports it.',
                           'Round 2 also doubles candidate depth; not an isolated round-count effect.']}
    save(OUT / 'protocol.json', protocol)
    print(json.dumps({'version': version, 'papers': 8, 'pages': protocol['corpus']['pages'],
                      'chunks': len(chunks), 'answerable': 42, 'skipped': 4}))


if __name__ == '__main__':
    main()
