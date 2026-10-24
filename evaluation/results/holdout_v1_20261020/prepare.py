"""Freeze twelve new questions and original-PDF evidence before any model call."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import unicodedata

import pymupdf

ROOT = Path('/Users/j/Desktop/Advanced-LLM-RAG')
STAGE = Path(__file__).resolve().parent
OUT = STAGE / 'results'
CHUNKS = json.loads((ROOT / 'data/processed/versions/all-papers-8-20261020/chunks.json').read_text())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def norm(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text)).lower().strip()


def evidence(chunk_id, quote):
    chunk = CHUNKS[chunk_id]
    assert chunk['chunk_id'] == chunk_id and norm(quote) in norm(chunk['text'])
    return {key: chunk[key] for key in ('source', 'page')} | {'quote': quote}


def question(qid, kind, text, references, points, novelty):
    return {'id': qid, 'type': kind, 'question': text,
            'gold_evidence': [evidence(*ref) for ref in references],
            'reference_points': points, 'novelty_vs_previous_46': novelty}


questions = [
    question('h01', 'single_document',
             'What label-smoothing value does Attention Is All You Need use, and how does the paper say it affects perplexity versus accuracy and BLEU?',
             [(69, 'we employed label smoothing of value'), (70, 'This hurts perplexity')],
             ['Label smoothing epsilon is 0.1.',
              'It hurts perplexity (the model is more unsure) but improves accuracy and BLEU.'],
             'Regularization and metric tradeoff; no old question asked label smoothing.'),
    question('h02', 'single_document',
             'In CRAG knowledge refinement, how are knowledge strips formed, filtered, and recomposed after a document is judged relevant?',
             [(1279, 'If a retrieved result is as short as one or two sentences'),
              (1280, 'irrelevant knowledge strips are filtered out')],
             ['A one- or two-sentence result is a strip; longer results are split into smaller units of a few sentences according to length.',
              'The fine-tuned retrieval evaluator scores the relevance of each strip and filters irrelevant strips.',
              'Relevant strips are concatenated in their original order to form internal knowledge.'],
             'Within-document refinement; old CRAG questions covered document-level judgments, actions, or external sources.'),
    question('h03', 'single_document',
             'What batching and text-preprocessing optimizations does ColBERT use to reduce padding and WordPiece tokenization overhead during offline indexing?',
             [(616, 'It sorts these documents by length'),
              (618, 'we parallelize the pre-processing across the available CPU cores')],
             ['Documents are sorted by length in groups and encoded in batches of comparable lengths, padding only to the batch maximum.',
              'Independent text preprocessing, especially WordPiece tokenization, is parallelized across CPU cores.'],
             'Indexing throughput mechanisms; old questions asked what representations are precomputed, not bucketing or CPU preprocessing.'),
    question('h04', 'single_document',
             'For dense evaluation of an uncropped test image, how does VGG convert its fully connected layers, and how does it reduce the output to final image-level class scores?',
             [(266, 'the last two FC layers to 1 × 1 conv.'),
              (267, 'the class score map is spatially averaged')],
             ['Convert the first fully connected layer to a 7x7 convolution and the final two to 1x1 convolutions, then apply the network to the whole uncropped image.',
              'Spatially average (sum-pool, in the paper wording) the class score map to a fixed-size vector.',
              'Average softmax class posteriors of the original and horizontally flipped images.'],
             'Dense inference and aggregation; old VGG questions covered filters, pooling, training, and dropout.'),
    question('h05', 'cross_document',
             'How does VGG initialize deeper configurations from configuration A, and how does this differ from the per-layer weight initialization reported in DCNN?',
             [(256, 'we initialised the ﬁrst four convolutional layers'),
              (177, 'We initialized the weights in each layer from a zero-mean Gaussian distribution')],
             ['VGG first trains the shallower configuration A with random initialization, then copies its first four convolutional and last three fully connected layers into deeper networks; intermediate layers are random.',
              'The copied VGG layers continue learning without a reduced learning rate.',
              'DCNN initializes weights in each layer from a zero-mean Gaussian with standard deviation 0.01.'],
             'Initialization transfer versus independent random initialization; old comparison asked optimizer batch/momentum/weight decay.'),
    question('h06', 'cross_document',
             'How do DCNN and VGG distribute training across multiple GPUs, and how do the GPUs exchange information in each scheme?',
             [(139, 'puts half of the kernels (or neurons) on each GPU'),
              (273, 'Multi-GPU training exploits data parallelism')],
             ['DCNN places roughly half the kernels/neurons on each of two GPUs; communication is restricted to selected layers (layer 3 sees both GPUs, layer 4 only its own).',
              'VGG uses data parallelism by splitting each image batch into GPU batches.',
              'VGG synchronously averages GPU gradients to obtain the full-batch gradient, equivalent to the single-GPU computation.'],
             'Parallelization and synchronization; no previous question asked model versus data parallelism.'),
    question('h07', 'cross_document',
             'How does the learning-rate schedule in Attention Is All You Need differ from DCNN, including what triggers the decrease in each paper?',
             [(66, 'increasing the learning rate linearly for the ﬁrst warmup_steps training steps'),
              (178, 'divide the learning rate by 10')],
             ['Transformer increases the learning rate linearly during 4000 warmup steps.',
              'After warmup Transformer decreases learning rate proportionally to inverse square root of step number.',
              'DCNN manually divides the learning rate by 10 when validation error stops improving (starting at 0.01, reduced three times).'],
             'Learning-rate control; previous training comparison did not ask schedules or trigger conditions.'),
    question('h08', 'cross_document',
             'How does the DPR end-to-end QA system select its final answer, and how does its output constraint differ from the abstractive QA capability described in RAG?',
             [(396, 'the answer is restricted to a span appearing in one or more'),
              (464, 'the reader assigns a passage selection score to each passage'),
              (465, 'is chosen as the ﬁnal answer'),
              (766, 'answer questions with free-form, abstractive text generation')],
             ['DPR uses an extractive reader and restricts answers to spans in retrieved passages.',
              'The reader scores passages and spans, then chooses the best span from the passage with the highest passage-selection score.',
              'RAG supports free-form abstractive answer generation beyond copying a passage span.'],
             'Reader answer selection and output constraint; old DPR/RAG questions addressed encoders, training, and indexes.'),
    question('h09', 'cross_document',
             'How does the DPR paper combine BM25 and DPR scores, and how does ColBERT distinguish re-ranking another retriever\'s candidates from end-to-end collection retrieval?',
             [(437, 'we obtain two initial sets of top-2000 passages'),
              (438, 'We used λ = 1.1'),
              (619, 'ColBERT can be used for re-ranking the output'),
              (627, 'index all document embeddings into faiss'),
              (628, 'the ﬁrst is an approximate stage aimed at ﬁltering')],
             ['DPR takes the union of top-2000 BM25 and top-2000 DPR passages and reranks by BM25(q,p) + lambda*sim(q,p), with lambda 1.1 selected on development accuracy.',
              'ColBERT re-ranking scores candidates returned by another retriever, typically a term-based model.',
              'ColBERT can alternatively retrieve directly from the full collection using a FAISS embedding index and approximate filtering followed by refinement.'],
             'Lexical combination and candidate-generation modes; old DPR/ColBERT comparisons covered vector representation, loss, and encoder sharing.'),
    question('h10', 'cross_document',
             'For short-answer open-domain QA, how does the correctness criterion reported by RAG differ from the criterion used by Self-RAG for PopQA and TriviaQA?',
             [(765, 'report Exact Match (EM) scores'),
              (1003, 'whether gold answers are included in the model generations')],
             ['RAG reports Exact Match scores for its open-domain QA evaluation.',
              'Self-RAG judges whether a gold answer is included in the generated text instead of strictly requiring exact matching; the raw scores therefore have different criteria.'],
             'Evaluation criterion rather than architecture or retrieval control; no previous question asked this metric distinction.'),
    question('h11', 'unanswerable',
             'Using only the supplied eight-paper corpus, what training-data size and hidden-state dimension are specified for the Mamba model in the Mamba paper?',
             [], ['State that the Mamba paper/model specification is absent from this corpus and the two requested values cannot be established; do not guess numbers.'],
             'An absent source/model specification, rather than a historical question about stock price or measured project latency.'),
    question('h12', 'unanswerable',
             'What exact ImageNet-1k top-1 accuracy did the original Transformer in Attention Is All You Need achieve under the same training protocol as VGG configuration D?',
             [], ['Explain that the corpus does not report the requested controlled ImageNet experiment for the original Transformer; do not substitute a BLEU score, a VGG result, or a later vision Transformer result.'],
             'False premise of a common cross-task experiment; prior unanswerable questions asked project timings or combined-method measurements.')
]
questions[-2]['unanswerable_rationale'] = 'The inventory contains only Transformer, AlexNet/DCNN, VGG, RAG, DPR, ColBERT, Self-RAG, and CRAG. Mamba is not supplied; a full-PDF text scan for Mamba is recorded separately. Absence is corpus-scoped, not a claim about all literature.'
questions[-1]['unanswerable_rationale'] = 'Attention Is All You Need reports translation and constituency parsing, not a controlled ImageNet classification run with VGG D. VGG reports its own visual recognition experiments; those do not establish an original-Transformer ImageNet score.'
questions[-1]['boundary_evidence'] = [evidence(71, 'On the WMT 2014 English-to-German translation task'),
                                        evidence(219, 'ImageNet Challenge 2014 submission')]

question_path = STAGE / 'candidate/holdout_v1_questions_en.json'
assert not (OUT / 'frozen_protocol.json').exists(), 'Never redefine a frozen set after execution.'
pdfs = {p.name: p for p in (ROOT / 'data/raw').rglob('*.pdf')}
pdf_texts = {name: [page.get_text() for page in pymupdf.open(path)] for name, path in pdfs.items()}
checks = []
for q in questions:
    ids = set()
    for item in q['gold_evidence'] + q.get('boundary_evidence', []):
        text = pdf_texts[item['source']][item['page'] - 1]
        matches = [c['chunk_id'] for c in CHUNKS if c['source'] == item['source']
                   and c['page'] == item['page'] and norm(item['quote']) in norm(c['text'])]
        assert norm(item['quote']) in norm(text), (q['id'], item, 'PDF mismatch')
        assert matches, (q['id'], item, 'chunk mismatch')
        checks.append({'question_id': q['id'], **item, 'pdf_verified': True, 'matched_chunk_ids': matches})
        if item in q['gold_evidence']:
            ids.update(matches)
    q['gold_chunk_ids_at_freeze'] = sorted(ids)
old = json.loads((ROOT / 'evaluation/all_papers_questions_en.json').read_text())
assert len(old) == 46 and not {norm(q['question']) for q in old} & {norm(q['question']) for q in questions}
assert sum(q['type'] == 'single_document' for q in questions) == 4
assert sum(q['type'] == 'cross_document' for q in questions) == 6
assert sum(q['type'] == 'unanswerable' for q in questions) == 2
scan = [{'source': name, 'pages': len(pages), 'mamba_occurrences': sum(len(re.findall(r'\bmamba\b', text, re.I)) for text in pages)} for name, pages in pdf_texts.items()]
assert all(row['mamba_occurrences'] == 0 for row in scan)
save(question_path, questions)
save(OUT / 'gold_verification_before_run.json', {'checks': checks, 'pdf_inventory_and_absent_source_scan': scan,
     'previous_questions': len(old), 'exact_duplicates': 0,
     'semantic_duplicate_screen': 'Assistant reviewed all old prompts and new knowledge targets before execution; see novelty_vs_previous_46. Not an independent adjudication.',
     'counts': {q['id']: len(q['gold_chunk_ids_at_freeze']) for q in questions}})
shutil.copy2(question_path, OUT / 'questions_frozen.json')
tracked = {ROOT / 'PROGRESS.md', ROOT / 'README.md', ROOT / 'main.py', ROOT / 'llm.py',
           ROOT / 'build_semantic_index.py', ROOT / 'download_arxiv_papers.py'}
for folder in ('src', 'evaluation', 'tests', 'data'):
    tracked.update(p for p in (ROOT / folder).rglob('*') if p.is_file()
                   and p.suffix in {'.py', '.json', '.md', '.pdf', '.index'} and '__pycache__' not in p.parts)
hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(tracked)}
save(OUT / 'baseline_hashes.json', hashes)
for name in ('PROGRESS.md', 'README.md'):
    shutil.copy2(ROOT / name, STAGE / 'baseline' / name)
snapshot = OUT / 'source_snapshot'
for p in sorted(tracked):
    if p.suffix == '.py' or p in (ROOT / 'PROGRESS.md', ROOT / 'README.md'):
        target = snapshot / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
print(json.dumps({'questions': len(questions), 'gold_checks': len(checks),
                  'gold_total': sum(len(q['gold_chunk_ids_at_freeze']) for q in questions),
                  'baseline_files': len(hashes), 'pdf_pages': sum(len(v) for v in pdf_texts.values())}))
