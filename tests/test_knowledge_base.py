# 在临时目录创建小型真实 FAISS 配对库，验证发布、激活/回退和损坏拒绝。
# 只操作测试资产，不切换项目当前知识库指针。

"""Exercise real FAISS pairs, interrupted publication and version pinning."""

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import faiss
import numpy as np

from src import knowledge_base as kb


class KnowledgeBaseTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.processed = self.root / 'data/processed'
        self.processed.mkdir(parents=True)
        index, chunks = self.write_pair(self.root / 'input-legacy', 'old')
        (self.processed / 'faiss_semantic.index').write_bytes(index.read_bytes())
        (self.processed / 'chunks_semantic.json').write_bytes(chunks.read_bytes())

    def write_pair(self, directory, label):
        directory.mkdir()
        index = faiss.IndexFlatIP(2)
        index.add(np.eye(2, dtype=np.float32))
        index_path, chunks_path = directory / 'faiss.index', directory / 'chunks.json'
        faiss.write_index(index, str(index_path))
        chunks = [{'chunk_id': i, 'text': f'{label} evidence passage {i} contains detailed scientific statements.',
                   'source': f'{label}.pdf', 'page': 1, 'title': label, 'section': None}
                  for i in range(2)]
        chunks_path.write_text(json.dumps(chunks), encoding='utf-8')
        return index_path, chunks_path

    def create(self, name):
        index, chunks = self.write_pair(self.root / f'input-{name}', name)
        return kb.create_version(self.processed, name, index, chunks, {'kind': 'fixture'})

    def test_existing_checkout_uses_legacy_without_pointer(self):
        index, chunks, meta = kb.load_knowledge_base(self.processed)
        self.assertEqual((index.ntotal, len(chunks), meta['version']), (2, 2, 'legacy'))

    def test_snapshot_copies_exact_bytes_without_activating(self):
        kb.create_version(self.processed, 'baseline', self.processed / 'faiss_semantic.index',
                          self.processed / 'chunks_semantic.json')
        folder = self.processed / 'versions/baseline'
        self.assertEqual((folder / 'faiss.index').read_bytes(),
                         (self.processed / 'faiss_semantic.index').read_bytes())
        self.assertEqual((folder / 'chunks.json').read_bytes(),
                         (self.processed / 'chunks_semantic.json').read_bytes())
        self.assertEqual(kb.load_knowledge_base(self.processed)[2]['version'], 'legacy')

    def test_switch_and_rollback_load_complete_pairs(self):
        self.create('first')
        self.create('second')
        for version in ('first', 'second', 'first'):
            kb.activate_version(self.processed, version)
            _, chunks, meta = kb.load_knowledge_base(self.processed)
            self.assertEqual(meta['version'], version)
            self.assertTrue(all(c['source'] == f'{version}.pdf' for c in chunks))

    def test_same_count_tampering_cannot_be_activated(self):
        self.create('good')
        self.create('bad')
        kb.activate_version(self.processed, 'good')
        original = (self.processed / 'active_kb.json').read_bytes()
        path = self.processed / 'versions/bad/chunks.json'
        chunks = json.loads(path.read_text())
        chunks[0]['text'] = 'Different text with the same number of chunks.'
        path.write_text(json.dumps(chunks))
        with self.assertRaisesRegex(ValueError, '哈希'):
            kb.activate_version(self.processed, 'bad')
        self.assertEqual((self.processed / 'active_kb.json').read_bytes(), original)
        self.assertEqual(kb.load_knowledge_base(self.processed)[2]['version'], 'good')

    def test_changed_manifest_is_rejected_without_fallback(self):
        self.create('first')
        kb.activate_version(self.processed, 'first')
        path = self.processed / 'versions/first/manifest.json'
        manifest = json.loads(path.read_text())
        manifest['build']['kind'] = 'changed'
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'manifest 已改变'):
            kb.load_knowledge_base(self.processed)

    def test_corrupt_index_is_rejected_before_faiss_deserialization(self):
        self.create('first')
        path = self.processed / 'versions/first/faiss.index'
        path.write_bytes(path.read_bytes()[:10])
        with patch.object(kb.faiss, 'deserialize_index') as deserialize:
            with self.assertRaisesRegex(ValueError, '哈希'):
                kb.load_knowledge_base(self.processed, 'first')
        deserialize.assert_not_called()

    def test_directory_pointer_does_not_fall_back_to_legacy(self):
        (self.processed / 'active_kb.json').mkdir()
        with self.assertRaises(OSError):
            kb.load_knowledge_base(self.processed)

    def test_incomplete_version_and_invalid_pointer_fail_visibly(self):
        folder = self.processed / 'versions/incomplete'
        folder.mkdir(parents=True)
        with self.assertRaises(FileNotFoundError):
            kb.activate_version(self.processed, 'incomplete')
        (self.processed / 'active_kb.json').write_text(
            json.dumps({'version': 'incomplete', 'manifest_sha256': None}))
        with self.assertRaisesRegex(ValueError, '指针'):
            kb.load_knowledge_base(self.processed)

    def test_interrupted_copy_does_not_publish_or_change_active_pair(self):
        self.create('first')
        kb.activate_version(self.processed, 'first')
        original = (self.processed / 'active_kb.json').read_bytes()
        index, chunks = self.write_pair(self.root / 'failed-input', 'failed')
        copy = kb.shutil.copyfile

        def interrupted(source, destination):
            if Path(destination).name == 'chunks.json':
                raise OSError('simulated interruption after index write')
            return copy(source, destination)

        with patch.object(kb.shutil, 'copyfile', side_effect=interrupted):
            with self.assertRaises(OSError):
                kb.create_version(self.processed, 'failed', index, chunks)
        self.assertFalse((self.processed / 'versions/failed').exists())
        self.assertFalse(list((self.processed / 'versions').glob('.building-*')))
        self.assertEqual((self.processed / 'active_kb.json').read_bytes(), original)
        self.assertEqual(kb.load_knowledge_base(self.processed)[2]['version'], 'first')

    def test_pointer_replace_failure_keeps_previous_selection(self):
        self.create('first')
        self.create('second')
        kb.activate_version(self.processed, 'first')
        original = (self.processed / 'active_kb.json').read_bytes()
        with patch.object(kb.os, 'replace', side_effect=OSError('simulated replace failure')):
            with self.assertRaises(OSError):
                kb.activate_version(self.processed, 'second')
        self.assertEqual((self.processed / 'active_kb.json').read_bytes(), original)
        self.assertFalse(list(self.processed.glob('.active-*')))

    def test_existing_versions_cannot_be_overwritten(self):
        self.create('first')
        original = (self.processed / 'versions/first/manifest.json').read_bytes()
        with self.assertRaises(FileExistsError):
            kb.create_version(self.processed, 'first', self.processed / 'faiss_semantic.index',
                              self.processed / 'chunks_semantic.json')
        self.assertEqual((self.processed / 'versions/first/manifest.json').read_bytes(), original)

    def test_unsafe_and_reserved_names_are_rejected(self):
        for name in ('../escape', '/tmp/escape', 'nested/name', '.hidden', 'legacy'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                kb.create_version(self.processed, name, self.processed / 'faiss_semantic.index',
                                  self.processed / 'chunks_semantic.json')

    def test_mismatched_count_and_position_ids_are_rejected(self):
        index, chunks_path = self.write_pair(self.root / 'invalid-input', 'invalid')
        chunks = json.loads(chunks_path.read_text())
        for invalid in (chunks[:1], [dict(chunks[0], chunk_id=1), chunks[1]]):
            chunks_path.write_text(json.dumps(invalid))
            with self.subTest(chunks=invalid), self.assertRaises(ValueError):
                kb.create_version(self.processed, 'invalid', index, chunks_path)
            self.assertFalse((self.processed / 'versions/invalid').exists())

    def test_loader_does_not_mix_versions_if_pointer_changes_mid_read(self):
        self.create('first')
        self.create('second')
        kb.activate_version(self.processed, 'first')
        read = kb._read_pair
        switched = False

        def switch_during_read(*args, **kwargs):
            nonlocal switched
            if not switched:
                switched = True
                kb.activate_version(self.processed, 'second')
            return read(*args, **kwargs)

        with patch.object(kb, '_read_pair', side_effect=switch_during_read):
            _, chunks, meta = kb.load_knowledge_base(self.processed)
        self.assertEqual(meta['version'], 'first')
        self.assertEqual(chunks[0]['source'], 'first.pdf')
        self.assertEqual(kb.load_knowledge_base(self.processed)[2]['version'], 'second')

    def test_answer_evaluation_pins_version_across_questions(self):
        import main as pipeline
        from evaluation import run_answer_evaluation as evaluation

        self.create('first')
        self.create('second')
        kb.activate_version(self.processed, 'first')
        initial = kb.load_knowledge_base(self.processed)
        output = self.root / 'answers'

        def decompose(query, call=None):
            kb.activate_version(self.processed, 'second')
            return {'needs_decomposition': False, 'sub_queries': []}

        class Embedding:
            def encode(self, texts, **kwargs):
                return np.array([[1.0, 0.0]], dtype=np.float32)

        class Reranker:
            def predict(self, pairs):
                return list(range(len(pairs), 0, -1))

        args = ['run_answer_evaluation', '--question-id', 'q2', 'q6', '--output-dir', str(output)]
        with patch('sys.argv', args), redirect_stdout(io.StringIO()), \
                patch.object(evaluation, 'load_knowledge_base', return_value=initial), \
                patch.object(pipeline, 'data_root', return_value=self.root), \
                patch.object(pipeline, 'load_embedding_model', return_value=Embedding()), \
                patch.object(pipeline, 'CrossEncoder', return_value=Reranker()), \
                patch.object(pipeline, 'decompose_query', side_effect=decompose), \
                patch.object(pipeline, 'generate_final_answer', return_value='Fixture evidence [1].'):
            evaluation.main()
        for question in ('q2', 'q6'):
            result = json.loads((output / f'{question}.json').read_text())
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['knowledge_base']['version'], 'first')
            self.assertTrue(all(c['source'] == 'first.pdf' for c in result['ledger']['citation_registry']))
        self.assertEqual(kb.load_knowledge_base(self.processed)[2]['version'], 'second')


if __name__ == '__main__':
    unittest.main()
