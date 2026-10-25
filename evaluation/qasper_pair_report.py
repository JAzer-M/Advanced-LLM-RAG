"""只读取配对实验记录：完整/短答评分、官方复算、模型匹配子集及逐次成本。"""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation import qasper_eval as old
from evaluation import qasper_pair_eval as paired
from evaluation import qasper_scoring as scoring

OUT = paired.OUT
load, dump = paired.load, paired.dump


def mean(values):
    return statistics.mean(values) if values else None


def source_alignment(sample, papers, chunks):
    """同一分块的近似段落映射只计算一次，不向生成阶段提供Gold。"""
    aligned = {}
    for pid in sorted({q['paper_id'] for q in sample['questions']}):
        paragraphs = [p for s in papers[pid]['full_text'] for p in s['paragraphs'] if p.strip()]
        paragraph_words = [(p, old.shingles(p)) for p in paragraphs]
        for chunk in chunks:
            if Path(chunk['source']).stem != pid:
                continue
            words = old.shingles(chunk['text'])
            aligned[chunk['chunk_id']] = [p for p, target in paragraph_words if words and target and
                (len(words & target) / len(words) >= .5 or len(words & target) / len(target) >= .5)]
    return aligned


def score():
    sample = load(OUT / 'frozen_sample.json')
    papers = load(old.CACHE / 'qasper-test-v0.3.json')
    chunks = load(ROOT / 'data/processed/versions' / paired.KB_VERSION / 'chunks.json')
    alignment = source_alignment(sample, papers, chunks)
    rows, predictions = [], {}
    for q in sample['questions']:
        gold = {scoring.normalize_evidence(p) for r in q['references'] for p in r['evidence']}
        gold_ids = {cid for cid, paragraphs in alignment.items() if Path(chunks[cid]['source']).stem == q['paper_id']
                    if any(scoring.normalize_evidence(p) in gold for p in paragraphs)}
        for version in paired.VERSIONS:
            for mode in paired.MODES:
                path = paired.result_path(version, q, mode)
                if not path.exists():
                    continue
                result = load(path)
                full, kind = scoring.answer_for_scoring(result)
                short, _ = scoring.answer_for_scoring(result, short=True)
                legacy, _ = old.predicted_answer(result)
                registry = result.get('ledger', {}).get('citation_registry', [])
                cited_numbers = set()
                import re
                for group in re.findall(r'\[(\d+(?:\s*[,，、]\s*\d+)*)\]', result.get('answer') or ''):
                    cited_numbers.update(int(n) for n in re.split(r'\s*[,，、]\s*', group))
                cited = list(dict.fromkeys(p for n, chunk in enumerate(registry, 1) if n in cited_numbers
                    for p in alignment.get(chunk['chunk_id'], []) if Path(chunk['source']).stem == q['paper_id']))
                retrieved = list(dict.fromkeys(p for c in registry if Path(c['source']).stem == q['paper_id']
                    for p in alignment.get(c['chunk_id'], [])))
                diagnostics = result.get('retrieval_diagnostics', {})
                judges = paired.result_path(version, q, mode, 'judge')
                judged = load(judges) if judges.exists() else {}
                calls = result.get('eval_api_calls', [])
                row = {'question_id': q['question_id'], 'paper_id': q['paper_id'], 'version': version, 'mode': mode,
                    'status': result.get('status'), 'answer_status': result.get('answer_status'),
                    'requested_model': result['evaluation']['requested_model'],
                    'reported_models': sorted({c['reported_model'] for c in calls if c.get('reported_model')}),
                    'prediction_kind': kind, 'gold_types': sorted({r['type'] for r in q['references']}),
                    'has_gold_evidence': bool(gold), 'available_gold_chunk_ids': sorted(gold_ids),
                    'answer_f1': max(old.token_f1(full, r['answer']) for r in q['references']),
                    'short_answer_f1': max(old.token_f1(short, r['answer']) for r in q['references']),
                    'legacy_answer_f1': max(old.token_f1(legacy, r['answer']) for r in q['references']),
                    'evidence_f1_raw': max(old.paragraph_f1(cited, r['evidence']) for r in q['references']),
                    'evidence_f1_normalized': max(scoring.paragraph_f1(cited, r['evidence']) for r in q['references']),
                    'retrieved_gold_evidence': bool({scoring.normalize_evidence(p) for p in retrieved} & gold),
                    'selected_gold_ids': sorted(set(result.get('selected_ids', [])) & gold_ids),
                    'initial_selected_gold_ids': sorted(set(result.get('initial_selected_ids',
                        result.get('selected_ids', []))) & gold_ids),
                    'candidate_gold_ids': sorted(set(diagnostics.get('candidate_ids', [])) & gold_ids)
                        if 'candidate_ids' in diagnostics else None,
                    'global_ranking_gold_ids': sorted(set(diagnostics.get('global_ranking_ids', [])) & gold_ids)
                        if 'global_ranking_ids' in diagnostics else None,
                    'wrong_source_registry_chunks': sum(Path(c['source']).stem != q['paper_id'] for c in registry),
                    'requests': len(calls), 'tokens': sum((c.get('usage') or {}).get('total_tokens', 0) for c in calls),
                    'seconds': result['eval_elapsed_seconds'], 'routing': result.get('routing', {}).get('route'),
                    'chinese_character_count': len(re.findall(r'[\u4e00-\u9fff]', result.get('answer') or '')),
                    'answer_paragraphs': len(re.split(r'\n\s*\n', result.get('answer') or '')),
                    'full_words': len(full.split()), 'short_words': len(short.split()),
                    'fallback': bool(result.get('fallback')), 'error': result.get('error'),
                    'judge_status': judged.get('status'), 'judge_method': judged.get('judging_method', 'model'),
                    'judge_model': judged.get('evaluation', {}).get('requested_model'),
                    'verdict': judged.get('verdict'), 'judge_declined': judged.get('declined')}
                rows.append(row)
                for label, answer in [('full', full), ('short', short)]:
                    predictions.setdefault((version, mode, label), []).append({'question_id': q['question_id'],
                        'predicted_answer': answer, 'predicted_evidence': cited})
    dump(OUT / 'scores/per_question.json', rows)
    gold_subset = {pid: {**papers[pid], 'qas': [q for q in papers[pid]['qas']
        if q['question_id'] in {v['question_id'] for v in sample['questions']}]} for pid in {q['paper_id'] for q in sample['questions']}}
    gold_path = old.CACHE / 'gold_pair_holdout_20261025.json'
    dump(gold_path, gold_subset)
    official = {}
    for (version, mode, label), values in predictions.items():
        target = OUT / f'scores/predictions_{version}_{mode}_{label}.jsonl'
        target.write_text(''.join(json.dumps(v, ensure_ascii=False) + '\n' for v in values), encoding='utf-8')
        run = subprocess.run([sys.executable, str(old.CACHE / 'qasper_evaluator.py'), '--predictions', str(target),
            '--gold', str(gold_path), '--text_evidence_only'], text=True, capture_output=True)
        official[f'{version}_{mode}_{label}'] = {'returncode': run.returncode,
            'stdout': run.stdout[-5000:], 'stderr': run.stderr[-2000:]}
    dump(OUT / 'scores/official_evaluator.json', official)
    return rows


