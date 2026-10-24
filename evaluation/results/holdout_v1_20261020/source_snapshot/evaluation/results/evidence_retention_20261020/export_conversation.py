"""Archive visible conversation and tool audit records, excluding private reasoning/configuration."""
from datetime import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path('/Users/j/.codex/sessions/2026/10/19/rollout-2026-10-19T18-07-08-01a153a1-156a-7aa3-bba9-65ecb6d1220e.jsonl')
DEST = ROOT / 'docs/chat_history'
STEM = 'RAG_2026-10-19_20'


def main():
    settings = json.loads((ROOT / 'api.local.json').read_text())
    secrets = {v for v in [settings.get('api_key'), os.environ.get('RAG_API_KEY')] if v and len(v) >= 8}
    replacements = 0

    def redact(text):
        nonlocal replacements
        for secret in secrets:
            replacements += text.count(secret)
            text = text.replace(secret, '<REDACTED>')
        text = re.sub(r'(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]{12,}', r'\1<REDACTED>', text)
        text = re.sub(r'''(?i)(["'](?:api_key|access_token|refresh_token|api_secret)["']\s*:\s*["'])([^"']+)(["'])''',
                      r'\1<REDACTED>\3', text)
        return text

    raw = SOURCE.read_bytes()
    messages, tool_rows = [], []
    ignored = 0
    for line in raw.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue  # An active session may be writing its final record.
        if row['type'] != 'response_item':
            continue
        item = row['payload']
        if item.get('type') == 'message' and item.get('role') in ['user', 'assistant']:
            role, phase = item['role'], item.get('phase')
            if role == 'assistant' and phase not in ['commentary', 'final', 'final_answer']:
                ignored += 1
                continue
            parts = [c['text'] for c in item.get('content', []) if c.get('type') in ['input_text','output_text']]
            if not parts:
                continue
            body = redact('\n\n'.join(parts))
            label = '用户' if role == 'user' else ('助手进度' if phase == 'commentary' else '助手答复')
            if role == 'user' and (body.lstrip().startswith(('<environment_context>', '<external_codex_apps_open_page>', '# AGENTS.md instructions'))):
                label = '用户会话上下文'
            timestamp = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Shanghai'))
            messages.append({'role': role, 'phase': phase, 'label': label,
                             'time': timestamp.strftime('%Y-%m-%d %H:%M:%S %Z'), 'text': body})
        elif item.get('type') in ['custom_tool_call', 'custom_tool_call_output', 'function_call', 'function_call_output']:
            # Whitelist visible call/result fields; never copy internal metadata or reasoning records.
            allowed = {key: item[key] for key in ['type','name','call_id','input','arguments','output','status'] if key in item}
            tool_rows.append(redact(json.dumps({'timestamp':row['timestamp'], **allowed}, ensure_ascii=False)))
    DEST.mkdir(parents=True, exist_ok=True)
    exported_at = datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    transcript = f'''# 本次 RAG 项目对话可见记录

对话：核验 RAG 项目进度。线程 ID：01a153a1-156a-7aa3-bba9-65ecb6d1220e。

导出时间：{exported_at}。按本地会话原始记录的顺序保留用户消息、助手可见进度和答复；会话环境上下文单独标记。此时当前轮仍在执行，后续消息可再次运行导出脚本刷新。

工具调用与返回另存为同目录 `{STEM}_tools.jsonl.gz`。不包含系统 / 开发者指令或内部推理记录；凭证值脱敏。历史对话中的结论保留原样，当前事实以根目录 PROGRESS.md 和最新实验报告为准。

'''
    for number, message in enumerate(messages, 1):
        transcript += f"## {number:03d} · {message['label']} · {message['time']}\n\n{message['text']}\n\n---\n\n"
    tools_text = '\n'.join(tool_rows) + '\n'
    assert all(secret not in transcript and secret not in tools_text for secret in secrets)
    mdpath = DEST / f'{STEM}_完整对话.md'
    toolpath = DEST / f'{STEM}_tools.jsonl.gz'
    mdpath.write_text(transcript)
    toolpath.write_bytes(gzip.compress(tools_text.encode(), mtime=0))
    manifest = {'thread_id':'01a153a1-156a-7aa3-bba9-65ecb6d1220e', 'exported_at':exported_at,
                'source_file':str(SOURCE), 'source_snapshot_bytes':len(raw),
                'source_snapshot_sha256':hashlib.sha256(raw).hexdigest(),
                'visible_messages':len(messages), 'user_messages':sum(m['role']=='user' for m in messages),
                'assistant_messages':sum(m['role']=='assistant' for m in messages), 'tool_records':len(tool_rows),
                'excluded_internal_message_records':ignored, 'known_secret_occurrences_redacted':replacements,
                'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [mdpath,toolpath]},
                'scope':'Visible conversation and tool audit through the snapshot; active turn can be refreshed.'}
    (DEST / f'{STEM}_export_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ['visible_messages','user_messages','assistant_messages','tool_records']},ensure_ascii=False))


if __name__ == '__main__':
    main()
