"""付费实验前只验证真实调用边界；不请求模型、不加载检索模型。"""
import contextlib
import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_comparison import audited_request, question_inputs


def main():
    public = {'model': 'offline'}
    protocol = {'api_public_settings': public, 'max_actual_chat_attempts': 2,
                'max_actual_chat_attempts_per_question': 1}
    current = {'qid': 'x', 'stage': 'initial'}
    calls, events = [], []
    def persist(): events.append(('persist', calls[-1]['status']))
    def request(prompt):
        assert calls[-1]['status'] == 'running' and events[-1] == ('persist', 'running')
        return {'answer': 'ok', 'finish_reason': 'stop'}
    settings = lambda: public
    def invoke(prompt='p', req=request):
        with contextlib.redirect_stdout(io.StringIO()):
            return audited_request(prompt,current,calls,protocol,req,persist,settings)
    invoke()
    assert len(calls)==1 and calls[0]['status']=='completed'
    assert invoke()['answer']=='ok' and len(calls)==1
    try: invoke('different')
    except RuntimeError as e: assert 'Per-question' in str(e)
    else: raise AssertionError('Per-question cap did not block')
    current.update(qid='y')
    def fail(prompt): raise ConnectionError('offline failure')
    try: invoke(req=fail)
    except ConnectionError: pass
    assert len(calls)==2 and calls[-1]['status']=='failed'
    try: invoke(req=fail)
    except RuntimeError as e: assert 'no automatic retry' in str(e)
    else: raise AssertionError('Failed request was retried')
    current.update(qid='z')
    try: invoke()
    except RuntimeError as e: assert 'Global' in str(e)
    else: raise AssertionError('Global cap did not block')
    assert question_inputs([{'id':'q','question':'ask','gold_evidence':['SECRET_GOLD'],'reference_points':['SECRET_ANSWER']}]) == [{'id':'q','question':'ask'}]
    changed = lambda: {'model':'changed'}
    try: audited_request('p',current,calls,protocol,request,persist,changed)
    except RuntimeError as e: assert 'options changed' in str(e)
    else: raise AssertionError('Changed settings were accepted')
    print('PASS: 7 audit checks (prewrite, completed resume, per-case cap, failure retention, no retry, global cap, whitelist/settings). Model/network calls: 0.')


if __name__ == '__main__':
    main()