def cluster_interval(pairs, metric):
    """按论文重采样，避免把同篇论文的问题当作互相独立的样本。"""
    by_paper = {}
    for baseline, revised in pairs:
        if metric == 'correct':
            delta = int(revised['verdict'] == 'correct') - int(baseline['verdict'] == 'correct')
        else:
            delta = revised[metric] - baseline[metric]
        by_paper.setdefault(baseline['paper_id'], []).append(delta)
    papers = list(by_paper)
    if not papers:
        return None
    rng = random.Random(20261025)
    values = []
    for _ in range(5000):
        picked = [delta for pid in rng.choices(papers, k=len(papers)) for delta in by_paper[pid]]
        values.append(statistics.mean(picked))
    values.sort()
    return {'mean_delta': mean([d for deltas in by_paper.values() for d in deltas]),
        'paper_cluster_bootstrap_95_percent': [values[124], values[4874]],
        'papers': len(papers), 'questions': len(pairs)}


def aggregate(rows, planned):
    return {'results': len(rows), 'planned': planned, 'status': dict(Counter(r['status'] for r in rows)),
        'requested_models': dict(Counter(r['requested_model'] for r in rows)),
        **{key: sum(r[key] for r in rows) / planned for key in
            ('answer_f1', 'short_answer_f1', 'legacy_answer_f1', 'evidence_f1_raw', 'evidence_f1_normalized')},
        'gold_hit': sum(r['retrieved_gold_evidence'] for r in rows),
        'initial_selected_gold_hit': sum(bool(r['initial_selected_gold_ids']) for r in rows),
        'questions_with_gold': sum(r['has_gold_evidence'] for r in rows),
        'judge': dict(Counter(r['verdict'] or 'missing_or_failed' for r in rows)),
        'judge_models': dict(Counter(r['judge_model'] or r['judge_method'] for r in rows)),
        'model_judge_generation_mismatch': sum(r['judge_method'] == 'model' and
            r['judge_status'] == 'completed' and r['judge_model'] != r['requested_model'] for r in rows),
        'requests': sum(r['requests'] for r in rows), 'tokens': sum(r['tokens'] for r in rows),
        'seconds_mean': mean([r['seconds'] for r in rows]), 'fallback_results': sum(r['fallback'] for r in rows),
        'wrong_source_registry_chunks': sum(r['wrong_source_registry_chunks'] for r in rows)}


