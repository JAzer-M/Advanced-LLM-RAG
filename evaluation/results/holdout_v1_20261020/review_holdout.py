"""Record the assistant's semantic review of actual answers and their citations."""
from collections import Counter
import json
from pathlib import Path

STAGE = Path(__file__).resolve().parent
OUT = STAGE if (STAGE / 'questions_frozen.json').exists() else STAGE / 'results'

# Each point follows the frozen reference_points in order. No result changes the rubric.
# Claims are meaningful factual units; a compound statement sharing evidence can be one unit.
REVIEWS = {
    'h01': {
        'points': [('covered', [1], '明确 epsilon=0.1。'),
                   ('covered', [2], '明确 perplexity 变差，accuracy/BLEU 改善，并解释模型更不确定。')],
        'claims': [('epsilon=0.1', [1], 'supported'),
                   ('更不确定使 perplexity 受损', [2], 'supported'),
                   ('accuracy 与 BLEU 改善', [2], 'supported')],
        'note': '核心完整，无新增错误。', 'failure_categories': []},
    'h02': {
        'points': [('partial', [1, 3], '回答切成条带/独立信息，但缺少一两句结果保留为一条、长结果按几句切分的粒度规则。'),
                   ('covered', [3], '微调检索评估器逐条带打相关性分并过滤。'),
                   ('covered', [3], '相关条带按原顺序拼接为 internal knowledge。')],
        'claims': [('Correct 后执行分解、过滤、重组', [2], 'supported'),
                   ('相关文档切成内部条带，每条假定含独立信息', [1, 3], 'supported'),
                   ('微调检索评估器计算每条带相关性并过滤无关条带', [3], 'supported'),
                   ('相关条带按顺序拼接形成内部知识', [3], 'supported'),
                   ('相关文档仍可能有噪声，精炼用于提取关键条带', [4], 'supported')],
        'note': '漏答粒度。Gold 1279 不在初始候选，也未进最终/生成上下文；不能归咎为单纯生成遗漏。',
        'failure_categories': ['initial_candidate_miss', 'incomplete_answer']},
    'h03': {
        'points': [('covered', [7], '组内按长度排序、相近长度组批、仅补到批内最大长度；B/b 示例也正确。'),
                   ('covered', [2], '明确 WordPiece 等独立预处理跨 CPU 核心并行。')],
        'claims': [('分组按长度排序并组相近长度的批，补到批最大长度；B=100000/b=128 为示例', [7], 'supported'),
                   ('WordPiece 等独立预处理跨 CPU 核心并行', [2], 'supported'),
                   ('可用时多 GPU 并行编码文档批', [7], 'supported'),
                   ('图6列有 per-batch maximum length 与 length-based bucketing 吞吐优化', [3], 'supported')],
        'note': '核心完整，额外多 GPU/图6信息也由实际引用支持。', 'failure_categories': []},
    'h04': {
        'points': [('covered', [1], '第一 FC->7x7，后两 FC->1x1，应用于整张未裁剪图像。'),
                   ('covered', [9], '对类别分数图做空间平均，保留原文 sum-pooling 说法。'),
                   ('missing', [], '没有回答原图与水平翻转图的 softmax 类别概率平均。')],
        'claims': [('FC 转为 7x7/1x1 卷积后应用整张未裁剪图像', [1], 'supported'),
                   ('分数图通道等于类别数、空间分辨率随输入大小变化', [9], 'supported'),
                   ('空间平均得到固定大小类别分数向量', [9], 'supported')],
        'note': 'Gold 266/267 均在上下文，模型还实际引用了包含翻转平均的[9]，却漏答该核心点。',
        'failure_categories': ['evidence_available_but_omitted']},
    'h05': {
        'points': [('partial', [1], '拷贝的层范围及中间层随机都正确，但未交代先随机初始化并训练浅层配置 A 这一前置步骤；按冻结的完整核心点记 partial。'),
                   ('covered', [1], '明确预初始化层不降低学习率并继续训练。'),
                   ('covered', [2], 'DCNN 每层零均值 Gaussian、标准差0.01。')],
        'claims': [('VGG 拷贝 A 的前四卷积层和后三全连接层，中间随机；拷贝层不降低学习率且继续学习', [1], 'supported'),
                   ('VGG 随机权重零均值、variance 10^-2，bias=0', [7], 'supported'),
                   ('DCNN 每层零均值 Gaussian、标准差0.01', [2], 'supported'),
                   ('DCNN 第二/四/五卷积层与全连接隐藏层 bias=1，其余=0', [2, 8], 'supported')],
        'note': '主要初始化比较正确；保留 A 的前置训练步骤遗漏。VGG 原文确写 variance，不能凭常识把该回答记成标准差混淆。',
        'failure_categories': ['evidence_available_but_omitted']},
    'h06': {
        'points': [('covered', [3, 5], 'DCNN 两 GPU 各放一半 kernel/神经元，只在部分层跨卡通信，第三/四层例子正确。'),
                   ('covered', [1], 'VGG 拆分图像 batch 做数据并行。'),
                   ('covered', [1], '同步平均各 GPU 梯度，得到整批梯度，与单 GPU 对应计算一致。')],
        'claims': [('DCNN 两 GPU 各一半 kernel/神经元，仅特定层通信；第三层跨卡、第四层同卡', [3], 'supported'),
                   ('DCNN 图2上下两个层部件分属两 GPU', [5], 'supported'),
                   ('VGG 拆 batch 到各 GPU 并行，平均梯度为完整 batch 梯度', [1], 'supported'),
                   ('VGG 梯度计算同步，结果与单 GPU 相同', [1], 'supported')],
        'note': '跨篇综合完整。', 'failure_categories': []},
    'h07': {
        'points': [('covered', [1], '线性 warmup 4000 步。'),
                   ('covered', [1], '之后按 step_num 的平方根倒数下降，以训练步数控制。'),
                   ('covered', [8], 'DCNN 验证误差停滞时手动除10，初值0.01、下降三次均给出。')],
        'claims': [('Transformer 前4000步线性增加，之后按步数平方根倒数下降', [1], 'supported'),
                   ('Transformer 调度由训练步数而非验证误差触发', [1], 'supported'),
                   ('DCNN 各层同学习率，验证误差停滞时手动除10，初值0.01、下调三次', [8], 'supported'),
                   ('两篇降学习率的控制依据不同', [1, 8], 'supported')],
        'note': '核心与比较完整。开头“仅能部分回答”和结尾对额外预热的保留措辞多余，但未拒绝或遗漏题目所需答案；不按关键词将其误计为实质过度拒答。',
        'unnecessary_insufficiency_caveat': True, 'failure_categories': []},
    'h08': {
        'points': [('covered', [6], 'DPR reader 从检索段落抽取答案片段，明确输出受段落 span 约束。'),
                   ('partial', [6], '给出 passage-selection/span 两种评分，但缺少从 passage-selection 最高的段落选择其中最佳 span 的最终决策规则。'),
                   ('covered', [2], 'RAG 可以自由形式抽象生成，不限于拷贝片段，文中明确说能力不同。')],
        'claims': [('DPR 对至多100段给段落选择分及抽取 span 的分数', [6], 'supported'),
                   ('DPR 答案为检索段落中的 span', [6], 'supported'),
                   ('RAG 支持超越抽取的自由形式抽象生成', [2], 'supported')],
        'note': '缺少最终选择规则；Gold 465 未进上下文。末段强调缺少显式跨篇比较句，属于不必要的比较保留措辞；前文已实际说明输出约束差异，因此不把它算作完全拒绝比较。',
        'unnecessary_insufficiency_caveat': True,
        'failure_categories': ['selected_evidence_miss', 'incomplete_answer', 'unnecessary_comparison_caveat']},
    'h09': {
        'points': [('partial', [1], 'top-2000各路、并集、线性公式正确，但未给出开发集选择 lambda=1.1 的细节。'),
                   ('covered', [8], '重排另一检索器（通常基于词项）返回的候选。'),
                   ('partial', [9, 10], '说明全库向量索引直接检索，但没有 FAISS 及近似过滤->精炼两个阶段。')],
        'claims': [('DPR 合并 BM25/DPR 各自 top-2000，以 BM25+lambda*sim 重排并集', [1], 'supported'),
                   ('ColBERT 可重排另一词项检索器候选或直接全库检索', [8], 'supported'),
                   ('ColBERT 全库模式用向量相似度索引', [9], 'supported'),
                   ('文中 MS MARCO 全库设置从8.8M文档直接取每题 top-1000', [10], 'supported')],
        'note': '高层区别正确且替代证据549/667支持全库检索，但冻结标准中的 lambda=1.1 与 FAISS 两阶段细节均遗漏。相应 Gold 438/627/628 未进入上下文。',
        'failure_categories': ['selected_evidence_miss', 'incomplete_answer']},
    'h10': {
        'points': [('missing', [], '未得到 RAG 的 Exact Match 判据；实际上下文没有 Gold 765。'),
                   ('partial', [2], 'Self-RAG 的 gold-answer inclusion 与不要求 strict exact match 已答对，但完整核心点还要求说明两篇得分标准不同；答案明确表示无法比较，因此该复合点按冻结规则记 partial。')],
        'claims': [('Self-RAG 用 gold answer 是否包含在生成中，而非 strict exact matching', [2], 'supported'),
                   ('所引 RAG [5] 只描述 TriviaQA 答案候选过滤', [5], 'supported'),
                   ('所引 RAG [9] 描述负对数似然训练及抽取式 QA 对比，未给出评测判据', [9], 'supported')],
        'note': '可答题部分拒答源于上下文缺少 RAG EM 原文，不是证据已齐的实质过度拒答。分解额外把 PopQA 绑定到原始 RAG（原题只把 PopQA/TriviaQA 指向 Self-RAG）；该漂移已观察到，但未做消融，不能宣称已证明因果。Gold 765 初始漏召、补查候选已有，最终仍未入选。',
        'partial_refusal_due_to_missing_context': True,
        'failure_categories': ['decomposition_scope_drift', 'initial_candidate_miss', 'selected_evidence_miss', 'incomplete_answer']},
    'h11': {
        'points': [('covered', [], '明确八篇资料不含 Mamba/所需训练数据量与隐藏状态维度，未猜数字。')],
        'claims': [('当前八篇库中没有 Mamba 论文与所需模型规格，无法据此回答', [], 'supported')],
        'appropriate_refusal': True,
        'note': '正确拒答；八篇 PDF 清单与全文 Mamba 扫描在运行前已核对，未依赖检索失败来定义不可答。',
        'failure_categories': []},
    'h12': {
        'points': [('covered', [], '拒绝推断原始 Transformer 的同协议 ImageNet 准确率，没有拿 BLEU 或 VGG 数字替代所问结果。')],
        'claims': [('所给上下文没有所问原始 Transformer 同协议 ImageNet 结果，无法推断', [], 'supported'),
                   ('VGG D 在256尺度的 top-1 验证误差为27.0%', [], 'supported'),
                   ('Transformer 翻译结果与 VGG 图像分类结果属于不同任务/数据集', [], 'supported')],
        'uncited_context_support': {'VGG D 在256尺度的 top-1 验证误差为27.0%': [285],
                                    'Transformer 翻译结果与 VGG 图像分类结果属于不同任务/数据集': [81, 285]},
        'citation_gaps': ['拒答后额外报告 VGG D 的27.0%验证误差及跨任务说明，却没有标注现成的上下文[2]/[1]；数值可证，但可追溯引用缺失。'],
        'appropriate_refusal': True,
        'note': '拒答内容正确，附带的27.0%也由真实上下文285支持；保留追加数值缺引用的问题，严格引用标准下不通过，不把它误报成数值幻觉。',
        'failure_categories': ['uncited_additional_numeric_claim']},
}


