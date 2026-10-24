# 把选中原文整理成证据账本：有限数值解析、主体线索、原句和统一引用编号。
# 输出用于辅助生成与人工核对；规则抽取和主体提示不等于通用语义理解。

"""Bounded typed grounding and extractive evidence for paper QA.

This module does NOT claim arbitrary natural-language entailment. Numeric
claims are rechecked against source parsing; other text is quoted verbatim.
Ownership uses conservative explicit clauses and bounded previous context.
Unknowns are surfaced, never silently converted into document subjects.
"""

import json
import re
import unicodedata

from src.numeric_evidence import parse_convolution_specs


def _normal(text):
    return re.sub(r'(?<=[A-Za-z])-\s+(?=[a-z])', '', unicodedata.normalize('NFKC', text))


_GENERIC_NAMES = {'CNN', 'GPU', 'RGB', 'PDF', 'FC', 'ReLU', 'ConvNet', 'ConvNets',
                  'ILSVRC', 'JSON', 'LSTM', 'RNN'}
_NAME = r'(?:[A-Z][a-z]+[A-Z][A-Za-z0-9-]*|[A-Z]{2,}(?:-\d+)?)'
_OWN = re.compile(r'\b(?:we\s+(?:also\s+)?(?:use|utilise|utilize|employ|propose|introduce|address|fix)|our\s+(?:network|model|architecture|CNN|ConvNets?|method|main contribution))\b', re.I)


def _signals(text):
    text = _normal(text)
    names = {m.group() for m in re.finditer(r'\b' + _NAME + r'\b', text)
             if m.group() not in _GENERIC_NAMES}
    direct = {name for name in names if re.search(
        re.escape(name) + r'\s*(?:\([^)]*\))?\s*'
        r'(?:,\s*which\s+|,\s*[^,.;\n]+,\s*)?'
        r'(?:uses?|has|employs?|is|was|contains?)\b', text)}
    own = bool(_OWN.search(text))
    contrast = bool(re.search(r'^\s*(?:Unlike|Compared with|In contrast to)\b.*?,\s*we\s+(?:use|employ)', text, re.I))
    if contrast and own:
        return 'own', None
    if len(direct) == 1:
        return 'named', next(iter(direct))
    if len(names) > 1 or names and own:
        return 'ambiguous', None
    if own:
        return 'own', None
    if len(names) == 1:
        return 'candidate_name', next(iter(names))
    return 'none', None


# 只向前读取同来源、相邻页、同章节的有限原文；找不到明确主体就保留未知。
def resolve_subject(chunks, index, quote=None, *, max_previous=4, max_chars=4096):
    """Resolve explicit subject/author anchors; no section-title-only default."""
    target = chunks[index]
    quote = quote if quote is not None else target['text']
    checked = [target['chunk_id']]

    def answer(subject, basis, anchor=None):
        return {'subject': subject, 'basis': basis, 'context_chunk_ids': checked.copy(),
                'identity_quote': anchor['text'] if anchor else None,
                'identity_chunk_id': anchor['chunk_id'] if anchor else None}

    signal, name = _signals(quote)
    if signal == 'named':
        return answer(name, 'explicit_named_clause', target)
    if signal == 'own':
        return answer(target.get('title') or target['source'], 'explicit_author_clause', target)
    if signal == 'ambiguous':
        return answer(None, 'ambiguous_subject')
    # An earlier clause in the same chunk may establish the antecedent.
    start = target['text'].find(quote)
    prefix = target['text'][:start] if start >= 0 else ''
    candidates = [(target, prefix)] if prefix.strip() else []
    consumed = len(quote) + len(prefix)
    for position in range(index - 1, max(-1, index - max_previous - 1), -1):
        previous = chunks[position]
        if previous['source'] != target['source']:
            break
        if not 0 <= target['page'] - previous['page'] <= 1:
            break
        if previous.get('section') != target.get('section'):
            break
        if consumed + len(previous['text']) > max_chars:
            break
        candidates.append((previous, previous['text']))
        consumed += len(previous['text'])
    third_party = bool(re.search(r'\b(?:they|their)\b', _normal(quote), re.I))
    for anchor, text in candidates:
        if anchor['chunk_id'] not in checked:
            checked.append(anchor['chunk_id'])
        signal, name = _signals(text)
        if signal == 'ambiguous':
            return answer(None, 'ambiguous_previous_context')
        if signal == 'named':
            return answer(name, 'bounded_named_antecedent', {**anchor, 'text': text})
        if signal == 'own' and not third_party:
            return answer(target.get('title') or target['source'],
                          'bounded_author_anchor', {**anchor, 'text': text})
    return answer(None, 'insufficient_identity_evidence')