def summarize(rows=None):
    rows = rows if rows is not None else load(OUT / 'scores/per_question.json')
    sample = load(OUT / 'frozen_sample.json')
    count = len(sample['questions'])
    by_key = {(r['version'], r['mode'], r['question_id']): r for r in rows}
    complete = len(rows) == count * 6 and all(r['judge_status'] is not None for r in rows)
    summary = {'evaluation_status': 'completed' if complete else 'in_progress',
        'generation_results': len(rows), 'planned_generation_results': count * 6,
        'questions': count, 'papers': sample['papers'], 'groups': {}, 'paired': {}, 'cost': {}}
    complete_blocks = []
    for q in sample['questions']:
        block = [by_key[(v, m, q['question_id'])] for v in paired.VERSIONS for m in paired.MODES
                 if (v, m, q['question_id']) in by_key]
        if len(block) == 6:
            complete_blocks.append({'question_id': q['question_id'],
                'requested_models': sorted({r['requested_model'] for r in block})})
    summary['question_model_blocks'] = {'complete': len(complete_blocks),
        'all_six_same_model': sum(len(b['requested_models']) == 1 for b in complete_blocks),
        'mixed_questions': [b for b in complete_blocks if len(b['requested_models']) != 1]}
    for version in paired.VERSIONS:
        summary['groups'][version] = {m: aggregate([r for r in rows if r['version'] == version and r['mode'] == m], count)
                                     for m in paired.MODES}
    for mode in paired.MODES:
        pairs = [(by_key[('baseline', mode, q['question_id'])], by_key[('revised', mode, q['question_id'])])
            for q in sample['questions'] if all((v, mode, q['question_id']) in by_key for v in paired.VERSIONS)]
        matched = [(b, r) for b, r in pairs if b['requested_model'] == r['requested_model']]
        judge_matched = [(b, r) for b, r in matched if (b['judge_method'] != 'model' or r['judge_method'] != 'model'
            or b['judge_model'] == r['judge_model']) and b['judge_status'] == r['judge_status'] == 'completed']
        summary['paired'][mode] = {'all_pairs': len(pairs), 'generation_model_matched_pairs': len(matched),
            'generation_and_judge_matched_pairs': len(judge_matched),
            'answer_f1_delta_all': cluster_interval(pairs, 'answer_f1'),
            'answer_f1_delta_matched': cluster_interval(matched, 'answer_f1'),
            'short_answer_f1_delta_matched': cluster_interval(matched, 'short_answer_f1'),
            'judge_correct_delta_matched': cluster_interval(judge_matched, 'correct'),
            'models_of_matched_pairs': dict(Counter(b['requested_model'] for b, r in matched))}
    for stage in ('development', 'runs', 'judge'):
        calls = [c for path in (OUT / stage).glob('*/*/*_calls.json') for c in load(path)]
        summary['cost'][stage] = {'attempts': len(calls), 'failed_attempts': sum(c['status'] != 'completed' for c in calls),
            'usage_missing_attempts': sum(c.get('usage') is None for c in calls),
            'reported_usage': {k: sum((c.get('usage') or {}).get(k, 0) for c in calls)
                for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')},
            'requested_models': dict(Counter(c['requested_model'] for c in calls))}
    dump(OUT / 'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def verify(summary):
    protocol = load(OUT / 'protocol.json')
    sample = load(OUT / 'frozen_sample.json')
    issues = []

    def check(condition, label):
        if not condition:
            issues.append(label)

    for version in paired.VERSIONS:
        folder = OUT / 'baseline_source' if version == 'baseline' else ROOT
        for name, checksum in protocol[version + '_source_hashes'].items():
            check(hashlib.sha256((folder / name).read_bytes()).hexdigest() == checksum, f'{version} source: {name}')
    for name, field in [('evaluation/qasper_pair_eval.py', 'harness_sha256'),
                        ('evaluation/qasper_scoring.py', 'scoring_sha256')]:
        check(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == protocol[field], name)
    check(hashlib.sha256((OUT / 'frozen_sample.json').read_bytes()).hexdigest() == protocol['sample_sha256'], 'sample hash')
    previous = load(ROOT / 'evaluation/results/qasper_20261024/frozen_sample.json')
    check(not {q['paper_id'] for q in sample['questions']} & {q['paper_id'] for q in previous['questions']}, 'paper overlap')
    check(not {q['question_id'] for q in sample['questions']} & {q['question_id'] for q in previous['questions']}, 'question overlap')
    changed = subprocess.check_output(['git', 'diff', '--name-only', '-z', protocol['baseline_commit']], cwd=ROOT).decode().split('\0')
    old_changes = [p for p in changed if p.startswith('evaluation/results/qasper_20261024/') or p == 'evaluation/qasper_eval.py']
    check(not old_changes, 'old evaluation changed')
    original_bytes = {}
    for name in ('evaluation/qasper_eval.py', 'evaluation/results/qasper_20261024/protocol.md',
                 'evaluation/results/qasper_20261024/frozen_sample.json'):
        before = subprocess.check_output(['git', 'show', protocol['baseline_commit'] + ':' + name], cwd=ROOT)
        original_bytes[name] = before == (ROOT / name).read_bytes()
        check(original_bytes[name], 'original frozen bytes: ' + name)
    transition = load(OUT / 'execution_transition.json')
    check(hashlib.sha256((OUT / 'run_parallel.py').read_bytes()).hexdigest() == transition['parallel_runner_sha256'],
          'parallel runner hash')
    kb = ROOT / 'data/processed/versions' / paired.KB_VERSION
    kb_hashes = {name: hashlib.sha256((kb / name).read_bytes()).hexdigest() for name in protocol['kb_manifest']['files']}
    check(kb_hashes == protocol['kb_manifest']['files'], 'new KB pair hash')
    downloads = load(OUT / 'downloads.json')
    for pid, entry in downloads.items():
        if entry['status'] != 'failed':
            check(hashlib.sha256((paired.RAW / (pid + '.pdf')).read_bytes()).hexdigest() == entry['sha256'], f'PDF: {pid}')
    # 先前已核对并在本轮再次确认的两个选择指针，不以当前值覆盖预期值。
    expected_pointers = {
        'data/processed/active_kb.json': '8106e53d0eeac32bb0a47fe811ed55de8d97fcf839b99c1b055893d9560b0020',
        'data/webui/library.json': '15db9473dfe3528c157a2a8aed9c507bb1b37eee93c9eb8570cc4b877caf2c09'}
    pointer_hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in expected_pointers}
    check(pointer_hashes == expected_pointers, 'existing KB pointers')
    generated = judged = 0
    for q in sample['questions']:
        expected_query = f'For the paper "{q["paper_title"]}" (arXiv: {q["paper_id"]}), answer this question: {q["question"]}'.strip()
        for version in paired.VERSIONS:
            for mode in paired.MODES:
                path = paired.result_path(version, q, mode)
                check(path.exists(), f'missing generation: {version}/{q["question_id"]}/{mode}')
                if not path.exists():
                    continue
                result = load(path)
                calls = result['eval_api_calls']
                generated += 1
                check(result.get('query') == expected_query, f'query: {version}/{q["question_id"]}/{mode}')
                check(result.get('original_question') == q['question'], 'original question')
                check(calls == load(path.with_name(mode + '_calls.json')), 'call journal mismatch')
                check(len(calls) <= {'rag': 3, 'agent': 11, 'auto': 13}[mode], 'call budget')
                check(result['api_summary']['attempts'] == len(calls), 'attempt reconciliation')
                check(result['api_summary']['reported_usage']['total_tokens'] ==
                    sum((c.get('usage') or {}).get('total_tokens', 0) for c in calls), 'usage reconciliation')
                check(not any(c['status'] == 'running' for c in calls), 'unfinished generation call')
                target = paired.result_path(version, q, mode, 'judge')
                check(target.exists(), 'missing judge record')
                if target.exists():
                    judged += 1
                    value = load(target)
                    if value.get('judging_method') == 'failed_generation_rule':
                        check(result['status'] == 'failed' and value['verdict'] == 'incorrect', 'failed-generation judgment rule')
    official_issues = []
    for key, value in load(OUT / 'scores/official_evaluator.json').items():
        check(value['returncode'] == 0, 'official evaluator exit')
        values = json.loads(value['stdout'])
        version, mode, label = key.split('_')
        group = summary['groups'][version][mode]
        for official_key, local_key in [('Answer F1', 'answer_f1' if label == 'full' else 'short_answer_f1'),
                                        ('Evidence F1', 'evidence_f1_raw')]:
            delta = abs(values[official_key] - group[local_key])
            if delta > 1e-12:
                official_issues.append({'group': key, 'metric': official_key, 'difference': delta})
        check(values['Missing predictions'] == 0, 'official missing predictions')
    check(not official_issues, 'official score mismatch')
    # 仅输出是否命中及路径，不输出凭证本身。
    private_path = ROOT / 'api.local.json'
    private = load(private_path) if private_path.exists() else {}
    keys = {value.encode() for value in (private.get('api_key'), os.environ.get('RAG_API_KEY')) if value}
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    files = {p for p in OUT.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / p for p in changed + untracked if p and (ROOT / p).is_file())
    leaks = [str(p.relative_to(ROOT)) for p in files if any(key in p.read_bytes() for key in keys)]
    check(not leaks, 'credential scan')
    result = {'generated': generated, 'judged': judged, 'record_consistency_issues': issues,
        'official_crosscheck_issues': official_issues, 'old_evaluation_tracked_changes': old_changes,
        'original_frozen_files_unchanged': original_bytes, 'execution_transition': transition,
        'kb_hashes': kb_hashes, 'pointer_hashes': pointer_hashes, 'credential_scan_files': len(files),
        'credential_scan_leaks': leaks, 'source_hashes_unchanged': not any('source:' in i for i in issues),
        'credential_values_checked': len(keys),
        'postprocessing_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'model_list_requests': load(OUT / 'model_inventory.json')['model_list_requests'],
        'paper_download_attempts': sum(d['status'] != 'existing' for d in downloads.values())}
    dump(OUT / 'verification.json', result)
    print('Final verification issues:', issues)
    return result


if __name__ == '__main__':
    summary = summarize(score())
    if summary['evaluation_status'] == 'completed':
        verification = verify(summary)
        raise SystemExit(bool(verification['record_consistency_issues']))
