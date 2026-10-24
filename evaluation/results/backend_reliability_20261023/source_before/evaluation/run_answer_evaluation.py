# 回答采集入口：保存真实 main 全流程，或复用旧证据只重新生成回答。
# 两种模式都可能调用生成 API；replay 在这里不表示离线或免费。

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
from src.knowledge_base import load_knowledge_base


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# 完整运行与固定证据生成分别标记来源，调用审计/失败原文会与每题结果一并保存。
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--questions', type=Path, default=ROOT / 'evaluation/questions.json',
                        help='题目 JSON；默认保留已有六题')
    parser.add_argument('--question-id', nargs='+')
    parser.add_argument('--replay-dir', type=Path, help='复用指定目录的证据，跳过检索，只重跑生成')
    parser.add_argument('--kb-version', help='固定知识库版本；默认在运行开始时锁定当前版本')
    args = parser.parse_args()
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    if args.replay_dir and args.replay_dir.resolve() == output.resolve():
        parser.error('固定证据的输入目录和输出目录必须不同。')
    if args.replay_dir and args.kb_version:
        parser.error('固定证据回放使用保存的证据，不同时指定知识库版本。')

    questions = json.loads(args.questions.read_text(encoding='utf-8'))
    if len({q['id'] for q in questions}) != len(questions):
        parser.error('题目 ID 不能重复。')
    if args.question_id:
        unknown = set(args.question_id) - {q['id'] for q in questions}
        if unknown:
            parser.error(f'题目 ID 不存在：{sorted(unknown)}')
        questions = [q for q in questions if q['id'] in args.question_id]

    tracked = [ROOT / 'main.py', ROOT / 'llm.py', Path(__file__).resolve(),
               *sorted((ROOT / 'src').glob('*.py')),
               args.questions, ROOT / 'evaluation/answer_review_protocol.md']
    knowledge_base = None
    if args.replay_dir:
        tracked.extend(args.replay_dir / f"{q['id']}.json" for q in questions)
    else:
        # 启动时固定实际版本，后续各题传同一版本，避免运行途中切库混入不同资料。
        _, _, knowledge_base = load_knowledge_base(ROOT / 'data/processed', args.kb_version)
        tracked.extend(Path(knowledge_base[key]) for key in ('index_path', 'chunks_path'))
        if knowledge_base['manifest_path']:
            tracked.append(Path(knowledge_base['manifest_path']))
    hashes = {}
    for path in tracked:
        resolved = path.resolve()
        name = resolved.relative_to(ROOT).as_posix() if resolved.is_relative_to(ROOT) else str(resolved)
        hashes[name] = digest(path)
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

        # 在共享 API 入口记账，覆盖分解、回答及可能的引用修复，不只统计最终生成。
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
                if isinstance(exc, api.IncompleteResponseError):
                    call['response'] = exc.response
                raise
            finally:
                call['elapsed_seconds'] = round(time.perf_counter() - started, 2)

        provenance = 'fixed evidence; generation only' if args.replay_dir else 'fresh full main pipeline'
        print(qid, provenance, flush=True)
        started = time.perf_counter()
        result = {'question_id': qid, 'query': question['question'], 'run_provenance': provenance,
                  'knowledge_base': knowledge_base}
        try:
            api.chat_completion = audited_chat
            with (output / f'{qid}.log').open('w', encoding='utf-8') as log:
                with redirect_stdout(log), redirect_stderr(log):
                    if args.replay_dir:
                        saved = json.loads((args.replay_dir / f'{qid}.json').read_text(encoding='utf-8'))
                        assert saved['query'] == question['question']
                        result.update({key: saved[key] for key in ('context', 'ledger', 'selected_ids')})
                        result['knowledge_base'] = saved.get('knowledge_base')
                        result['prompt'] = pipeline.build_prompt(question['question'], saved['context'])
                        draft = pipeline.generate_final_answer(result['prompt'])
                        repair = repair_citations_once(question['question'], saved['context'], draft,
                                                       saved['ledger']['citation_registry'],
                                                       pipeline.generate_final_answer)
                        result.update(answer=repair['answer'], original_answer=draft, citation_validation=repair)
                    else:
                        result.update(pipeline.main(question['question'], kb_version=knowledge_base['version']))

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
