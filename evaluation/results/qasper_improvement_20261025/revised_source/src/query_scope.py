"""论文身份用于限定来源；检索问题保留原始语义，不反复拼接题名。"""
from pathlib import Path
import re


def paper_question(query):
    match = re.fullmatch(r'For the paper ["“](.+?)["”]\s*\(arXiv:\s*([\d.]+(?:v\d+)?)\),\s*'
                         r'answer this question:\s*(.+)', query.strip(), re.I | re.S)
    return {'title': match[1], 'paper_id': match[2], 'question': match[3].strip()} if match else None


def resolve_query_scope(query, chunks, sources=None):
    papers = {c['source']: c.get('title', '') for c in chunks}
    if sources is not None:
        if not isinstance(sources, (list, tuple)) or not sources or any(s not in papers for s in sources):
            raise ValueError('sources必须是当前知识库中存在的论文文件名列表。')
        selected = list(dict.fromkeys(sources))
    else:
        # 仅使用完整题名/文件名/明确arXiv编号；不将短缩写或一般术语当成硬过滤条件。
        selected = []
        for source, title in papers.items():
            names = [source, Path(source).stem]
            if len(title.strip()) >= 8:
                names.append(title.strip())
            if any(len(name) >= 4 and re.search(r'(?<![\w-])' + re.escape(name) + r'(?![\w-])', query, re.I)
                   for name in names):
                selected.append(source)
    bound = paper_question(query)
    content = query
    if bound and len(selected) == 1:
        source = selected[0]
        if (Path(source).stem == bound['paper_id'] or papers[source].casefold() == bound['title'].casefold()):
            content = bound['question']
    return {'sources': selected, 'retrieval_query': content}
