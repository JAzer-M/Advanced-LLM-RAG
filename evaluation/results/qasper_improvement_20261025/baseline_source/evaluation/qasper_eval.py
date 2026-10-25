"""QASPER 独立评测：固定抽样 → 下载 arXiv PDF 并建库 → RAG/Agent/Auto 同条件运行 → 官方口径评分 + 大模型判分。

每一步都可断点续跑：已存在的结果文件不会重算，失败的生成请求也不会自动重试。
运行：.venv/bin/python evaluation/qasper_eval.py <prepare|build|run|score|judge|report>
"""
import argparse
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import random
import re
import ssl
import string
import subprocess
import sys
import tarfile
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RUN = '20261024'
SEED = 20261024
TARGET_QUESTIONS = 50
MODES = ('rag', 'agent', 'auto')
KB_VERSION = f'qasper-test50-{RUN}'
OUT = ROOT / f'evaluation/results/qasper_{RUN}'
CACHE = ROOT / 'evaluation/qasper_cache'                 # 数据集原文件（含论文全文），只留本机
RAW = ROOT / f'data/raw/qasper-test50-{RUN}'              # 论文 PDF，只留本机
DATASET_URL = 'https://qasper-dataset.s3.us-west-2.amazonaws.com/qasper-test-and-evaluator-v0.3.tgz'
ARXIV_ID = re.compile(r'\d{4}\.\d{4,5}')


def tls_context():
    """python.org 版 macOS Python 默认不带根证书；与 src/arxiv_tools.py 一样加载 certifi 证书。"""
    import certifi
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


# ---------- 官方口径：归一化、词级 F1、段落 F1，各标注者取最大值 ----------
def normalize_answer(text):
    text = text.lower()
    text = ''.join(ch for ch in text if ch not in set(string.punctuation))
    text = re.sub(r'\b(a|an|the)\b', ' ', text)
    return ' '.join(text.split())


def token_f1(prediction, reference):
    pred, ref = normalize_answer(prediction).split(), normalize_answer(reference).split()
    if not pred or not ref:
        return float(pred == ref)
    same = sum((Counter(pred) & Counter(ref)).values())
    if same == 0:
        return 0.0
    precision, recall = same / len(pred), same / len(ref)
    return 2 * precision * recall / (precision + recall)


def paragraph_f1(prediction, reference):
    if not reference and not prediction:
        return 1.0
    same = len(set(reference) & set(prediction))
    if same == 0:
        return 0.0
    precision, recall = same / len(prediction), same / len(reference)
    return 2 * precision * recall / (precision + recall)


def references(question):
    """每位标注者一条参考答案；证据只取正文段落（去掉 FLOAT SELECTED 图表引用），对应官方 text_evidence_only。"""
    refs = []
    for item in question['answers']:
        answer = item['answer']
        if answer.get('unanswerable'):
            text, kind = 'Unanswerable', 'none'
        elif answer.get('extractive_spans'):
            text, kind = ', '.join(answer['extractive_spans']), 'extractive'
        elif answer.get('free_form_answer'):
            text, kind = answer['free_form_answer'], 'abstractive'
        elif answer.get('yes_no') is not None:
            text, kind = ('Yes' if answer['yes_no'] else 'No'), 'boolean'
        else:
            continue
        evidence = [e for e in answer.get('evidence', []) if 'FLOAT SELECTED' not in e]
        refs.append({'answer': text, 'type': kind, 'evidence': evidence})
    return refs


# ---------- 系统输出 → 评测用答案与证据 ----------
CITATION = re.compile(r'\s*\[\d+(?:\s*[,，、]\s*\d+)*\]')
DECLINE = re.compile(
    r"(not (?:explicitly |directly |clearly )?(?:mention|state|report|provide|specif|discuss|describ|includ|give|list|address|contain)"
    r"|no (?:information|mention|evidence|details|explicit)|cannot (?:be )?(?:determin|answer|find|confirm|verif)"
    r"|unable to (?:find|determine|answer|verify)|insufficient (?:evidence|information)|does not appear"
    r"|未(?:提及|提供|说明|报告)|无法(?:确定|回答|核实|找到))", re.I)


def clean_answer(answer):
    text = CITATION.sub('', answer or '')
    return re.sub(r'[*_`#]+', '', text).strip()