def main():
    questions = json.loads((OUT / 'questions_frozen.json').read_text())
    assert {q['id'] for q in questions} == set(REVIEWS), 'Finish all manual reviews before publishing.'
    records = []
    for q in questions:
        qid = q['id']
        result = json.loads((OUT / f'{qid}.json').read_text())
        review = REVIEWS[qid]
        assert len(review['points']) == len(q['reference_points'])
        registry = result.get('ledger', {}).get('citation_registry', [])
        points = [{'reference_point': point, 'status': status, 'answer_citation_numbers': citations,
                   'reason': reason} for point, (status, citations, reason) in zip(q['reference_points'], review['points'])]
        claims = []
        for statement, citations, status in review['claims']:
            assert all(number in result['citation_structure']['cited_numbers'] for number in citations)
            context_ids = review.get('uncited_context_support', {}).get(statement, [])
            claims.append({'claim': statement, 'status': status, 'answer_citation_numbers': citations,
                           'evidence': [{'citation': number, **registry[number - 1]} for number in citations],
                           'uncited_context_evidence': [chunk for chunk in registry if chunk['chunk_id'] in context_ids]})
        covered = sum(p['status'] == 'covered' for p in points)
        is_answerable = q['type'] != 'unanswerable'
        supported = all(c['status'] == 'supported' for c in claims)
        refused = review.get('over_refusal', False)
        strict = result['status'] == 'completed' and supported and not refused and (
            covered == len(points) if is_answerable else review.get('appropriate_refusal', False))
        strict = strict and result.get('citation_structure', {}).get('structure_passed', False) and not review.get('citation_gaps')
        records.append({'id': qid, 'type': q['type'], 'pipeline_status': result['status'],
                        'core_points': points, 'covered': covered, 'total_core_points': len(points),
                        'core_point_coverage': covered / len(points),
                        'important_claims': claims, 'strict_pass': strict,
                        'over_refusal': refused, 'appropriate_refusal': review.get('appropriate_refusal'),
                        'citation_gaps': review.get('citation_gaps', []),
                        'partial_refusal_due_to_missing_context': review.get('partial_refusal_due_to_missing_context', False),
                        'unnecessary_insufficiency_caveat': review.get('unnecessary_insufficiency_caveat', False),
                        'failure_categories': review['failure_categories'], 'note': review['note']})
    groups = {}
    for name in ('all_answerable', 'single_document', 'cross_document', 'unanswerable', 'all_questions'):
        members = [r for r in records if (r['type'] != 'unanswerable' if name == 'all_answerable'
                    else True if name == 'all_questions' else r['type'] == name)]
        success = [r for r in members if r['pipeline_status'] == 'completed']
        groups[name] = {'planned': len(members), 'executed_successfully': len(success),
                        'strict_pass_count': sum(r['strict_pass'] for r in members),
                        'strict_pass_rate_planned': sum(r['strict_pass'] for r in members) / len(members),
                        'strict_pass_rate_successful': sum(r['strict_pass'] for r in success) / len(success) if success else None}
        if name != 'unanswerable':
            answerable = [r for r in members if r['type'] != 'unanswerable']
            groups[name].update(core_point_coverage_macro=sum(r['core_point_coverage'] for r in answerable) / len(answerable),
                                covered_core_points=sum(r['covered'] for r in answerable),
                                total_core_points=sum(r['total_core_points'] for r in answerable))
    claim_counts = Counter(c['status'] for r in records for c in r['important_claims'])
    payload = {'reviewer': 'This assistant; semantic review of actual answers against provided original passages, not independent blind adjudication.',
               'scoring': 'Frozen reference_points; covered=1, partial/missing/wrong=0; macro over 10 answerable questions.',
               'groups': groups, 'important_claim_support_counts': dict(claim_counts),
               'appropriate_refusals': sum(r['appropriate_refusal'] is True for r in records),
               'answerable_over_refusals': sum(r['over_refusal'] for r in records if r['type'] != 'unanswerable'),
               'partial_refusals_due_to_missing_context': sum(r['partial_refusal_due_to_missing_context'] for r in records),
               'cases_with_citation_gaps': sum(bool(r['citation_gaps']) for r in records),
               'cases': records}
    (OUT / 'manual_review.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    lines = ['# P1 留出集 v1：逐题人工语义核对', '',
             '评审为本助手；标准在模型运行前冻结。partial/missing/wrong 都不计完整覆盖，不冒充第三方盲评。', '']
    for record in records:
        lines += [f"## {record['id']}：严格通过={record['strict_pass']}；核心点={record['covered']}/{record['total_core_points']}",
                  '', record['note'], '', f"[原始答案与全部上下文]({record['id']}.md)", '',
                  '| 预定核心点 | 判断 | 引用 | 理由 |', '| --- | --- | --- | --- |']
        for point in record['core_points']:
            lines.append(f"| {point['reference_point']} | {point['status']} | {point['answer_citation_numbers']} | {point['reason']} |")
        lines += ['', '| 实际重要断言 | 引用 | 语义支撑 |', '| --- | --- | --- |']
        for claim in record['important_claims']:
            lines.append(f"| {claim['claim']} | {claim['answer_citation_numbers']} | {claim['status']} |")
        lines.append('')
    (OUT / 'manual_review.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in payload.items() if k != 'cases'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
