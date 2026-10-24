"""Local regressions for incomplete API answers and invalid sparse candidates."""

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import llm
from src import api_llm as api
from src.bm25_retriever import build_bm25_index, retrieve_bm25
from src.hybrid_retriever import reciprocal_rank_fusion


def response(answer="Complete answer [1].", finish_reason="stop"):
    return {
        "model": "fixture-model",
        "choices": [{"message": {"content": answer}, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
    }


def chunks_for(texts):
    return [
        {"chunk_id": i, "text": text, "source": f"paper-{i}.pdf", "page": 1,
         "title": "Fixture", "section": None}
        for i, text in enumerate(texts)
    ]


class APICompletionTests(unittest.TestCase):
    def setUp(self):
        settings = patch.object(api, "load_settings", return_value={"model": "fixture-model"})
        settings.start()
        self.addCleanup(settings.stop)
        request = patch.object(api, "_request", return_value=response())
        self.request = request.start()
        self.addCleanup(request.stop)

    def test_normal_response_is_preserved(self):
        result = api.chat_completion("Question")
        self.assertEqual(result["answer"], "Complete answer [1].")
        self.assertEqual(result["finish_reason"], "stop")
        self.assertEqual(result["usage"], response()["usage"])
        self.request.assert_called_once()

    def test_length_is_rejected_with_partial_response_and_usage(self):
        self.request.return_value = response("Partial answer [1].", "length")
        with self.assertRaisesRegex(RuntimeError, "未完成.*length") as caught:
            api.chat_completion("Question")
        self.assertEqual(caught.exception.response["answer"], "Partial answer [1].")
        self.assertEqual(caught.exception.response["usage"], response()["usage"])
        self.request.assert_called_once()

    def test_other_non_stopped_responses_are_not_complete_answers(self):
        for reason in ("content_filter", "tool_calls", None):
            with self.subTest(finish_reason=reason):
                self.request.return_value = response(finish_reason=reason)
                with self.assertRaisesRegex(RuntimeError, "未完成"):
                    api.chat_completion("Question")

    def test_empty_stopped_response_is_still_rejected(self):
        for answer in ("", "   ", None):
            with self.subTest(answer=answer):
                self.request.return_value = response(answer)
                with self.assertRaisesRegex(RuntimeError, "未返回正文"):
                    api.chat_completion("Question")

    def test_main_and_shared_generation_entrypoints_propagate_truncation(self):
        self.request.return_value = response("Partial answer [1].", "length")
        for generate in (api.generate_final_answer, llm.generate_answer):
            with self.subTest(entrypoint=generate):
                with self.assertRaisesRegex(RuntimeError, "未完成.*length"):
                    generate("Question")

    def test_evaluation_keeps_failure_evidence_without_publishing_answer(self):
        from evaluation import run_answer_evaluation as evaluation

        self.request.return_value = response("Partial answer [1].", "length")
        questions = json.loads((evaluation.ROOT / "evaluation/questions.json").read_text())
        query = next(q["question"] for q in questions if q["id"] == "q2")
        chunk = chunks_for(["Fixture evidence."])[0]
        with TemporaryDirectory() as directory:
            replay, output = Path(directory) / "replay", Path(directory) / "output"
            replay.mkdir()
            output.mkdir()
            (replay / "q2.json").write_text(json.dumps({
                "query": query, "context": chunk["text"], "selected_ids": [0],
                "ledger": {"citation_registry": [chunk]},
            }))
            (output / "q2.md").write_text("Stale successful answer")
            args = ["run_answer_evaluation", "--question-id", "q2", "--replay-dir",
                    str(replay), "--output-dir", str(output)]
            with patch("sys.argv", args), redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    evaluation.main()
            self.assertEqual(caught.exception.code, 1)
            saved = json.loads((output / "q2.json").read_text())
            self.assertEqual(saved["status"], "failed")
            self.assertIn("length", saved["error"])
            self.assertEqual(saved["api_calls"][0]["response"]["finish_reason"], "length")
            self.assertEqual(saved["api_calls"][0]["response"]["answer"], "Partial answer [1].")
            self.assertEqual(saved["api_calls"][0]["response"]["usage"], response()["usage"])
            self.assertEqual(saved["model_calls"], 1)
            self.assertFalse((output / "q2.md").exists())
            self.assertEqual(json.loads((output / "collection.json").read_text())["q2"]["status"], "failed")


class SparseCandidateTests(unittest.TestCase):
    def setUp(self):
        self.chunks = chunks_for([
            "positional encoding order", "convolution kernels filters", "pooling stride windows",
        ])
        self.bm25 = build_bm25_index(self.chunks)

    def test_queries_without_usable_matches_return_no_candidates(self):
        for query in ("为什么需要位置编码", "!!!", "unseenquerytoken"):
            with self.subTest(query=query):
                self.assertEqual(retrieve_bm25(self.bm25, self.chunks, query, 3), [])

    def test_zero_score_padding_is_removed_and_mixed_query_still_matches(self):
        for query in ("positional encoding", "什么是 positional encoding"):
            with self.subTest(query=query):
                results = retrieve_bm25(self.bm25, self.chunks, query, 3)
                self.assertEqual([r["chunk_id"] for r in results], [0])
                self.assertGreater(results[0]["score"], 0)

    def test_negative_scores_for_real_matches_are_preserved(self):
        chunks = chunks_for(["shared common", "shared common", "shared common", "unrelated"])
        results = retrieve_bm25(build_bm25_index(chunks), chunks, "shared", 4)
        self.assertEqual([r["chunk_id"] for r in results], [0, 1, 2])
        self.assertTrue(all(r["score"] < 0 for r in results))

    def test_empty_sparse_branch_preserves_dense_order_in_rrf(self):
        dense = [dict(self.chunks[2], score=0.9), dict(self.chunks[1], score=0.8)]
        sparse = retrieve_bm25(self.bm25, self.chunks, "为什么需要位置编码", 3)
        fused = reciprocal_rank_fusion(dense, sparse, k=60, top_k=3)
        self.assertEqual([r["chunk_id"] for r in fused], [2, 1])


if __name__ == "__main__":
    unittest.main()
