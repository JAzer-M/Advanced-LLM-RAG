"""只读开发回归记录；保留全部阶段，缓存响应不重复计入实际API费用。"""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent


def read(path):return json.loads(path.read_text())


def main():
    phases=[];live=[];cached=[]
    for name in ('.','followup','final','scoped_inputs'):
        folder=OUT/name;calls=read(folder/'actual_chat_calls.json')
        posts=[c for c in calls if c['http_posts']]
        reused=[c for c in calls if not c['http_posts']]
        assert all(c['status']=='completed' and c['response']['finish_reason']=='stop' for c in calls)
        assert all(c['http_posts']==1 for c in posts)
        assert all(c.get('response_source',{}).get('reused_completed_probe') for c in reused)
        live+=posts;cached+=reused
        phases.append({'name':name,'logical_calls':len(calls),'actual_http_posts':len(posts),'cached_calls':len(reused),
                       'new_reported_usage':{k:sum(c['response']['usage'].get(k,0) for c in posts)
                                             for k in ('prompt_tokens','completion_tokens','total_tokens')},
                       'results':{p.parent.name:read(p)['status'] for p in (folder/'runs').glob('*/result.json')}})
    definitions=[('a03_auto','final/runs/a03_auto/result.json',[True,True],[1387],
                  '两组upper/lower阈值均正确，[4]指向1387；仅一次原RAG生成，无Agent调用。'),
                 ('a04_auto','final/runs/a04_auto/result.json',[True,True,True],[73,903],
                  'Transformer beam4，RAG指定两生成任务beam4/10文档，分别[8]73和[1]903。'),
                 ('a04_agent','runs/a04_agent/result.json',[True,True,True],[73,903],
                  '阶段一恢复交付，但初检已足够仍执行search和read_neighbors两行动，保留过处理事实。'),
                 ('a02_agent','runs/a02_agent/result.json',[True,True],[145],
                  '参数2/5/1e-4/.75及ReLU后均正确；本次未额外编造完整归一化公式。'),
                 ('h10_rag','runs/h10_rag/result.json',[False,True],[1003],
                  '只给出Self-RAG包含金标准答案标准；RAG判据缺失，未建立完整比较。'),
                 ('h10_auto','scoped_inputs/runs/h10_auto/result.json',[False,True],[1003],
                  '升级后实际搜索一次，未补到765；反馈再次partial/空gap且共享修正额度已用，degraded。缓存草稿还把RAG套到PopQA/TriviaQA，降级不代表内容正确。')]
    reviews=[]
    for rid,path,points,ids,note in definitions:
        result=read(OUT/path)
        reviews.append({'id':rid,'result_path':path,'status':result['status'],'required_covered':points,
                        'strict_pass':all(points) and result['status']=='completed','source_chunk_ids':ids,
                        'notes':note,'result_sha256':hashlib.sha256((OUT/path).read_bytes()).hexdigest(),
                        'actions':result.get('agent',{}).get('actions_executed',0),
                        'route':result.get('routing',{}).get('route')})
    summary={'scope':'Known development regressions across documented versions; not a new accuracy benchmark.',
             'summarized_at_utc':datetime.now(timezone.utc).isoformat(),
             'final_design':'RAG first, explicit evidence gap/citation failure triggers bounded Agent; failed upgrades visibly degraded.',
             'typical_full_query_calls':{'rag':2,'old_auto':4,'final_auto_direct':2},
             'maximum_full_query_calls':{'agent':11,'auto':13},
             'actual_unique_http_posts':len(live),'logical_calls_including_cache':len(live)+len(cached),
             'cached_successful_probe_calls':len(cached),
             'actual_new_reported_usage':{k:sum(c['response']['usage'].get(k,0) for c in live)
                                           for k in ('prompt_tokens','completion_tokens','total_tokens')},
             'http_failures':0,'automatic_retries':0,'usage_missing_calls':0,
             'phases':phases,'selected_development_reviews':reviews,
             'old_eight_question_scores_recomputed':False,
             'remaining_issue':'Repeated invalid partial/empty-gap feedback consumes the one shared correction allowance; h10 did not complete.',
             'limits':['Same assistant author/reviewer; not independent or blind.',
                       'Saved real initial retrieval reused; actual new decomposition/retrieval was not rerun.',
                       'Different phases use documented code versions; do not merge selected successes into an accuracy rate.',
                       'No new held-out quality, concurrency or P95 claim.']}
    assert summary['actual_unique_http_posts']==32
    assert summary['actual_new_reported_usage']['total_tokens']==98399
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('actual_unique_http_posts','logical_calls_including_cache','actual_new_reported_usage')},ensure_ascii=False))


if __name__=='__main__':main()
