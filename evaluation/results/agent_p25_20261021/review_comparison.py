"""人工语义判断的可复核记录；程序只检查原文身份并汇总，不用词频评分。"""
import json
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def grade(points, strict, reason, citations=True, failures=None, refusal=False, over_refusal=False):
    return {'points': points, 'strict_pass': strict, 'reason': reason,
            'citation_support_pass': citations, 'citation_gaps': [], 'unsupported_claims': [],
            'appropriate_refusal': refusal, 'over_refusal': over_refusal, 'failure_categories': failures or []}


# 下列判断来自本助手逐条阅读实际答案、冻结评分点和该路径的引用原文。
# 引文存在性自动检查不产生这些语义标签；未完成/失败题也保留计划分母。
REVIEWS = {
    'b01': {
        'rag': grade(['covered','covered'],True,'Adam及三个常数完整，引用[7]的66原文逐项支持。'),
        'agent': grade(['covered','covered'],True,'与固定RAG相同的事实与引用；复核通过不额外计分。')},
    'b02': {
        'rag': grade(['covered','covered','covered'],True,'正确区分卷积2/4/5与FC隐藏层偏置1、其余0，并说明ReLU正输入促进早期学习；[1]/[2]对应177/178。'),
        'agent': grade(['missing','missing','missing'],False,'规划第二需求摘录why does it...，未包含DCNN主体；当前校验拒绝，未生成答案。',False,['planning_pronoun_scope_rejected'])},
    'b03': {
        'rag': grade(['partial','covered','covered'],False,'给出[256,512]、224x224与S=384初始化/微调所有层；冻结第1点同时要求说明S为等比例缩放后的最短边，实际未说明，按合取评分点记partial。',True,['incomplete_core_qualifier']),
        'agent': grade(['missing','missing','missing'],False,'规划摘录不在原问题中，被逐字引文校验拒绝；未生成答案。',False,['planning_nonverbatim_question_quote'])},
    'b04': {
        'rag': grade(['covered','covered'],True,'单位L2范数、点积=余弦、[-1,1]均由[1]608支持。'),
        'agent': grade(['covered','covered'],True,'同样完整；[1]608支持数值/相似度，[2]611的Normalize公式补充表示处理顺序。')},
    'b05': {
        'rag': grade(['covered','covered','covered'],True,'5/20检查点与VGG多个模型softmax后验平均分别正确，句间则字表达操作对象差异；[1]/[2]为73/296。'),
        'agent': grade(['covered','covered','covered'],True,'5/20与类别后验平均正确，显式说明checkpoint权重平均和预测后验平均的区别，未编造跨任务性能优势。')},
    'b06': {
        'rag': grade(['covered','covered','covered'],True,'DCNN错误率改善、VGG无收益且A-LRN例外、内存与时间开销均完整；末尾关于未提供其他成本的说明多余，但没有遗漏所问事实。'),
        'agent': grade(['missing','missing','missing'],False,'模型为两方法各抽取同一What do DCNN and VGG...片段，包含另一已声明主体，被主体隔离校验拒绝。',False,['planning_joint_subject_scope_rejected'])},
    'b07': {
        'rag': grade(['partial','covered','covered','covered'],False,'ASQA三类指标完整；DPR回答复述表2注434的passages措辞，未明确第2节400定义的“以问题为单位、Top-k至少一段含答案跨度”，冻结第1点评partial。434表注本身措辞有歧义，这不是无来源编造；保留为评审敏感案例。',True,['metric_denominator_not_explicit','source_caption_ambiguity']),
        'agent': grade(['partial','covered','covered','covered'],False,'与固定RAG相同：ASQA完整，DPR引用434却未澄清问题层面分母；复核通过不能消除此定义缺口。表注文字支持其表述，因此不标为凭空断言。',True,['metric_denominator_not_explicit','source_caption_ambiguity'])},
    'b08': {
        'rag': grade(['covered','covered'],True,'Transformer base的8 P100/100000步/12小时与DCNN的2 GTX580 3GB/5-6天完整；额外90周期有179支持，未计算跨任务加速比。'),
        'agent': grade(['covered','covered'],True,'与固定RAG相同，12/65及122/179原文支持硬件、步数和训练时间；未作同条件速度排名。')},
    'b09': {
        'rag': grade(['covered','covered','covered'],True,'RAG遗漏beam候选的额外前向、检索概率加权边际及Self-RAG归一化critique加权/段级beam均完整；[7]757、[3]996、[4]946支持。'),
        'agent': grade(['covered','covered','partial'],False,'RAG两个机制完整，Self-RAG归一化、加权和与生成概率相加的公式正确，但未提冻结第3点中的segment-level beam search；按主评分点记partial。此beam要求比题面直接问的score更细，另作公开的事后敏感性说明，不将其说成公式错误。',True,['incomplete_frozen_beam_context'])},
    'b10': {
        'rag': grade(['covered','covered'],True,'GPT-4生成反思监督并蒸馏入critic、CRAG用ChatGPT改写关键词两点完整；额外分组采样有982支持。无需托管critic的附带句沿用944原文，只限该文离线标注/生成器训练语境，不扩展为critic从不训练。'),
        'agent': grade(['covered','covered'],True,'两种外部模型角色清晰，944/982/1113支持监督数据，1283支持关键词改写；无额外主体或条件转移。')},
    'b11': {
        'rag': grade(['covered'],True,'明确当前语料不含Mistral7B论文及两项规格，不猜数值；运行前PDF清单不含该主论文。',True,refusal=True),
        'agent': grade(['covered'],True,'列出Mistral7B原文规格证据缺口，无训练token或窗口长度猜测；模型stop后在本地生成缺口说明，回答阶段0调用。',True,refusal=True)},
    'b12': {
        'rag': grade(['covered'],True,'明确缺少年度美元成本与固定刷新间隔，未把2016/2018索引快照差当刷新周期；额外快照/准确率描述分别由806/811支持。',True,refusal=True),
        'agent': grade(['covered'],True,'限定RAG搜索新增7段，再读806邻段新增4段，最终missing/stop；本地零回答调用列出两项真实缺口，没有猜年费或刷新周期。',True,refusal=True)},
}


