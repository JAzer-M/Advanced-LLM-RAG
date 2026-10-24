"""P2.5运行前准备：冻结问题、逐字Gold、原PDF校验与现有资产哈希。无API调用。"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def normal(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text)).casefold().replace('\u00ad', '')


def questions(chunks):
    def case(qid, kind, query, points, refs, note):
        evidence = []
        for cid, quote in refs:
            c = chunks[cid]
            assert normal(quote) in normal(c['text']), (qid, cid, quote)
            evidence.append({'source': c['source'], 'page': c['page'], 'quote': quote})
        return {'id': qid, 'type': kind, 'question': query, 'reference_points': points,
                'gold_evidence': evidence, 'novelty_and_scope': note}
    return [
        case('b01', 'single_document',
             'Which optimizer and beta1, beta2, and epsilon values does the Transformer in Attention Is All You Need use?',
             ['The optimizer is Adam.', 'beta1=0.9, beta2=0.98 and epsilon=10^-9.'],
             [(66, 'We used the Adam optimizer')], 'Optimizer constants; distinct from old learning-rate schedule questions.'),
        case('b02', 'single_document',
             'How does DCNN initialize neuron biases in different layers, and why does it use positive biases in selected layers?',
             ['Biases are 1 in convolutional layers 2, 4, 5 and fully connected hidden layers.',
              'Biases in the remaining layers are 0.',
              'Positive initial biases accelerate early learning by supplying ReLUs with positive inputs.'],
             [(177, 'We ini- tialized the neuron biases'), (178, 'with the constant 0')], 'Bias initialization rather than earlier weight-initialization comparison.'),
        case('b03', 'single_document',
             'In VGG multi-scale training, how is the training scale S sampled, what crop size is used, and how is the multi-scale model initialized?',
             ['Each image samples S from [256,512]; S is the shortest side of the isotropically rescaled image.',
              'The input crop remains 224x224.',
              'All layers of a same-configuration single-scale model pretrained at S=384 are fine-tuned.'],
             [(260, 'smallest side of an isotropically-rescaled training image'),
              (262, 'randomly sampling S from a certain range'), (264, 'fine-tuning all layers of a single-scale model')],
             'Scale jitter and initialization; fixed-scale/model-initialization facts in old questions are related but not this question.'),
        case('b04', 'single_document',
             'After the token embeddings are projected in ColBERT, how are they normalized, and what equivalence and value range does this give to their dot products?',
             ['Each output embedding is normalized to L2 norm 1.',
              'The dot product of two normalized embeddings equals cosine similarity and lies in [-1,1].'],
             [(608, 'each has L2 norm equal to one')], 'Normalization mechanism; related to previously tested MaxSim, but a new question and scoring points.'),
        case('b05', 'cross_document',
             'Which checkpoints are averaged for Transformer base and big models, and how does this differ from the way VGG combines multiple model predictions?',
             ['Transformer base uses one model formed by averaging its last 5 checkpoints; big averages its last 20 checkpoints.',
              'VGG averages softmax class posteriors from several models.',
              'The distinction is averaging model checkpoints versus averaging model output probabilities.'],
             [(73, 'averaging the last 5 checkpoints'), (296, 'averaging their soft-max class posteriors')], 'Two different averaging operations; no requirement to compare measured accuracy across tasks.'),
        case('b06', 'cross_document',
             'What do DCNN and VGG report about the usefulness of local response normalization, and what computational costs does VGG mention?',
             ['DCNN reports that response normalization improves generalization and reduces top-1/top-5 errors (1.4/1.2 percentage points if numbers are supplied).',
              'VGG finds no performance improvement and generally omits LRN, with the A-LRN comparison as an exception.',
              'VGG says LRN increases memory consumption and computation time.'],
             [(146, 'reduces our top-1 and top-5 error rates'), (235, 'increased memory con- sumption and computation time'),
              (279, 'A-LRN network')], 'New LRN comparison; preserve VGG exception instead of saying every model omits normalization.'),
        case('b07', 'cross_document',
             "What does DPR's top-k retrieval accuracy count, and which metrics does Self-RAG use for correctness, fluency, and citations on ASQA?",
             ['DPR counts the fraction of questions whose top-k retrieved passages contain an answer span.',
              'Self-RAG uses str-em for ASQA correctness.', 'Self-RAG uses MAUVE for ASQA fluency.',
              'Self-RAG uses citation precision and recall for ASQA citations.'],
             [(400, 'fraction of ques- tions'), (1004, 'citation precision and recall')], 'Retrieval success versus long-form generation metrics; not old short-answer correctness comparison.'),
        case('b08', 'cross_document',
             'What hardware and approximate training duration do the Transformer base model and DCNN report for their own experiments?',
             ['Transformer base trains on 8 NVIDIA P100 GPUs for 100000 steps or about 12 hours.',
              'DCNN trains on 2 NVIDIA GTX 580 GPUs with 3GB each for about 5-6 days.'],
             [(64, '8 NVIDIA P100 GPUs'), (65, '100,000 steps or 12 hours'), (179, '5–6 days on two NVIDIA GTX 580 3GB GPUs')],
             'Reported paper training resources; not the old unmeasured local-project latency questions.'),
        case('b09', 'cross_document',
             "How does RAG-Sequence's Thorough Decoding score a candidate absent from a document's beam, and how does Self-RAG use critique-token probabilities to score output segments?",
             ['RAG-Sequence runs an extra forward pass for each document whose beam did not contain the candidate.',
              'It multiplies generator probability by retriever probability and sums across documents for the marginal.',
              'Self-RAG uses segment-level beam search and a weighted linear sum of normalized critique-token probabilities to update segment scores.'],
             [(757, 'additional forward pass for each document'), (995, 'linear weighted sum of the normalized probability')],
             'New RAG decoding component paired with a previously covered Self-RAG scoring mechanism; not unseen atomic knowledge.'),
        case('b10', 'cross_document',
             'How does Self-RAG obtain reflection-token supervision for its own critic, and how does CRAG use ChatGPT before a web search?',
             ['Self-RAG prompts GPT-4 for reflection-token labels and distills that supervision into its own critic.',
              'CRAG uses ChatGPT to rewrite the input question into a keyword-based search query.'],
             [(982, 'prompting GPT-4 to generate reflection tokens'), (1283, 'queries composed of keywords by ChatGPT')],
             'Different roles of teacher/rewriter models; related to prior critic and external-retrieval questions.'),
        case('b11', 'unanswerable',
             'Using only the supplied corpus, what training-token count and context-window length are specified for Mistral 7B in the Mistral 7B paper?',
             ['The Mistral 7B primary paper is absent from the eight-paper corpus; the requested specifications cannot be established and must not be guessed.'],
             [], 'Absent primary paper; related boundary type to old Mamba, with a new target.'),
        case('b12', 'unanswerable',
             'What exact annual index-refresh cost in US dollars and fixed index-refresh interval does the original RAG paper report?',
             ['The RAG paper does not specify an annual USD cost or a fixed refresh interval; explain the missing measurements without inventing either value.'],
             [], 'Present paper, absent operational measurements; qualitative update mechanisms are not numerical cost/interval evidence.'),
    ]


def main():
    if (OUT / 'frozen_protocol.json').exists():
        raise RuntimeError('Already frozen; do not overwrite the question set or protocol.')
    sys.path.insert(0, str(ROOT))
    import fitz
    from src.api_llm import load_settings
    folder = ROOT / 'data/processed/versions/all-papers-8-20261020'
    chunks = json.loads((folder / 'chunks.json').read_text())
    qs = questions(chunks)
    old = json.loads((ROOT / 'evaluation/all_papers_questions_en.json').read_text()) + json.loads((ROOT / 'evaluation/holdout_v1_questions_en.json').read_text())
    assert not ({q['question'] for q in qs} & {q['question'] for q in old})
    pdfs = {p.name: p for p in (ROOT / 'data/raw').rglob('*.pdf')}
    checks = []
    for q in qs:
        ids = set()
        for e in q['gold_evidence']:
            matches = [c['chunk_id'] for c in chunks if c['source'] == e['source'] and c['page'] == e['page'] and normal(e['quote']) in normal(c['text'])]
            assert matches
            ids.update(matches)
            with fitz.open(pdfs[e['source']]) as doc:
                page = doc[e['page'] - 1].get_text()
            # PDF换行连字符与分块清理可能不同；保留原页文本便于审阅。
            squash = lambda t: normal(t).replace('-', '').replace('–', '').replace('−', '')
            assert squash(e['quote']) in squash(page), (q['id'], e)
            checks.append({'id': q['id'], **e, 'chunk_ids': matches, 'pdf_quote_verified': True})
        q['gold_chunk_ids_at_freeze'] = sorted(ids)
    assert not any('mistral' in source.casefold() for source in pdfs)
    rag = pdfs['2005.11401v4.pdf']
    with fitz.open(rag) as doc:
        boundary_pages = [{'page': i+1, 'text': p.get_text()} for i,p in enumerate(doc) if re.search(r'cost|updat|hot.swap|dollar|annual', p.get_text(), re.I)]
    save(OUT / 'boundary_source_review.json', {'mistral_primary_paper_absent': True, 'corpus_sources': sorted(pdfs), 'rag_update_or_cost_pages': boundary_pages})
    save(OUT / 'questions_frozen.json', qs)
    save(OUT / 'gold_verification_before_run.json', checks)
    exclude = {'.git', '.venv', '__pycache__', '.pytest_cache', '.DS_Store'}
    baseline = {str(p.relative_to(ROOT)): sha(p) for p in ROOT.rglob('*') if p.is_file() and not p.is_relative_to(OUT) and not any(s in exclude for s in p.relative_to(ROOT).parts)}
    save(OUT / 'baseline_hashes.json', baseline)
    source_paths = [ROOT/'agent.py', ROOT/'main.py', *sorted((ROOT/'src').glob('*.py')), ROOT/'evaluation/metrics.py',
                    OUT/'run_comparison.py', OUT/'test_driver.py', OUT/'prepare.py', OUT/'questions_frozen.json', OUT/'review_protocol.md',
                    folder/'manifest.json', folder/'chunks.json', folder/'faiss.index']
    public = {key: load_settings().get(key) for key in ('base_url', 'model', 'chat_options')}
    protocol = {'name': 'P2.5 paired frozen same-corpus holdout', 'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
                'question_ids': [q['id'] for q in qs], 'kb_version': folder.name, 'max_actual_chat_attempts': 156,
                'max_actual_chat_attempts_per_question': 13, 'automatic_retries': 0,
                'api_public_settings': public, 'source_hashes': {str(p.relative_to(ROOT)): sha(p) for p in source_paths},
                'comparison': 'Shared fresh fixed-RAG retrieval; original RAG generation versus added existing Agent loop and review.',
                'cohorts': {'single_document': 4, 'cross_document': 6, 'unanswerable': 2},
                'reviewer': 'Same coding assistant; not an independent blind review.'}
    save(OUT/'frozen_protocol.json', protocol)
    snap = OUT/'source_snapshot'
    for p in source_paths:
        if p.is_relative_to(OUT): continue
        target = snap/p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())
    print(json.dumps({'questions': len(qs), 'gold_pdf_checks': len(checks), 'protected_existing_files': len(baseline), 'max_chat_attempts': 156}))


if __name__ == '__main__':
    main()
