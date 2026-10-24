"""首次付费调用前冻结新题、核心/补充要求、PDF逐字出处与源码。"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normal(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text)).casefold().replace('\u00ad','')


def questions(chunks):
    def case(qid, kind, question, required, supplementary, refs):
        gold=[]
        for cid,quote in refs:
            chunk=chunks[cid]
            assert normal(quote) in normal(chunk['text']), (qid,cid,quote)
            gold.append({'source':chunk['source'],'page':chunk['page'],'quote':quote})
        return {'id':qid,'type':kind,'question':question,'required_points':required,
                'supplementary_points':supplementary,'gold_evidence':gold,
                'novelty':'New question and required facts; same known corpus, not an unseen-knowledge claim.'}
    return [
        case('a01','single_document',
             'In Attention Is All You Need, which three transformations share a weight matrix, and how are those weights scaled in the embedding layers?',
             ['The encoder/input embedding, decoder/output embedding, and pre-softmax linear transformation share the same weight matrix.',
              'In the embedding layers the weights are multiplied by sqrt(d_model).'],
             ['Naming the cited predecessor paper or giving the numerical base-model dimension is optional.'],
             [(44,'we share the same weight matrix between the two embedding layers and the pre-softmax linear transformation')]),
        case('a02','single_document',
             'What k, n, alpha, and beta values does DCNN use for local response normalization, and is that normalization applied before or after ReLU?',
             ['The LRN hyperparameters are k=2, n=5, alpha=10^-4, and beta=0.75.',
              'This normalization is applied after the ReLU nonlinearity in the selected layers.'],
             ['Explaining the brightness-normalization name or reproducing the entire formula is optional.'],
             [(145,'we used k = 2, n = 5, α = 10−4, and β = 0.75'),
              (145,'We applied this normalization after applying the ReLU nonlinearity')]),
        case('a03','single_document',
             'What upper and lower retrieval-confidence thresholds does CRAG report for PopQA and for Biography?',
             ['PopQA uses upper threshold 0.59 and lower threshold -0.99.',
              'Biography uses upper threshold 0.95 and lower threshold -0.91.'],
             ['The PubQA/ARC settings and a full explanation of all three action types are optional.'],
             [(1387,'they were set as (0.59, -0.99) in PopQA'),
              (1387,'as well as (0.95, -0.91) in Biography')]),
        case('a04','cross_document',
             'For Transformer translation and for the original RAG paper\'s Open-MSMarco and Jeopardy generation experiments, what beam size is used in each, and how many documents are retrieved for those RAG experiments?',
             ['Transformer translation uses beam size 4.',
              'RAG uses beam size 4 for the specified generation experiments.',
              'RAG uses ten retrieved documents for Open-MSMarco and Jeopardy generation (both RAG-Token and RAG-Sequence).'],
             ['Transformer length penalty and RAG Fast/Thorough decoding details are optional.'],
             [(73,'We used beam search with a beam size of 4'),
              (903,'For Open-MSMarco and Jeopardy question generation, we report test numbers using ten retrieved documents'),
              (903,'We use a beam size of four')]),
        case('a05','cross_document',
             'What training batch size and learning rate are reported for the main DPR retriever and for ColBERT fine-tuning?',
             ['DPR main retriever training uses batch size 128.',
              'DPR encoder training uses learning rate 10^-5.',
              'ColBERT fine-tuning uses batch size 32.',
              'ColBERT fine-tuning uses learning rate 3*10^-6.'],
             ['Negative passage composition, epoch counts, warm-up and embedding dimensions are optional.'],
             [(435,'with a batch size of 128'),(436,'with a learning rate of 10−5'),
              (641,'learning rate 3 × 10−6 with a batch size 32')]),
        case('a06','cross_document',
             'How do DCNN and VGG center RGB pixel values before the network, and from which data are their subtracted means computed?',
             ['DCNN subtracts the mean activity over the training set from each pixel and uses centered raw RGB values.',
              'VGG subtracts the mean RGB value computed on the training set from each pixel.'],
             ['Resizing/cropping dimensions, data augmentation and a stronger claim about spatial mean-image granularity are optional.'],
             [(128,'subtracting the mean activity over the training set from each pixel'),
              (232,'subtracting the mean RGB value, computed on the training set, from each pixel')]),
        case('a07','unanswerable',
             'Using only the supplied corpus, what hidden-layer count and context-window length does the Gemma 2 technical report specify for Gemma 2 9B?',
             ['The Gemma 2 primary report is absent; the supplied corpus cannot establish either requested specification and neither value should be guessed.'],
             ['An exhaustive inventory of the eight supplied papers is optional.'], []),
        case('a08','unanswerable',
             'What exact monetary training bill in US dollars and energy consumption in kWh does the original DPR paper report for training its main retriever?',
             ['The supplied DPR paper does not establish an exact USD training bill or kWh consumption; state both gaps without inventing either measurement.'],
             ['Available GPU, epoch and batch-size details may be given as context but cannot substitute for dollars or kWh.'], []),
    ]


def main():
    if (OUT/'frozen_protocol.json').exists():
        raise RuntimeError('Already frozen; keep original inputs and failed results.')
    sys.path.insert(0,str(ROOT))
    import fitz
    from src.api_llm import load_settings
    folder=ROOT/'data/processed/versions/all-papers-8-20261020'
    chunks=json.loads((folder/'chunks.json').read_text())
    qs=questions(chunks)
    banks=[*sorted((ROOT/'evaluation').glob('*questions*.json')),
           ROOT/'evaluation/results/agent_p25_20261021/questions_frozen.json']
    prior={q['question'] for p in banks for q in json.loads(p.read_text())}
    assert not ({q['question'] for q in qs} & prior)
    pdfs={p.name:p for p in (ROOT/'data/raw').rglob('*.pdf')}
    checks=[]
    squash=lambda text:normal(text).replace('-','').replace('–','').replace('−','')
    for q in qs:
        ids=set()
        for ref in q['gold_evidence']:
            matches=[c['chunk_id'] for c in chunks if c['source']==ref['source'] and c['page']==ref['page']
                     and normal(ref['quote']) in normal(c['text'])]
            assert matches
            ids.update(matches)
            with fitz.open(pdfs[ref['source']]) as doc:
                text=doc[ref['page']-1].get_text()
            assert squash(ref['quote']) in squash(text), (q['id'],ref)
            checks.append({'id':q['id'],**ref,'chunk_ids':matches,'pdf_quote_verified':True})
        q['gold_chunk_ids_at_freeze']=sorted(ids)
    assert not any('gemma' in c['text'].casefold() for c in chunks)
    with fitz.open(pdfs['2004.04906v3.pdf']) as doc:
        boundary=[{'page':i+1,'text':p.get_text()} for i,p in enumerate(doc)
                  if re.search(r'cost|hour|gpu|train|energy|dollar|kwh',p.get_text(),re.I)]
    save(OUT/'boundary_source_review.json',{'gemma_2_absent_in_chunks':True,'sources':sorted(pdfs),
                                          'dpr_training_or_resource_pages':boundary})
    save(OUT/'questions_frozen.json',qs)
    save(OUT/'gold_verification_before_run.json',checks)
    source_paths=[ROOT/'main.py',ROOT/'agent.py',*sorted((ROOT/'src').glob('*.py')),
                  ROOT/'evaluation/metrics.py',ROOT/'tests/test_main_auto.py',
                  OUT/'prepare.py',OUT/'run_comparison.py',OUT/'test_driver.py',
                  OUT/'review_protocol.md',OUT/'questions_frozen.json',
                  folder/'chunks.json',folder/'faiss.index',folder/'manifest.json']
    public={k:load_settings().get(k) for k in ('base_url','model','chat_options')}
    protocol={'name':'P2 Auto frozen 8-question three-arm same-corpus closeout',
              'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'kb_version':folder.name,
              'question_ids':[q['id'] for q in qs],
              'cohorts':{'single_document':3,'cross_document':3,'unanswerable':2},
              'max_actual_chat_attempts':184,'max_actual_chat_attempts_per_question':23,
              'automatic_retries':0,'api_public_settings':public,
              'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in source_paths},
              'reviewer':'Same coding assistant; not independent or blind.',
              'scope':'Shared actual initial retrieval; RAG vs fixed Agent vs Auto; no P3.'}
    save(OUT/'frozen_protocol.json',protocol)
    for path in source_paths:
        if path.is_relative_to(OUT):continue
        target=OUT/'source_snapshot'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(path.read_bytes())
    print(json.dumps({'questions':len(qs),'pdf_quote_checks':len(checks),'max_actual_attempts':184}))


if __name__=='__main__':main()
