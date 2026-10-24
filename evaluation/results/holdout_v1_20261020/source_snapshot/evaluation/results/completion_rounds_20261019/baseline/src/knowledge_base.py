"""Publish paired knowledge-base files and switch between immutable versions."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

import faiss
import numpy as np


def version_name(value):
    if value == 'legacy' or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', value):
        raise ValueError('版本名须为 1～64 位字母、数字、点、短横线或下划线；legacy 为原始库保留名。')
    return value


def _read_pair(index_path, chunks_path, expected=None):
    # 哈希与解析使用同一份字节，避免校验后再次读取不同内容。
    index_bytes = index_path.read_bytes()
    chunks_bytes = chunks_path.read_bytes()
    hashes = {'faiss.index': hashlib.sha256(index_bytes).hexdigest(),
              'chunks.json': hashlib.sha256(chunks_bytes).hexdigest()}
    if expected is not None and hashes != expected:
        raise ValueError('知识库索引或分块的哈希不一致；拒绝加载或切换。')
    index = faiss.deserialize_index(np.frombuffer(index_bytes, dtype=np.uint8))
    chunks = json.loads(chunks_bytes.decode('utf-8-sig'))
    if not isinstance(chunks, list) or not chunks or index.ntotal != len(chunks) or index.d <= 0:
        raise ValueError('知识库必须非空，且索引向量数与分块数一致。')
    required = {'chunk_id', 'text', 'source', 'page', 'title', 'section'}
    for position, chunk in enumerate(chunks):
        if (not isinstance(chunk, dict) or not required <= chunk.keys()
                or type(chunk['chunk_id']) is not int or chunk['chunk_id'] != position
                or not isinstance(chunk['text'], str) or not chunk['text'].strip()):
            raise ValueError(f'分块 {position} 缺少字段、正文为空或 chunk_id 与向量行号不一致。')
    return index, chunks, hashes


def load_knowledge_base(processed_dir, version=None):
    """Read the active pointer once; return a verified index, chunks and provenance.

    Without a pointer, keep existing checkouts working with the original pair.
    Explicit version='legacy' also selects that pair without changing the pointer.
    A broken pointer/version fails visibly rather than silently changing sources.
    """
    processed_dir = Path(processed_dir).resolve()
    expected_manifest = None
    pointer_path = processed_dir / 'active_kb.json'
    if version is None:
        if pointer_path.exists():
            pointer = json.loads(pointer_path.read_text(encoding='utf-8'))
            version = version_name(pointer['version'])
            expected_manifest = pointer['manifest_sha256']
            if not isinstance(expected_manifest, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_manifest):
                raise ValueError('当前版本指针缺少有效的 manifest 哈希。')
        else:
            version = 'legacy'

    manifest_path = None
    manifest_sha = None
    if version == 'legacy':
        index_path = processed_dir / 'faiss_semantic.index'
        chunks_path = processed_dir / 'chunks_semantic.json'
        index, chunks, hashes = _read_pair(index_path, chunks_path)
    else:
        folder = processed_dir / 'versions' / version_name(version)
        manifest_path = folder / 'manifest.json'
        manifest_bytes = manifest_path.read_bytes()
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        if expected_manifest is not None and manifest_sha != expected_manifest:
            raise ValueError('当前版本的 manifest 已改变；拒绝加载。')
        manifest = json.loads(manifest_bytes)
        if manifest['schema_version'] != 1 or manifest['version'] != version:
            raise ValueError('知识库 manifest 的版本或格式不一致。')
        if set(manifest['files']) != {'faiss.index', 'chunks.json'}:
            raise ValueError('知识库 manifest 必须登记索引和分块两个文件。')
        index_path, chunks_path = folder / 'faiss.index', folder / 'chunks.json'
        index, chunks, hashes = _read_pair(index_path, chunks_path, manifest['files'])
        if manifest['chunk_count'] != len(chunks) or manifest['dimension'] != index.d:
            raise ValueError('知识库 manifest 的数量或维度与实际文件不一致。')

    metadata = {'version': version, 'chunk_count': len(chunks), 'dimension': index.d,
                'index_path': str(index_path), 'chunks_path': str(chunks_path),
                'manifest_path': str(manifest_path) if manifest_path else None,
                'manifest_sha256': manifest_sha, 'files': hashes}
    return index, chunks, metadata


def create_version(processed_dir, version, index_path, chunks_path, build_metadata=None):
    """Copy a complete pair to staging, validate, then publish without overwriting."""
    version = version_name(version)
    versions_dir = Path(processed_dir).resolve() / 'versions'
    versions_dir.mkdir(parents=True, exist_ok=True)
    target = versions_dir / version
    if target.exists():
        raise FileExistsError(f'知识库版本已存在，不能覆盖：{version}')
    staging = Path(tempfile.mkdtemp(prefix='.building-', dir=versions_dir))
    try:
        shutil.copyfile(index_path, staging / 'faiss.index')
        shutil.copyfile(chunks_path, staging / 'chunks.json')
        index, chunks, hashes = _read_pair(staging / 'faiss.index', staging / 'chunks.json')
        manifest = {'schema_version': 1, 'version': version,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'chunk_count': len(chunks), 'dimension': index.d,
                    'files': hashes, 'build': build_metadata or {}}
        (staging / 'manifest.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        # 同一文件系统内重命名目录；中断的 .building-* 不会成为可用版本。
        staging.rename(target)
        return manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def activate_version(processed_dir, version):
    """Validate before atomically replacing the current pointer; rollback is identical."""
    version_name(version)
    processed_dir = Path(processed_dir).resolve()
    _, _, metadata = load_knowledge_base(processed_dir, version)
    pointer = {'version': version, 'manifest_sha256': metadata['manifest_sha256']}
    descriptor, temporary = tempfile.mkstemp(prefix='.active-', suffix='.json', dir=processed_dir)
    temporary = Path(temporary)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(pointer, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, processed_dir / 'active_kb.json')
    finally:
        temporary.unlink(missing_ok=True)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('snapshot', 'activate'):
        commands.add_parser(command).add_argument('version', type=version_name)
    commands.add_parser('validate').add_argument('version', nargs='?')
    commands.add_parser('list')
    args = parser.parse_args()
    processed = Path(__file__).resolve().parents[1] / 'data' / 'processed'
    try:
        if args.command == 'snapshot':
            result = create_version(processed, args.version,
                                    processed / 'faiss_semantic.index',
                                    processed / 'chunks_semantic.json',
                                    {'kind': 'legacy_snapshot; copied without re-encoding'})
        elif args.command == 'activate':
            result = activate_version(processed, args.version)
        elif args.command == 'validate':
            _, _, result = load_knowledge_base(processed, args.version)
        else:
            _, _, current = load_knowledge_base(processed)
            versions = processed / 'versions'
            result = {'active': current['version'], 'versions': sorted(
                p.name for p in versions.glob('*')
                if p.is_dir() and not p.name.startswith('.') and (p / 'manifest.json').is_file())}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        parser.exit(1, f'知识库操作失败：{exc}\n')


if __name__ == '__main__':
    main()