def predicted_answer(result):
    """回答很短且第一句就说明论文未提供该信息时，按官方约定记为 Unanswerable；否则用去掉引用编号的全文。"""
    if result.get('status') == 'failed':
        return '', 'failed'
    text = clean_answer(result.get('answer'))
    first = re.split(r'(?<=[.!?。！？])\s', text, maxsplit=1)[0]
    if len(text.split()) <= 80 and DECLINE.search(first):
        return 'Unanswerable', 'declined'
    return text, 'answered'


def shingles(text, k=5):
    words = re.findall(r'[a-z0-9]+', text.lower())
    if len(words) < k:
        return {tuple(words)} if words else set()
    return {tuple(words[i:i + k]) for i in range(len(words) - k + 1)}


def align(chunk_text, paragraphs, threshold=0.5):
    """系统分块与 QASPER 段落边界不同：段落至少一半的 5 词片段落在分块中（或反之）即视为同一证据。"""
    chunk = shingles(chunk_text)
    matched = []
    for paragraph in paragraphs:
        para = shingles(paragraph)
        if not para or not chunk:
            continue
        overlap = len(para & chunk)
        if overlap / len(para) >= threshold or overlap / len(chunk) >= threshold:
            matched.append(paragraph)
    return matched


def evidence_sets(result, paper):
    """返回（回答实际引用的段落，检索选入上下文的段落），均已对齐到 QASPER 原文段落。"""
    registry = result.get('ledger', {}).get('citation_registry', [])
    cited = sorted({int(n) for group in re.findall(r'\[(\d+(?:\s*[,，、]\s*\d+)*)\]', result.get('answer') or '')
                    for n in re.split(r'\s*[,，、]\s*', group)})
    paragraphs = [p for section in paper['full_text'] for p in section['paragraphs'] if p and p.strip()]

    def aligned(entries):
        found = []
        for entry in entries:
            if Path(entry.get('source', '')).stem != paper['id']:
                continue
            for paragraph in align(entry.get('text', ''), paragraphs):
                if paragraph not in found:
                    found.append(paragraph)
        return found
    cited_entries = [registry[n - 1] for n in cited if 1 <= n <= len(registry)]
    return aligned(cited_entries), aligned(registry)


# ---------- 1. 固定抽样并下载 PDF ----------
def fetch_dataset():
    CACHE.mkdir(parents=True, exist_ok=True)
    archive = CACHE / Path(DATASET_URL).name
    if not archive.exists():
        print('下载 QASPER 测试集与官方评测脚本：', DATASET_URL)
        with urlopen(Request(DATASET_URL, headers={'User-Agent': 'PaperLens-QASPER-eval'}), timeout=120,
                     context=tls_context()) as response:
            archive.write_bytes(response.read())
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            name = Path(member.name).name
            if member.isfile() and name.endswith(('.json', '.py')) and not (CACHE / name).exists():
                (CACHE / name).write_bytes(tar.extractfile(member).read())
    test = sorted(CACHE.glob('qasper-test*.json'))
    if not test:
        raise SystemExit('压缩包中没有找到 qasper-test*.json。')
    return archive, test[0]


