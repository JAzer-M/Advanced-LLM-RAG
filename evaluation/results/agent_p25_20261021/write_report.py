"""用已冻结规则和已审阅结果生成报告；纯离线，不改变成绩。"""
from collections import Counter
import json
from pathlib import Path
import statistics

OUT = Path(__file__).resolve().parent


def main():
    s=json.loads((OUT/'summary.json').read_text())
    rows=json.loads((OUT/'case_metrics.json').read_text())
    protocol=json.loads((OUT/'frozen_protocol.json').read_text())
    execution=json.loads((OUT/'execution_summary.json').read_text())
    assert s['quality_complete'] and execution['terminal_records']==12
    pct=lambda x:f'{x*100:.2f}%'
    r,a=s['groups']['all']['rag'],s['groups']['all']['agent']
    ra,aa=s['groups']['answerable']['rag'],s['groups']['answerable']['agent']
    ru,au=s['path_attributed_usage']['rag'],s['path_attributed_usage']['agent']
    actual=s['actual_usage']
    delta=a['strict_pass_rate_planned']-r['strict_pass_rate_planned']
    verdict=('本轮Agent严格通过数高于固定RAG；仅为本批小样本观察，额外成本另报。' if delta>0 else
             '本轮Agent没有提高严格通过数；当前版本未证明相对固定RAG的质量收益。' if delta==0 else
             '本轮Agent严格通过数低于固定RAG；当前版本未通过质量收益验收，需要先修正可用性问题。')
    lines=['# P2.5：固定RAG与现有Agent的成对量化验收\n','真实采集：2026-10-21，Asia/Shanghai；离线复核与交接续接：2026-10-22。目录名保留采集日期。未提交、未推送。\n',
           '**'+verdict+'**\n',
           '本轮完整采集12道新问题的两条路径，并按运行前冻结规则审阅；这表示对照实验完成，不等于当前Agent质量达标。\n',
           '## 主要结果\n','| 指标 | 固定RAG | Agent |','| --- | ---: | ---: |',
           f"| 成功交付结果（含合理拒答） | {r['executed_successfully']}/12 | {a['executed_successfully']}/12 |",
           f"| 全部题严格通过 | {r['strict_pass_count']}/12 ({pct(r['strict_pass_rate_planned'])}) | {a['strict_pass_count']}/12 ({pct(a['strict_pass_rate_planned'])}) |",
           f"| 10道可答题严格通过 | {ra['strict_pass_count']}/10 | {aa['strict_pass_count']}/10 |",
           f"| 可答题核心点覆盖 macro | {pct(ra['core_coverage_macro'])} | {pct(aa['core_coverage_macro'])} |",
           f"| 可答题核心点覆盖 micro | {ra['covered_points']}/{ra['total_points']} | {aa['covered_points']}/{aa['total_points']} |",
           f"| 不可答题正确拒答 | {s['groups']['unanswerable']['rag']['appropriate_refusals']}/2 | {s['groups']['unanswerable']['agent']['appropriate_refusals']}/2 |",
           f"| 关键引用支持通过（可答计划分母） | {ra['citation_support_pass_cases']}/10 | {aa['citation_support_pass_cases']}/10 |",
           f"| 路径归因请求数（共享初检各计一次） | {ru['attempts']} | {au['attempts']} |",
           f"| 路径归因token | {ru['total_tokens']:,} | {au['total_tokens']:,} |",
           f"| 路径中位耗时，秒 | {s['timing']['rag']['median_seconds']:.3f} | {s['timing']['agent']['median_seconds']:.3f} |",'\n',
           f"严格通过率变化为 **{delta*100:+.2f}个百分点**。同题成对结果：Agent独有通过{s['strict_pass_pairs']['agent_only_pass']}；RAG独有通过{s['strict_pass_pairs']['rag_only_pass']}；共同通过{s['strict_pass_pairs']['both_pass']}；共同未通过{s['strict_pass_pairs']['neither_pass']}。\n",
           '运行失败和未交付草稿按计划分母计0；成功输出子集的通过率见summary.json，不能用它替代整体通过率。引用支持与核心完整性分开：有来源的模糊定义仍可能未覆盖评分点。\n',
           '## 执行条件与计费边界\n',
           f"题集：4单篇、6跨篇、2不可答；八篇固定库all-papers-8-20261020，1397段；模型路由{protocol['api_public_settings']['model']}，temperature=0、thinking disabled、max_tokens=4096。生产main、Agent、工具、提示与索引未改。\n",
           '固定RAG实际运行当前main：候选120、Top-10、最多两轮已有规则补查，rewrite/HyDE关闭。Agent接收同一次初检产生的原文与目录，然后运行现有最多3行动/6决策调用，以及最多4回答/复核调用。它没有收到固定RAG答案、Gold、评分点或旧分解。\n',
           '**本实验检验在固定RAG检索结果上增加现有Agent层的整体效果。** 它没有隔离“工具补查、生成提示改变、复核”的单独因果贡献，也没有提前完成统一main用户入口。\n',
           f"全轮上限156，实际客户端尝试 **{actual['attempts']}**，HTTP POST **{actual['http_posts']}**，失败尝试 **{actual['failed_attempts']}**，自动重试0；输入{actual['prompt_tokens']:,}、输出{actual['completion_tokens']:,}、合计 **{actual['total_tokens']:,} token**。usage缺失请求：{actual['missing_usage_call_numbers']}。\n",
           f"共享初检实际{s['shared_initial_usage']['attempts']}次、{s['shared_initial_usage']['total_tokens']:,} token，只付出一次；为比较两个逻辑路径，在各自归因成本中各计一次。因此两个路径token之和减去共享初检={actual['total_tokens']:,}，不能把两条路径成本相加当成实际用量。未核验货币单价，不换算人民币。\n",
           f"Agent/RAG归因token比={au['total_tokens']/ru['total_tokens']:.3f}。失败较早的Agent题成本较低，不能据此说高效；两条路径均成功交付的共同子集成本另存summary.json的matched_execution_success_costs。\n",
           f"本次采集进程耗时{execution['this_session_elapsed_seconds']:.3f}秒（含两条路径工作，共享初检只执行一次）；CPU模型初载单列resource_loading.json。路径耗时均包含各自初检，Agent不包含固定RAG回答耗时。共享模型、顺序单次运行，非冷启动、并发或P95。\n",
           '## 检索与工具行为\n',
           '| 共享初检指标 | 值 |','| --- | ---: |']
    for name,val in s['initial_top10_metrics'].items():lines.append(f'| {name}@10 | {val:.6f} |')
    lines += ['\n上述Top-10对两条路径相同，含失败题的共同初检，10道可答题计分；不可答无Gold题跳过。Gold为非穷尽，替代原文可支持答案。\n',
              f"本轮Agent工具行动共{s['agent_tool_actions']}次。固定RAG上下文指定Gold召回macro={s['rag_context_gold_recall_macro']:.6f}；Agent最终收集证据指定Gold召回macro={s['agent_collected_gold_recall_macro']:.6f}，规划失败题仍保留其实际初始原文，未把解析失败误当检索漏召。每题实际生成输入证据数/字符数、采集证据数和停止原因见case_metrics.json。Agent追加顺序前10/20/全量仅作诊断，不是独立Top-20策略实验。\n",
              '## 逐题结果\n','| 题 | 类别 | RAG核心完整点 | Agent核心完整点 | RAG严格 | Agent严格 | 工具行动/停止 |',
              '| --- | --- | ---: | ---: | --- | --- | --- |']
    for row in rows:
        cols=[]
        for arm in ('rag','agent'):
            sem=row[arm]['semantic'];cols.append(f"{sum(p=='covered' for p in sem['points'])}/{len(sem['points'])}")
        lines.append(f"| {row['id']} | {row['type']} | {cols[0]} | {cols[1]} | {'通过' if row['rag']['semantic']['strict_pass'] else '未通过'} | {'通过' if row['agent']['semantic']['strict_pass'] else '未通过'} | {row['agent']['tool_actions']} / {row['agent']['halt_reason'] or row['agent']['loop_status']} |")
    lines += ['\n完整实际答案和逐条原文核对：[manual_review.md](manual_review.md)。全部初稿、复核、失败、输入和轨迹保留在[cases](cases/)及[实际请求账本](actual_chat_calls.json)。\n',
              '## 失败与解释边界\n']
    for row in rows:
        for arm in ('rag','agent'):
            if not row[arm]['semantic']['strict_pass']:
                lines.append(f"- **{row['id']} / {arm}**：{row[arm]['semantic']['reason']}")
    lines += ['\n**b07审阅敏感性：** DPR第2节400给出以问题为单位的操作定义，但表2注434写成percentage of top 20/100 retrieved passages。两条输出均复述表注，按冻结评分点记partial，未认定无来源编造。保留该题的主结果；若仅作事后敏感性分析排除b07，两臂都会少一个严格未通过题，具体数见下，不回写主成绩。\n']
    without=[row for row in rows if row['id']!='b07']
    lines.append('排除b07后的严格通过：'+ '；'.join(f"{arm} {sum(row[arm]['semantic']['strict_pass'] for row in without)}/11" for arm in ('rag','agent'))+'。\n')
    relaxed={arm:sum(row[arm]['semantic']['strict_pass'] or (row['id']=='b03' and arm=='rag') or (row['id']=='b09' and arm=='agent') for row in rows) for arm in ('rag','agent')}
    lines += ['b03固定RAG未说明S的最短边含义，而冻结第1点同时包含此限定；b09 Agent公式正确但未提冻结评分点中的段级beam search。两处按主评分点记partial。这些细粒度条件比题面直接要求更细，公开保留，不能把本轮“严格通过率”泛称为通用答案准确率。\n',
              f"**事后敏感性分析（非主成绩）：** 若只放宽上述两处附加背景要求，固定RAG为{relaxed['rag']}/12，Agent为{relaxed['agent']}/12；分差仍为{relaxed['agent']-relaxed['rag']}题。该分析不改写预先冻结的主结果。\n",
              '这12题是同语料新问题，部分原子知识点与旧题重合；本助手既出题又审阅，非独立第三方盲评。每题一次、样本小，不给出总体显著性或线上性能承诺。原h01/h10/h11已用于开发，仅作历史案例引用，未加入本轮分母。\n',
              '## 接续建议\n',
              '先根据本轮真实失败修正规划抽取对回指、联合主语及逐字片段的处理，并以本轮失败作为开发回归；继续保持主体/数据集条件隔离。生产改动另起记录，不能改写本次失败或用本批调试后分数冒充新留出成绩。随后接通统一main入口，并用另建新题验证质量与成本。\n',
              '最终项目可量化为：固定语料规模与版本、固定RAG检索指标、同题严格通过/核心覆盖、拒答与引用、真实请求/token/耗时、失败率和修复前后回归。当前已经具备这些记录的基础；未来简历只使用可复核且对应实际版本的数字。\n',
              '冻结文件：[题集](questions_frozen.json)、[评分规则](review_protocol.md)、[协议](frozen_protocol.json)、[PDF Gold核验](gold_verification_before_run.json)。汇总：[summary.json](summary.json)、[逐题指标](case_metrics.json)。所有离线分析脚本不产生模型调用。\n']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'strict_pass_rag':r['strict_pass_count'],'strict_pass_agent':a['strict_pass_count'],
                      'delta_percentage_points':delta*100,'actual_tokens':actual['total_tokens'],'report':str(OUT/'report.md')},ensure_ascii=False))


if __name__=='__main__':
    main()
