"""Exercise actual main retrieval and context assembly; answer generation is explicitly stubbed."""
from contextlib import redirect_stderr, redirect_stdout
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    import numpy as np
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    import main as pipeline
    import evaluation.run_evaluation as evaluation
    import src.api_llm as api
    api.chat_completion = lambda *a, **k: (_ for _ in ()).throw(AssertionError('API forbidden'))
    embedding = pipeline.load_embedding_model()
    reranker = pipeline.CrossEncoder(pipeline.RERANKER_MODEL_NAME, device='cpu')
    original_predict, score_cache = reranker.predict, {}

    def cached_predict(pairs):
        missing = list(dict.fromkeys(tuple(pair) for pair in pairs if tuple(pair) not in score_cache))
        if missing:
            score_cache.update((pair, float(score)) for pair, score in zip(missing, original_predict(missing)))
        return np.array([score_cache[tuple(pair)] for pair in pairs], dtype=np.float32)

    reranker.predict = cached_predict
    questions = {q['id']:q for q in json.loads((ROOT / 'evaluation/all_papers_questions_en.json').read_text())}
    auxiliary = json.loads((ROOT / 'evaluation/results/all_papers_20261020/auxiliary.json').read_text())
    reports = {q['id']:q for q in json.loads((OUT / 'comparison.json').read_text())['variants']['fixed_selection_candidate120']['questions']}
    records = []
    for qid in ['p1','p6','n07']:
        aux, question = auxiliary[qid], questions[qid]['question']
        for mode in (['base','both'] if qid == 'p1' else ['base']):
            for k in [10,20]:
                name = f'{qid}_{mode}_{k}'
                with patch.object(pipeline, 'load_embedding_model', return_value=embedding), \
                        patch.object(pipeline, 'CrossEncoder', return_value=reranker), \
                        patch.object(pipeline, 'decompose_query', return_value=aux['decomposition']), \
                        patch.object(pipeline, 'rewrite_query', return_value=aux['rewritten_query']), \
                        patch.object(pipeline, 'generate_hypothetical_document', return_value=aux['hypothetical_document']), \
                        patch.object(pipeline, 'generate_final_answer', return_value='Retrieval replay only [1].'), \
                        patch.multiple(pipeline, USE_MULTI_QUERY=mode == 'both', USE_HYDE=mode == 'both', RERANK_TOP_K=k), \
                        (OUT / f'main_{name}.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
                    result = pipeline.main(question, kb_version='all-papers-8-20261020')
                if mode == 'base':
                    expected = reports[qid]['metrics_by_k'][str(k)]['Evidence Completion (up to 2 rounds)']['retrieved_ids']
                else:
                    # Real original-query anchor must stay fixed even with both augmentations.
                    assert result['retrieval_diagnostics']['retrieval_anchor_ids'] == reports[qid]['stage_ids']['rrf'][:1]
                    expected = None
                if expected is not None:
                    assert result['selected_ids'] == expected, (name,'main/evaluation mismatch')
                save(OUT / 'main_replay' / f'{name}.json', {'id':qid,'mode':mode,'top_k':k,
                    'selected_ids':result['selected_ids'],'diagnostics':result['retrieval_diagnostics'],
                    'context':result['context'],'ledger':result['ledger'],
                    'real_answer_generated':False,'api_calls':0,
                    'matches_evaluation':None if expected is None else result['selected_ids']==expected})
                records.append({'id':qid,'mode':mode,'top_k':k,'selected_ids':result['selected_ids']})
                print('Replayed actual main retrieval', name, flush=True)
    # Same CLI also checks both augmentation budgets, plus the still-active three-paper KB.
    evaluation.load_embedding_model = lambda: embedding
    evaluation.CrossEncoder = lambda *a, **k: reranker
    for name, qpath, version, extra in [
        ('p1_ablation', OUT/'inputs/p1.json', 'all-papers-8-20261020', ['--query-ablation']),
        ('active_three_papers', ROOT/'evaluation/questions.json', 'semantic-mac-20261019', [])]:
        target = OUT / name
        sys.argv = ['evaluation.run_evaluation','--questions',str(qpath),'--kb-version',version,
                    '--candidate-k','120','--top-k','10','20','--complete-evidence','--completion-rounds','2',
                    '--auxiliary-cache',str(ROOT/'evaluation/results/all_papers_20261020/auxiliary.json'),
                    '--output-dir',str(target),*extra]
        with (OUT/f'{name}.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
            evaluation.main()
        report = json.loads((target/'results.json').read_text())
        assert report['status']=='completed' and report['api_call_count']==0
        if name == 'p1_ablation':
            q = report['questions'][0]
            for record in records:
                if record['id']=='p1' and record['mode']=='both':
                    assert record['selected_ids'] == q['metrics_by_k'][str(record['top_k'])]['Pipeline both (2 rounds)']['retrieved_ids']
                    path = OUT/'main_replay'/f"p1_both_{record['top_k']}.json"
                    saved = json.loads(path.read_text())
                    saved['matches_evaluation'] = True
                    save(path,saved)
        print('Verified actual evaluation CLI',name,flush=True)
    save(OUT/'main_replay_summary.json',{'actual_main_retrieval_runs':len(records),'all_selected_ids_match':True,
        'augmented_p1_anchor_frozen':True,'active_three_papers_cli_completed':True,'api_calls':0,
        'answer_generation':'Stubbed, not semantic answer validation.','runs':records})


if __name__ == '__main__':
    main()
