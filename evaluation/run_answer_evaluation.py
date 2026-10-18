"""保存真实主流程或固定证据的回答，供人工核对；不计算语义准确率。"""

import argparse
import hashlib
import json
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main as pipeline
import src.api_llm as api
from src.citation_validation import check_citations, repair_citations_once


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--question-id', nargs='+', choices=('q1', 'q2', 'q3', 'q4', 'q5', 'q6'))
    parser.add_argument('--replay-dir', type=Path, help='复用指定目录的证据，跳过检索，只重跑生成')
    args = parser.parse_args()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    if args.replay_dir and args.replay_dir.resolve() == output.resolve():
        parser.error('固定证据的输入目录和输出目录必须不同。')

    tracked = [ROOT / 'main.py', ROOT / 'llm.py', Path(__file__).resolve(),
               *sorted((ROOT / 'src').glob('*.py')),
               ROOT / 'evaluation/questions.json', ROOT / 'evaluation/answer_review_protocol.md',
               ROOT / 'data/processed/chunks_semantic.json',
               ROOT / 'data/processed/faiss_semantic.index']
    hashes = {p.relative_to(ROOT).as_posix(): digest(p) for p in tracked}
    questions = json.loads((ROOT / 'evaluation/questions.json').read_text(encoding='utf-8'))
    if args.question_id:
        questions = [q for q in questions if q['id'] in args.question_id]
    summary_path = output / 'collection.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8')) if summary_path.is_file() else {}
    original_chat = api.chat_completion
    failed = False

    for question in questions:
        qid = question['id']
        # 防止失败重跑后，同目录仍留下上一次的成功答案。
        for suffix in ('.json', '.md'):
            (output / f'{qid}{suffix}').unlink(missing_ok=True)
        calls = []

        def audited_chat(prompt, *call_args, **kwargs):
            started = time.perf_counter()
            call = {'prompt': prompt}
            calls.append(call)
            try:
                response = original_chat(prompt, *call_args, **kwargs)
                call['response'] = response
                return response
            except RuntimeError as exc:
                call['error'] = str(exc)
                raise
            finally:
                call['elapsed_seconds'] = round(time.perf_counter() - started, 2)

        provenance = 'fixed evidence; generation only' if args.replay_dir else 'fresh full main pipeline'
        print(qid, provenance, flush=True)
        started = time.perf_counter()
        result = {'question_id': qid, 'query': question['question'], 'run_provenance': provenance}
        try:
            api.chat_completion = audited_chat
            with (output / f'{qid}.log').open('w', encoding='utf-8') as log:
                with redirect_stdout(log), redirect_stderr(log):
                    if args.replay_dir:
                        saved = json.loads((args.replay_dir / f'{qid}.json').read_text(encoding='utf-8'))
                        assert saved['query'] == question['question']
                        result.update({key: saved[key] for key in ('context', 'ledger', 'selected_ids')})
                        result['prompt'] = pipeline.build_prompt(question['question'], saved['context'])
                        draft = pipeline.generate_final_answer(result['prompt'])
                        repair = repair_citations_once(question['question'], saved['context'], draft,
                                                       saved['ledger']['citation_registry'],
                                                       pipeline.generate_final_answer)
                        result.update(answer=repair['answer'], original_answer=draft, citation_validation=repair)
                    else:
                        result.update(pipeline.main(question['question']))

            registry = result['ledger']['citation_registry']
            assert [c['chunk_id'] for c in registry[:len(result['selected_ids'])]] == result['selected_ids']
            assert all(c['text'] in result['context'] for c in registry)
            result['citation_structure'] = check_citations(result['answer'], registry,
                                                         question['type'] != 'unanswerable')
            result['status'] = 'completed'
            references = '\n\n'.join(
                f"### [{i}] {c['source']}, p.{c['page']} (chunk {c['chunk_id']})\n\n{c['text']}"
                for i, c in enumerate(registry, 1))
            (output / f'{qid}.md').write_text(
                f"# {qid}: {result['query']}\n\n## 回答\n\n{result['answer']}\n\n"
                f"## 运行来源\n\n{provenance}\n\n## 原文供审阅\n\n{references}\n", encoding='utf-8')
        except Exception as exc:
            failed = True
            result.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        finally:
            api.chat_completion = original_chat

        result.update(api_calls=calls, model_calls=len(calls), evaluation_code_sha256=hashes,
                      elapsed_seconds=round(time.perf_counter() - started, 2))
        (output / f'{qid}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        summary[qid] = {key: result[key] for key in ('status', 'model_calls', 'elapsed_seconds', 'run_provenance')}
        summary[qid]['structure_passed'] = result.get('citation_structure', {}).get('structure_passed', False)
        summary[qid]['semantic_support'] = 'requires_manual_review'
        (output / 'collection.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        print(qid, result['status'], flush=True)

    assert all(digest(ROOT / name) == sha for name, sha in hashes.items())
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
