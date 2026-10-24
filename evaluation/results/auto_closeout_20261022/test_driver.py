"""付费前验证白名单、预写记账、预算、同路径续接与失败保留；不联网。"""
import contextlib
import io
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_comparison import audited_request,question_inputs,shared_initial


def main():
    public={'model':'offline'}
    protocol={'api_public_settings':public,'max_actual_chat_attempts':3,'max_actual_chat_attempts_per_question':2}
    current={'qid':'x','stage':'agent'};calls=[];events=[]
    def persist():events.append(calls[-1]['status'])
    def request(prompt):
        assert calls[-1]['status']=='running' and events[-1]=='running'
        return {'answer':'ok','finish_reason':'stop'}
    def invoke(prompt='p',req=request,settings=lambda:public):
        with contextlib.redirect_stdout(io.StringIO()):
            return audited_request(prompt,current,calls,protocol,req,persist,settings)
    invoke();invoke();assert len(calls)==1
    current['stage']='auto';invoke();assert len(calls)==2
    try:invoke('different')
    except RuntimeError as exc:assert 'Per-question' in str(exc)
    else:raise AssertionError('Per-case cap missing')
    current['qid']='y'
    def fail(prompt):raise ConnectionError('offline')
    try:invoke(req=fail)
    except ConnectionError:pass
    assert calls[-1]['status']=='failed' and len(calls)==3
    try:invoke(req=fail)
    except RuntimeError as exc:assert 'no automatic retry' in str(exc)
    else:raise AssertionError('Failed request retried')
    current['qid']='z'
    try:invoke()
    except RuntimeError as exc:assert 'Global' in str(exc)
    else:raise AssertionError('Global cap missing')
    try:invoke(settings=lambda:{'model':'changed'})
    except RuntimeError as exc:assert 'options changed' in str(exc)
    else:raise AssertionError('Changed settings accepted')
    assert question_inputs([{'id':'q','question':'ask','required_points':['SECRET'],'gold_evidence':['SECRET']}])==[{'id':'q','question':'ask'}]
    rag={key:[] for key in ('query','knowledge_base','retrieval_diagnostics','selected_ids','context','ledger')}
    initial=shared_initial({**rag,'answer':'SECRET','decomposition':'SECRET','prompt':'SECRET'})
    assert set(initial)==set(rag)|{'status'} and 'SECRET' not in str(initial)
    initial['ledger'].append('mutated');assert rag['ledger']==[]
    print('PASS: prewrite, exact success resume, no cross-arm cache, per-question/global caps, failed retention/no retry, settings freeze, question/evidence whitelists, deep copy. API calls: 0.')


if __name__=='__main__':main()
