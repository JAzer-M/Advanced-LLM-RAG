import hashlib
import unittest

from src.reranker import rerank_results


class RerankerMetadataTests(unittest.TestCase):
    def test_title_already_in_filename_preserves_legacy_model_input(self):
        class InputSensitiveModel:
            def predict(self, pairs):
                return [int(hashlib.sha256(text.encode()).hexdigest()[:6], 16)
                        for _, text in pairs]

        chunks = [{'chunk_id': i, 'source': source, 'title': title, 'text': f'Passage {i}.'}
                  for i, (source, title) in enumerate([
                      ('VGG.pdf', 'VGG'), ('DCNN.pdf', 'DCNN'),
                      ('Attention is all you need.pdf', 'Attention is All you Need')])]
        legacy = [{k: v for k, v in c.items() if k != 'title'} for c in chunks]
        before = rerank_results('query', legacy, InputSensitiveModel(), top_k=3)
        after = rerank_results('query', chunks, InputSensitiveModel(), top_k=3)
        self.assertEqual([(c['chunk_id'], c['rerank_score']) for c in before],
                         [(c['chunk_id'], c['rerank_score']) for c in after])


if __name__ == '__main__':
    unittest.main()
