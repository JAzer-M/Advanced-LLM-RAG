"""离线整理逐条人工审阅、成本及修复报告；标签由本助手核对后明确记录，不调用模型。"""
import hashlib
import json
from pathlib import Path
import re
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
OLD = OUT.parent/'agent_p25_20261021'
sys.path.insert(0, str(ROOT))
import agent


def save(name, data):
    (OUT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def main():
    # 每项为原冻结评分点的完整/部分判定；不会把模型复核pass直接当作答案完整。
    decisions = {
        'b02': [('covered', '指定卷积层2/4/5及全连接隐藏层偏置为1。',
                 [1]), ('covered', '其余层偏置为0。', [2]),
                ('covered', '正输入供给ReLU，加速早期学习。', [1])],
        'b03': [('partial', '范围[256,512]正确；未说明S为等比例缩放图像的最短边。', [1]),
                ('covered', '固定224×224裁剪。', [2]),
                ('covered', '相同配置、S=384预训练单尺度模型的全部层微调。', [4])],
        'b06': [('covered', '泛化收益、top-1/top-5改善及附加CIFAR-10事实均有原文支持；数值保留原文%写法。', [4,6]),
                ('partial', '无性能收益及A-LRN比较正确；未明确通常省略LRN、仅一个配置例外的架构事实。', [3,10]),
                ('covered', '内存消耗与计算时间均增加。', [3])]
    }
    questions = {q['id']:q for q in json.loads((OLD/'questions_frozen.json').read_text())}
    chunks = json.loads((ROOT/'data/processed/versions/all-papers-8-20261020/chunks.json').read_text())
    review, canonical_checks = {}, 0
    lines = ['# 修复后三道开发题的原文核对', '',
             '本助手人工阅读实际答案与原文后记录标签；非独立第三方盲评。沿用原冻结评分点，未改写旧P2.5结果。', '']
    for qid, rows in decisions.items():
        base = OUT/'cases'/qid
        loop = json.loads((base/'loop'/f'{qid}.json').read_text())
        result = json.loads((base/'answer'/f'{qid}.json').read_text())
        payload = json.loads((base/'answer/inputs.json').read_text())
        answer = (base/'answer/answer.md').read_text().strip()
        assert answer == result['result']['answer']
        assert result['result']['status'] == 'review_passed'
        registry = {p['citation']:p for p in payload['passages']}
        citations = {int(n) for n in re.findall(r'\[(\d+)\]', answer)}
        assert citations <= registry.keys()
        checked = []
        for n in sorted(citations):
            p = registry[n]
            canonical = chunks[p['chunk_id']]
            assert all(p[k] == canonical[k] for k in ('source','page','text'))
            checked.append({'citation':n, 'chunk_id':p['chunk_id'], 'source':p['source'],
                            'page':p['page'], 'original_text':p['text'], 'canonical_identity_verified':True})
            canonical_checks += 1
        point_rows = []
        assert len(rows) == len(questions[qid]['reference_points'])
        for reference, (label, reason, numbers) in zip(questions[qid]['reference_points'], rows):
            assert set(numbers) <= citations
            point_rows.append({'reference_point':reference, 'label':label, 'reason':reason,
                               'supporting_citations':numbers})
        strict = all(p['label']=='covered' for p in point_rows)
        review[qid] = {'planning_succeeded':True, 'delivered':True, 'model_review':'review_passed',
                       'strict_pass':strict, 'points':point_rows, 'citation_gaps':[], 'unsupported_claims':[],
                       'answer_sha256':hashlib.sha256(answer.encode()).hexdigest(), 'answer':answer,
                       'checked_citations':checked}
        lines += [f'## {qid}', '', questions[qid]['question'], '', answer, '',
                  f'原冻结标准严格通过：{strict}；核心完整点：{sum(p[0]=="covered" for p in rows)}/{len(rows)}。', '']
        for index, p in enumerate(point_rows,1):
            lines += [f'- 评分点{index}：{p["label"]}；{p["reason"]}']
        lines += ['', '本答案实际引用的当前库原文：', '']
        for p in checked:
            lines += [f'[{p["citation"]}] → chunk {p["chunk_id"]}，{p["source"]}，第{p["page"]}页：',
                      '', p['original_text'], '']
        review[qid]['validation_repairs'] = loop.get('validation_repairs', [])
    save('semantic_review.json', review)
    (OUT/'manual_review.md').write_text('\n'.join(lines)+'\n')
    calls = json.loads((OUT/'actual_chat_calls.json').read_text())
    costs = {}
    for qid in decisions:
        selected = [c for c in calls if c['question_id']==qid]
        costs[qid] = {'attempts':len(selected),
                      'tokens':sum(c['response']['usage']['total_tokens'] for c in selected),
                      'decision_calls':sum(c['stage']=='decision' for c in selected),
                      'answer_calls':sum(c['stage']=='answer' for c in selected)}
    summary = {'scope':'3 selected development failures; no new-set or full-12 improvement claim',
               'planning_successes':3, 'delivered_answers':3, 'model_review_passed':3,
               'frozen_strict_pass_count':sum(v['strict_pass'] for v in review.values()),
               'covered_points':sum(p['label']=='covered' for v in review.values() for p in v['points']),
               'total_points':sum(len(v['points']) for v in review.values()),
               'all_finish_reasons_stop':all(c['response']['finish_reason']=='stop' for c in calls),
               'citation_identity_checks':canonical_checks, 'per_case_usage':costs,
               'actual_usage':json.loads((OUT/'execution_summary.json').read_text())}
    save('summary.json', summary)
    table = '\n'.join(f'| {q} | 通过 | 已交付 / review_passed | '
                      f'{sum(p[0]=="covered" for p in rows)}/{len(rows)} | '
                      f'{"通过" if review[q]["strict_pass"] else "未通过"} | '
                      f'{costs[q]["attempts"]} / {costs[q]["tokens"]:,} |' for q,rows in decisions.items())
    report = f'''# P2.5之后：规划可用性修复与开发回归

日期：2026-10-22，Asia/Shanghai。用户授权修复上一轮规划问题，并要求说明流程。未接统一main、未提交或推送。

**三道旧失败题均恢复规划、决策和回答交付；217项离线测试通过。** 按原冻结细粒度评分仍只有1/3严格通过，核心点7/9；这不等于新题泛化或整轮12题成绩提升。

## 修复流程与依据

1. 先保存2695个现有文件的哈希、修改前源码及旧实验。原始响应回放稳定复现b02/b03/b06的3/3规划失败；无API请求，见[原始复现](original_reproduction.log)。
2. 用最小语言样例补回归，经过真实需求绑定和循环记账入口。第一批14项在修复前为3个失败、4个错误；另补respectively条件反例，先确认会失败。红灯日志保留。
3. 分步验证原因：只补回指/联合主体绑定后，绑定测试转绿，剩余3项循环修正测试仍失败；接入受预算约束的规划修正后转绿。最后全部217项测试通过，网络尝试0，见[测试日志](all_tests_final.log)。
4. 冻结修复版本与三题输入，再只重跑这三道开发题。复用原P2.5初检原文，不重跑固定RAG、不传旧答案/Gold/评分点。随后逐条阅读实际答案、实际引用与原文，记录完整/部分覆盖；模型pass不能替代人工核对。
5. 独立目录保存修复结果、真实请求、失败和文档交接；旧实验结果保持不动。

## 生产改动

- `agent.py`：在单一声明主体、摘录唯一、前文只有一个同名先行词时，允许it/its回指扩展；多主体或重复先行词不猜测。
- `agent.py`：question_quote继续保存连续原题；仅把紧邻并列的主体名列表确定性投影到当前主体，need保留原谓语/条件。非连续引文仍拒绝；含分别条件、分离的非对称条件或另一主体后续限定的片段仍拒绝。搜索与独立事实检查只用投影后的need，不重新带入其他主体。
- `agent.py`：max-actions循环内的完整但无效规划最多修正一次；与原状态/行动修正共用一次额度，决策最多6调用、最多3工具行动，回答最多4调用。网络失败或截断不进入格式修正，也不自动重试；默认纯诊断/单步模式不额外启用规划修正。
- `src/agent_answer.py`：生成和复核明确使用need确定范围、question_quote保留审计上下文；引用/连续原文/复核校验不放宽。
- 新增`tests/test_agent_plan_repair.py`的15项行为回归；保持普通函数、字典和列表，无框架或主入口改造。

## 三题真实开发回归

| 题 | 规划 | 回答与模型复核 | 原冻结完整点 | 原冻结严格 | 实际请求 / token |
| --- | --- | --- | --- | --- | ---: |
{table}

本轮三个新规划均一次通过；真实运行没有触发plan_repair。b03的格式修正分支由经过run_diagnostics的离线测试验证，原来伪造的连续引文仍会被拒绝。本轮b02首次事实检查因原文引文不匹配而被拒绝，使用原有一次状态修正；首次回答复核也因非连续原文被拒绝，经一次修订后通过。原始失败均保留。

b03仍未明确S为等比例缩放图像的最短边；b06仍未明确VGG通常省略LRN、仅一个配置例外。它们覆盖题面直接所问的主要事实且实际引用支持充分，但按原冻结合取评分点记partial，不能以模型review_passed把主评分改成3/3。b06的1.4%/1.2%照录原文错误率变化写法，没有另做单位换算。

全轮真实15次请求/15次chat POST，输入35,697、输出3,406，合计39,103 token；全部stop，HTTP失败、缺失usage与自动重试均0。用量仅含修复后的三题Agent，不含旧初检的历史成本；不是和上一轮整批成本直接比较。执行约38.970秒，CPU模型初载另列，非冷启动或P95。首次沙箱socket预检在chat前被拒，0模型请求；放行访问同一已配置本机代理后按相同冻结协议执行，失败日志另存。

## 结论与边界

本次解除的是三种规划阻塞，并验证旧主体/数据集隔离、逐字引文、共享修正额度和调用上限仍有效。有限词法规则不等于通用语义解析器；无法明确绑定的复杂比较仍会保守拒绝。

三题已用于诊断、提示修改和回归，属于开发题；同一助手审阅。没有重跑其余9题，也没有重算或拼接新的12题通过率，原P2.5严格10/12对7/12的历史结果完整保留。尚未验证修复版本的新留出质量、成本收益或统一main用户流程。接续可先审阅这些边界，再接main与另建新题验证；不要为了通过背景细节而把评测答案写进规划或生成提示。

证据：[逐条原文审阅](manual_review.md)、[汇总JSON](summary.json)、[实际请求账本](actual_chat_calls.json)、[冻结协议](frozen_protocol.json)、[原始响应回放](captured_plan_replay.json)、[最终核验](verification.json)。
'''
    (OUT/'report.md').write_text(report)
    print(json.dumps({k:v for k,v in summary.items() if k!='actual_usage'},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
