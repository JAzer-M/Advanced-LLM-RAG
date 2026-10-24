"""Download a small, version-pinned arXiv manifest; keep PDFs local and resumable."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pymupdf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    papers = json.loads(args.manifest.read_text(encoding='utf-8'))['papers']
    ids = [paper['arxiv_id'] for paper in papers]
    if (not ids or len(set(ids)) != len(ids)
            or any(not re.fullmatch(r'\d{4}\.\d{4,5}v[1-9]\d*', value) for value in ids)):
        parser.error('清单须包含不重复、带版本号的现代 arXiv ID。')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / 'downloads.json'
    previous = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}
    records = previous.get('papers', {})
    failed = False
    last_request = 0
    context = ssl.create_default_context()

    for paper in papers:
        paper_id = paper['arxiv_id']
        target = args.output_dir / f'{paper_id}.pdf'
        temporary = target.with_suffix('.pdf.part')
        record = dict(records.get(paper_id, {}))
        record.update(arxiv_id=paper_id, title=paper['title'],
                      pdf_url=f'https://arxiv.org/pdf/{paper_id}', filename=target.name)
        try:
            expected = record.get('sha256')
            if target.exists():
                actual = hashlib.sha256(target.read_bytes()).hexdigest()
                if expected and actual != expected:
                    raise ValueError('现有文件哈希改变；保留文件，拒绝覆盖。')
                record['status'] = 'skipped_verified' if expected else 'validated_existing'
            else:
                for attempt in range(2):
                    time.sleep(max(0, 3.1 - (time.monotonic() - last_request)))
                    last_request = time.monotonic()
                    try:
                        request = Request(record['pdf_url'], headers={
                            'User-Agent': 'Advanced-LLM-RAG-Pilot/0.1 (local research)'})
                        with urlopen(request, timeout=45, context=context) as response:
                            temporary.write_bytes(response.read())
                        break
                    except (HTTPError, URLError, TimeoutError) as exc:
                        if attempt or (isinstance(exc, HTTPError)
                                       and exc.code not in (429, 500, 502, 503, 504)):
                            raise
                        time.sleep(5)
                actual = hashlib.sha256(temporary.read_bytes()).hexdigest()
                if expected and actual != expected:
                    raise ValueError('固定版本的下载哈希与记录不同；拒绝替换。')
                record.update(status='downloaded', fetched_at=datetime.now(timezone.utc).isoformat())

            candidate = temporary if temporary.exists() and not target.exists() else target
            if not candidate.read_bytes().startswith(b'%PDF-'):
                raise ValueError('下载内容不是 PDF。')
            with pymupdf.open(candidate, filetype='pdf') as pdf:
                if not len(pdf) or not pdf[0].get_text().strip():
                    raise ValueError('PDF 无页面或首页无可提取文本。')
                record['pages'] = len(pdf)
            if candidate == temporary:
                temporary.replace(target)
            record.update(sha256=actual, bytes=target.stat().st_size)
            record.pop('error', None)
        except Exception as exc:
            failed = True
            record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        finally:
            temporary.unlink(missing_ok=True)
        records[paper_id] = record
        report = {'manifest_sha256': hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                  'updated_at': datetime.now(timezone.utc).isoformat(), 'papers': records}
        report_temporary = report_path.with_suffix('.json.part')
        report_temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        report_temporary.replace(report_path)
        print(paper_id, record['status'], record.get('pages', ''), record.get('error', ''), flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