# 为当前回答的原文注册连续引用序号，重复片段复用同一编号。
def _citation(registry, chunk):
    for i, existing in enumerate(registry, 1):
        if existing['chunk_id'] == chunk['chunk_id'] and existing['source'] == chunk['source']:
            return i
    registry.append(chunk)
    return len(registry)


# 数值规格无法解析时保留原句；数值的主体不明时放入 unresolved，不升级成事实断言。
def build_ledger(chunks, selected_ids):
    """Keep all supported numeric facts and exact sentences; expose unknowns.

    The quote fallback preserves other paper topics without pretending that
    their meaning has been parsed as numeric facts or verified as paraphrases.
    """
    by_id = {c['chunk_id']: (i, c) for i, c in enumerate(chunks)}
    registry = [by_id[cid][1] for cid in selected_ids]
    records, unknown = [], []
    for cid in selected_ids:
        index, chunk = by_id[cid]
        specs = parse_convolution_specs(chunk['text'])
        units = specs or [
            {'kind': 'quotation', 'evidence_quote': m.group(),
             'evidence_start': m.start(), 'evidence_end': m.end()}
            for m in re.finditer(r'[^.!?]+(?:[.!?](?=\s|$)|$)', chunk['text'])
            if len(m.group().strip()) >= 30]
        for unit in units:
            identity = resolve_subject(chunks, index, unit['evidence_quote'])
            citations = [_citation(registry, chunk)]
            anchor_id = identity['identity_chunk_id']
            if anchor_id is not None:
                anchor = by_id[anchor_id][1]
                anchor_cite = _citation(registry, anchor)
                if anchor_cite not in citations:
                    citations.append(anchor_cite)
            record = {**unit, 'subject': identity['subject'], 'identity': identity,
                      'source': chunk['source'], 'chunk_id': cid, 'page': chunk['page'],
                      'citations': citations, 'record_id': f'E{len(records) + len(unknown) + 1}'}
            # Exact quotations assert only that the text occurs, not its entity.
            # Unknown numeric subjects are not promoted to factual assertions.
            if unit['kind'] != 'quotation' and identity['subject'] is None:
                unknown.append(record)
            else:
                records.append(record)
    return {'records': records, 'unresolved': unknown, 'citation_registry': registry,
            'selected_ids': list(selected_ids)}


_FIELDS = ('kind', 'subject', 'layer', 'kernel_count', 'spatial_kernel_size',
           'channels_per_kernel', 'evidence_quote', 'citations')


# 仅校验账本字段/原句/可解析数值的一致性，不能审核任意自然语言改写。
def validate_claim(claim, ledger):
    """Typed/extractive entailment only; unrestricted paraphrases abstain."""
    record = next((r for r in ledger['records'] if r['record_id'] == claim.get('record_id')), None)
    if record is None:
        return {'accepted': False, 'reason': 'unknown_record'}
    for field in _FIELDS:
        if claim.get(field) != record.get(field):
            return {'accepted': False, 'reason': 'claim_or_support_mismatch:' + field}
    if any(key not in record for key in claim):
        return {'accepted': False, 'reason': 'unverifiable_additional_claim'}
    if any(claim[key] != record[key] for key in claim):
        return {'accepted': False, 'reason': 'canonical_record_mismatch'}
    source = next(c for c in ledger['citation_registry'] if c['chunk_id'] == record['chunk_id'])
    if source['text'][record['evidence_start']:record['evidence_end']] != record['evidence_quote']:
        return {'accepted': False, 'reason': 'source_quote_mismatch'}
    if record['kind'] == 'convolution_specification':
        reparsed = parse_convolution_specs(record['evidence_quote'])
        fields = ('layer', 'kernel_count', 'spatial_kernel_size', 'channels_per_kernel')
        if not any(all(p[f] == record[f] for f in fields) for p in reparsed):
            return {'accepted': False, 'reason': 'numeric_entailment_failed'}
    return {'accepted': True, 'reason': 'typed_or_extractive_support_only'}