def main():
    chunks = json.loads((ROOT/'data/processed/versions/all-papers-8-20261020/chunks.json').read_text())
    questions = {q['id']:q for q in json.loads((OUT/'questions_frozen.json').read_text())}
    result = {'_reviewer': 'Same coding assistant; frozen rubric; manual semantic reading, not independent blind adjudication.'}
    md = ['# P2.5 逐题原文与语义核对\n', '评分点与判定在semantic_review.json；此文列实际答案、原因和实际引用原文。\n']
    for qid, arms in REVIEWS.items():
        folder = OUT/'cases'/qid
        result[qid] = arms
        md += [f"## {qid}\n",questions[qid]['question']+'\n']
        for arm, row in arms.items():
            assert len(row['points'])==len(questions[qid]['reference_points'])
            if arm=='rag':
                record_path=folder/'rag.json'
                record=json.loads(record_path.read_text()) if record_path.exists() else {}
                answer=record.get('answer','')
                registry=record.get('ledger',{}).get('citation_registry',[])
            else:
                record_path=folder/'answer'/f'{qid}.json'
                record=json.loads(record_path.read_text()) if record_path.exists() else {}
                answer=record.get('result',{}).get('answer','')
                input_path=folder/'answer/inputs.json'
                registry=json.loads(input_path.read_text())['passages'] if input_path.exists() else []
            row['answer_available']=bool(answer)
            row['checked_citations']=[]
            for number in sorted({int(n) for n in re.findall(r'\[(\d+)\]',answer)}):
                assert 1<=number<=len(registry)
                c=registry[number-1]; raw=chunks[c['chunk_id']]
                assert all(c[k]==raw[k] for k in ('text','source','page'))
                row['checked_citations'].append({'number':number,'chunk_id':c['chunk_id'],
                    'source':c['source'],'page':c['page'],'quote':c['text'],'canonical_identity_verified':True})
            if row['strict_pass']:
                assert answer and all(p=='covered' for p in row['points'])
            md += [f"### {arm}: {'通过' if row['strict_pass'] else '未通过'}\n",answer or '(无交付答案)',
                   '\n评分：'+', '.join(row['points']), '\n依据：'+row['reason']+'\n']
            for ref in row['checked_citations']:
                md += [f"[{ref['number']}] {ref['source']} p.{ref['page']} / chunk{ref['chunk_id']}\n",'> '+ref['quote']+'\n']
    (OUT/'semantic_review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (OUT/'manual_review.md').write_text('\n'.join(md)+'\n')
    print(json.dumps({'reviewed_cases':len(REVIEWS),'arms':sum(len(v) for v in REVIEWS.values()),'generation_api_calls':0}))


if __name__=='__main__':
    main()