def download_pdf(paper_id):
    target = RAW / f'{paper_id}.pdf'
    if target.exists():
        return {'status': 'existing', 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    import pymupdf
    time.sleep(3.1)  # arXiv 建议的请求间隔
    url = f'https://arxiv.org/pdf/{paper_id}'
    try:
        with urlopen(Request(url, headers={'User-Agent': 'PaperLens-QASPER-eval (local research)'}), timeout=60,
                     context=tls_context()) as response:
            body, final = response.read(), response.geturl()
        with pymupdf.open(stream=body, filetype='pdf') as pdf:
            pages = len(pdf)
        if not 1 <= pages <= 200:
            raise ValueError(f'页数 {pages} 超出入库范围')
    except Exception as exc:
        return {'status': 'failed', 'error': f'{type(exc).__name__}: {exc}', 'url': url}
    RAW.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    return {'status': 'downloaded', 'url': final, 'pages': pages, 'bytes': len(body),
            'sha256': hashlib.sha256(body).hexdigest()}


def prepare(args):
    if (OUT / 'frozen_sample.json').exists():
        print('抽样已冻结，不重新抽样：', OUT / 'frozen_sample.json')
        return
    archive, test_path = fetch_dataset()
    data = load(test_path)
    ids = sorted(pid for pid in data if ARXIV_ID.fullmatch(pid))
    random.Random(SEED).shuffle(ids)
    papers, questions, downloads, total = [], [], {}, 0
    for pid in ids:
        if total >= TARGET_QUESTIONS:
            break
        qas = [q for q in data[pid]['qas'] if references(q)]
        if not qas:
            continue
        downloads[pid] = download_pdf(pid)
        print(pid, downloads[pid]['status'], len(qas), '题', flush=True)
        if downloads[pid]['status'] == 'failed':
            continue  # 下载失败的论文整篇跳过，按固定顺序取下一篇
        papers.append({'arxiv_id': pid, 'title': data[pid]['title']})
        for q in qas:
            questions.append({'question_id': q['question_id'], 'paper_id': pid, 'paper_title': data[pid]['title'],
                              'question': q['question'], 'references': references(q)})
        total += len(qas)
    dump(OUT / 'paper_manifest.json', {'source': 'QASPER v0.3 test split (CC BY 4.0)', 'papers': papers})
    dump(OUT / 'downloads.json', downloads)
    dump(OUT / 'frozen_sample.json', {
        'dataset': DATASET_URL, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'test_file': test_path.name, 'seed': SEED, 'target_questions': TARGET_QUESTIONS,
        'eligible_arxiv_papers': len(ids), 'papers': len(papers), 'questions': questions,
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    print(f'已冻结 {len(papers)} 篇论文、{len(questions)} 道题 → {OUT / "frozen_sample.json"}')


# ---------- 2. 建库：独立版本，不切换当前库，不影响网页库 ----------
def build(args):
    sample = load(OUT / 'frozen_sample.json')
    if (ROOT / 'data/processed/versions' / KB_VERSION).exists():
        print('知识库已存在：', KB_VERSION)
        return
    names = sorted(p.name for p in RAW.glob('*.pdf'))
    expected = sorted({q['paper_id'] + '.pdf' for q in sample['questions']})
    if names != expected:
        raise SystemExit(f'PDF 集合与抽样不一致：{set(names) ^ set(expected)}')
    command = [sys.executable, str(ROOT / 'build_semantic_index.py'), '--version', KB_VERSION,
               '--raw-dir', str(RAW), '--paper-manifest', str(OUT / 'paper_manifest.json'),
               '--two-column-files', *names]  # QASPER 论文多为 ACL 双栏排版，统一按双栏读取
    subprocess.run(command, cwd=ROOT, check=True)


# ---------- 3. 三种模式同条件运行 ----------
def cached_models(pipeline):
    """每题重复加载同一检索模型只浪费时间；缓存模型对象，不改变检索、预算或回答逻辑。"""
    cache = {}
    original_embedding, original_cross = pipeline.load_embedding_model, pipeline.CrossEncoder

    def embedding(*a, **k):
        key = ('embedding', repr(a), repr(sorted(k.items())))
        if key not in cache:
            cache[key] = original_embedding(*a, **k)
        return cache[key]

    def cross(*a, **k):
        key = ('cross', repr(a), repr(sorted(k.items())))
        if key not in cache:
            cache[key] = original_cross(*a, **k)
        return cache[key]
    pipeline.load_embedding_model, pipeline.CrossEncoder = embedding, cross


def run(args):
    sample = load(OUT / 'frozen_sample.json')
    import main as pipeline
    from src import api_llm
    cached_models(pipeline)
    settings = {k: api_llm.load_settings().get(k) for k in ('base_url', 'model', 'chat_options')}
    dump(OUT / 'run_settings.json', {'kb_version': KB_VERSION, 'modes': MODES, 'allow_network': False, **settings})
    todo = [(q, m) for q in sample['questions'] for m in MODES
            if not (OUT / 'runs' / q['question_id'] / f'{m}.json').exists()]
    print(f'待运行 {len(todo)} 次（已完成的跳过）；模型 {settings["model"]}，知识库 {KB_VERSION}', flush=True)
    for n, (q, mode) in enumerate(todo, 1):
        folder = OUT / 'runs' / q['question_id']
        folder.mkdir(parents=True, exist_ok=True)
        log, started = io.StringIO(), time.monotonic()
        try:
            with redirect_stdout(log), redirect_stderr(log):
                result = pipeline.main(q['question'], kb_version=KB_VERSION, mode=mode,
                                       output_dir=(folder / f'{mode}_run') if mode != 'rag' else None)
        except Exception as exc:
            result = {'query': q['question'], 'mode': mode, 'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'}
        result = result or {'query': q['question'], 'mode': mode, 'status': 'failed', 'error': 'no result'}
        result['eval_elapsed_seconds'] = round(time.monotonic() - started, 2)
        (folder / f'{mode}.log').write_text(log.getvalue(), encoding='utf-8')
        dump(folder / f'{mode}.json', result)
        usage = result.get('api_summary', {}).get('reported_usage', {}).get('total_tokens', 0)
        print(f'[{n}/{len(todo)}] {q["question_id"][:10]} {mode:5s} {result.get("status")} '
              f'{result["eval_elapsed_seconds"]}s {usage} token', flush=True)


# ---------- 4. 评分 ----------
def score(args):
    sample = load(OUT / 'frozen_sample.json')
    _, test_path = fetch_dataset()
    papers = load(test_path)
    rows, predictions = [], {m: [] for m in MODES}
    for q in sample['questions']:
        paper = {**papers[q['paper_id']], 'id': q['paper_id']}
        for mode in MODES:
            path = OUT / 'runs' / q['question_id'] / f'{mode}.json'
            if not path.exists():
                continue
            result = load(path)
            answer, kind = predicted_answer(result)
            cited, retrieved = evidence_sets(result, paper)
            refs = q['references']
            api = result.get('api_summary', {})
            rows.append({
                'question_id': q['question_id'], 'mode': mode, 'status': result.get('status'),
                'prediction_kind': kind, 'gold_types': sorted({r['type'] for r in refs}),
                'gold_majority_unanswerable': sum(r['type'] == 'none' for r in refs) * 2 > len(refs),
                'answer_f1': max(token_f1(answer, r['answer']) for r in refs),
                'evidence_f1': max(paragraph_f1(cited, r['evidence']) for r in refs),
                'retrieved_gold_evidence': any(set(retrieved) & set(r['evidence']) for r in refs if r['evidence']),
                'has_gold_evidence': any(r['evidence'] for r in refs),
                'requests': api.get('attempts', 0), 'tokens': api.get('reported_usage', {}).get('total_tokens', 0),
                'seconds': result.get('eval_elapsed_seconds')})
            predictions[mode].append({'question_id': q['question_id'], 'predicted_answer': answer,
                                      'predicted_evidence': cited})
    dump(OUT / 'scores/per_question.json', rows)
    # 用官方评测脚本交叉核对本脚本的数字；它的接口若与预期不同，只记录输出，不影响主结果。
    official, evaluator, gold = {}, CACHE / 'qasper_evaluator.py', CACHE / 'gold_subset.json'
    qids = {q['question_id'] for q in sample['questions']}
    subset = {pid: {**papers[pid], 'qas': [x for x in papers[pid]['qas'] if x['question_id'] in qids]}
              for pid in {q['paper_id'] for q in sample['questions']}}
    gold.write_text(json.dumps(subset), encoding='utf-8')
    for mode in MODES:
        pred_path = OUT / f'scores/predictions_{mode}.jsonl'
        pred_path.write_text(''.join(json.dumps(p, ensure_ascii=False) + '\n' for p in predictions[mode]), encoding='utf-8')
        if evaluator.exists():
            done = subprocess.run([sys.executable, str(evaluator), '--predictions', str(pred_path), '--gold', str(gold),
                                   '--text_evidence_only'], capture_output=True, text=True)
            official[mode] = {'returncode': done.returncode, 'stdout': done.stdout[-4000:], 'stderr': done.stderr[-2000:]}
    dump(OUT / 'scores/official_evaluator.json', official)
    print(f'已评分 {len(rows)} 条运行 → {OUT / "scores"}')


# ---------- 5. 大模型判分：同一模型服务，作为 F1 之外的补充，偏差在报告中说明 ----------
JUDGE = """You are grading an answer to a question about an NLP research paper.
Several human annotators who read the full paper wrote the reference answers below. "Unanswerable" means the
annotator found that the paper does not contain the answer.

Question: {question}

Reference answers:
{references}

System answer:
{answer}

Grade the system answer:
- "correct": it conveys the key information of at least one reference answer (extra correct detail is fine),
  or the references are Unanswerable and the system says the paper does not provide the information.
- "partially_correct": it gets part of the key information right but misses or garbles an essential part.
- "incorrect": wrong, contradicts the references, answers a different question, or claims the paper does not
  provide information that a reference answer gives.
Also report "declined": true if the system says the information is not available in the paper.

Return only JSON: {{"verdict": "correct|partially_correct|incorrect", "declined": true|false, "reason": "one sentence"}}"""


def judge(args):
    from src import api_llm
    from src.model_json import loads_model_json
    sample = load(OUT / 'frozen_sample.json')
    for q in sample['questions']:
        refs = '\n'.join(f'- ({r["type"]}) {r["answer"]}' for r in q['references'])
        for mode in MODES:
            source = OUT / 'runs' / q['question_id'] / f'{mode}.json'
            target = OUT / 'judge' / q['question_id'] / f'{mode}.json'
            if not source.exists() or target.exists():
                continue
            result = load(source)
            prompt = JUDGE.format(question=q['question'], references=refs,
                                  answer=clean_answer(result.get('answer')) or '(empty)')
            try:
                reply = api_llm.chat_completion(prompt)
                verdict = loads_model_json(reply['answer'])
                if verdict.get('verdict') not in ('correct', 'partially_correct', 'incorrect'):
                    raise ValueError(f'unexpected verdict: {verdict!r}')
                record = {'status': 'completed', **verdict, 'usage': reply.get('usage')}
            except Exception as exc:
                record = {'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'}
            dump(target, record)
            print(q['question_id'][:10], mode, record.get('verdict', record['status']), flush=True)


# ---------- 6. 汇总 ----------
def report(args):
    rows = load(OUT / 'scores/per_question.json')

    def mean(values):
        return round(sum(values) / len(values), 4) if values else None
    summary = {}
    for mode in MODES:
        mine = [r for r in rows if r['mode'] == mode]
        verdicts = []
        for r in mine:
            path = OUT / 'judge' / r['question_id'] / f'{mode}.json'
            verdicts.append(load(path) if path.exists() else {'status': 'missing'})
        judged = [v for v in verdicts if v.get('status') == 'completed']
        answerable = [r for r in mine if not r['gold_majority_unanswerable']]
        unanswerable = [r for r in mine if r['gold_majority_unanswerable']]
        summary[mode] = {
            'runs': len(mine), 'failed': sum(r['status'] == 'failed' for r in mine),
            'answer_f1': mean([r['answer_f1'] for r in mine]),
            'answer_f1_by_type': {t: mean([r['answer_f1'] for r in mine if t in r['gold_types']])
                                  for t in ('extractive', 'abstractive', 'boolean', 'none')},
            'evidence_f1': mean([r['evidence_f1'] for r in mine]),
            'retrieved_gold_evidence_rate': mean([float(r['retrieved_gold_evidence']) for r in mine if r['has_gold_evidence']]),
            'answerable_questions': len(answerable), 'unanswerable_questions': len(unanswerable),
            'declined_on_unanswerable': sum(r['prediction_kind'] == 'declined' for r in unanswerable),
            'declined_on_answerable': sum(r['prediction_kind'] == 'declined' for r in answerable),
            'judge': {k: sum(v.get('verdict') == k for v in judged) for k in ('correct', 'partially_correct', 'incorrect')},
            'judge_completed': len(judged),
            'requests_total': sum(r['requests'] for r in mine), 'tokens_total': sum(r['tokens'] for r in mine),
            'tokens_mean': mean([r['tokens'] for r in mine]), 'seconds_mean': mean([r['seconds'] or 0 for r in mine])}
    dump(OUT / 'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('step', choices=('prepare', 'build', 'run', 'score', 'judge', 'report'))
    args = parser.parse_args()
    {'prepare': prepare, 'build': build, 'run': run, 'score': score, 'judge': judge, 'report': report}[args.step](args)


if __name__ == '__main__':
    main()