# 渲染完整证据视图并补回遗漏记录；它是审阅材料，不是最终科研问答。
def render_complete(ledger, proposed_ids=None):
    """Program rendering cannot lose accepted records or invent citation IDs."""
    by_id = {r['record_id']: r for r in ledger['records']}
    proposed_ids = proposed_ids or []
    ordered = list(dict.fromkeys(i for i in proposed_ids if i in by_id))
    restored = [i for i in by_id if i not in ordered]
    ordered += restored
    lines = []
    for rid in ordered:
        r = by_id[rid]
        checked = validate_claim(r, ledger)
        if not checked['accepted']:
            raise ValueError(f'Invalid canonical evidence {rid}: {checked}')
        cite = ''.join(f'[{i}]' for i in r['citations'])
        if r['kind'] == 'convolution_specification':
            h, w = r['spatial_kernel_size']
            layer = r['layer'] if r['layer'] is not None else 'unknown'
            lines.append(f"- {r['subject']}: layer {layer}; spatial {h}×{w}; "
                         f"{r['kernel_count']} kernels; {r['channels_per_kernel']} channels/kernel. {cite}")
        else:
            lines.append(f"- Source quotation ({r['source']}, p.{r['page']}): “{r['evidence_quote'].strip()}” {cite}")
    if ledger['unresolved']:
        lines.append('\nUnresolved subject (not promoted to a factual assertion):')
        for r in ledger['unresolved']:
            cite = ''.join(f'[{i}]' for i in r['citations'])
            lines.append(f"- Source quotation: “{r['evidence_quote']}” {cite}")
    return {'answer': '\n'.join(lines), 'rendered_ids': ordered,
            'restored_omissions': restored, 'rejected_ids': [i for i in proposed_ids if i not in by_id],
            'coverage_of_accepted_records': len(ordered) / len(by_id) if by_id else None,
            'unresolved_count': len(ledger['unresolved']),
            'limitation': 'Evidence view, not an unrestricted generated scientific explanation.'}


# 为生成提供数值和主体提示；main 仍同时保留原始片段供核对。
def render_guidance(ledger):
    """Supplement raw context with typed numbers and bounded subject hints."""
    lines = []
    for r in ledger['records']:
        cite = ''.join(f'[{i}]' for i in r['citations'])
        if r['kind'] == 'convolution_specification':
            h, w = r['spatial_kernel_size']
            layer = r['layer'] if r['layer'] is not None else 'unknown'
            channels = r['channels_per_kernel'] if r['channels_per_kernel'] is not None else 'unknown'
            lines.append(f"- {r['subject']}: convolutional layer {layer}; spatial kernel size "
                         f"{h}×{w}; {r['kernel_count']} kernels; {channels} channels per kernel. {cite}")
        elif r['identity']['basis'] in ('explicit_named_clause', 'bounded_named_antecedent'):
            lines.append(f"- Rule-based subject attribution: {r['subject']}; "
                         f"passage: “{r['evidence_quote'].strip()}” {cite}")
    for r in ledger['unresolved']:
        cite = ''.join(f'[{i}]' for i in r['citations'])
        lines.append(f"- Subject unresolved; do not assign this specification to a network "
                     f"based on the filename alone: “{r['evidence_quote']}” {cite}")
    return '\n'.join(lines)
