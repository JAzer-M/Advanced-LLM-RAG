"""Preserve task-scoped final sources and verify handoff links and transcript hashes."""
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    files = ['main.py', 'src/reranker.py', 'src/evidence_gap.py', 'evaluation/run_evaluation.py',
             'tests/test_evidence_gap.py', 'tests/test_retention_regression.py', 'README.md', 'PROGRESS.md',
             'docs/EVIDENCE_RETENTION_AND_BUDGET_2026-10-20.md']
    patch = ''
    snapshots = {}
    for name in files:
        source, baseline, final = ROOT / name, OUT / 'baseline' / name, OUT / 'final' / name
        final.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, final)
        snapshots[name] = digest(final)
        patch += ''.join(difflib.unified_diff(baseline.read_text().splitlines(True) if baseline.exists() else [],
                                            source.read_text().splitlines(True),
                                            fromfile='a/' + name if baseline.exists() else '/dev/null',
                                            tofile='b/' + name))
    (OUT / 'task_changes.patch').write_text(patch)
    (OUT / 'final_hashes.json').write_text(json.dumps(snapshots, indent=2) + '\n')
    archive = ROOT / 'docs/history/PROGRESS_BEFORE_RETENTION_2026-10-20.md'
    assert archive.read_bytes() == (OUT / 'baseline/PROGRESS.md').read_bytes()
    checked = 0
    for name in ['README.md', 'PROGRESS.md', 'docs/EVIDENCE_RETENTION_AND_BUDGET_2026-10-20.md']:
        source = ROOT / name
        for target in re.findall(r'\[[^\]\n]+\]\(([^)\n]+)\)', source.read_text()):
            target = target.strip('<>')
            if re.match(r'[a-zA-Z]+:', target) or target.startswith('#'):
                continue
            relative = unquote(target.split('#')[0])
            assert (source.parent / relative).exists(), (name, target)
            checked += 1
    manifest_path = ROOT / 'docs/chat_history/RAG_2026-10-19_20_export_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest['files'].items():
        assert digest(manifest_path.parent / name) == expected
    tool_path = manifest_path.parent / 'RAG_2026-10-19_20_tools.jsonl.gz'
    records = gzip.decompress(tool_path.read_bytes()).decode().splitlines()
    assert len(records) == manifest['tool_records']
    for line in records:
        row = json.loads(line)
        assert row['type'] in ['custom_tool_call', 'custom_tool_call_output', 'function_call', 'function_call_output']
    transcript = (manifest_path.parent / 'RAG_2026-10-19_20_完整对话.md').read_text()
    assert len(re.findall(r'^## \d{3,} · ', transcript, re.M)) == manifest['visible_messages']
    assert '{{' not in (ROOT / 'PROGRESS.md').read_text()
    assert '进行中' not in (ROOT / 'docs/EVIDENCE_RETENTION_AND_BUDGET_2026-10-20.md').read_text()
    diff_check = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True, text=True)
    assert diff_check.returncode == 0, diff_check.stdout + diff_check.stderr
    summary = {'status': 'passed', 'final_source_snapshots': len(snapshots), 'local_markdown_links_checked': checked,
               'old_progress_preserved_byte_for_byte': True, 'transcript_messages': manifest['visible_messages'],
               'tool_records': len(records), 'transcript_sha256_verified': True, 'git_diff_check': 'passed',
               'scope': 'Patch is relative to the task baseline, preserving pre-existing dirty changes.'}
    (OUT / 'artifact_audit.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
