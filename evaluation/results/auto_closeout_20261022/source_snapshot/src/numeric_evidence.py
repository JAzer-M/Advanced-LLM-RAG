# 仅解析明确表达的卷积核数量、空间尺寸、通道和层号；每条结果保留原文及偏移。
# 无法识别的字段保持未知，论文/模型主体归属由 grounded_evidence.py 另行处理。

"""Conservative parser for explicit English convolution-kernel specifications.

No model calls or architecture defaults. Only ``N kernels of size H x W [x C]``
is supported. Document ownership is deliberately outside this parser's scope.
Returned offsets and quotes always refer to the unmodified source text.
"""

import re


_ORDINALS = dict(zip(
    'first second third fourth fifth sixth seventh eighth ninth tenth '
    'eleventh twelfth thirteenth fourteenth fifteenth sixteenth seventeenth '
    'eighteenth nineteenth twentieth'.split(), range(1, 21)))
_ORDINAL = '|'.join(_ORDINALS) + r'|\d+(?:st|nd|rd|th)'
_SUBJECT = re.compile(
    rf'(?:^\s*|,\s*(?:and\s+)?|\band\s+)(?:the\s+)?'
    rf'(?P<ordinal>{_ORDINAL})\s+convolutional\s+layer\b', re.I)
_SPEC = re.compile(
    r'(?<![\w.\-])(?P<count>[1-9]\d*)\s+(?:kernels?|filters?)\s+(?:of|with)\s+(?:spatial\s+)?size\s+'
    r'(?P<h>[1-9]\d*)\s*[×x]\s*(?P<w>[1-9]\d*)'
    r'(?:\s*[×x]\s*(?P<c>[1-9]\d*))?(?!\d|\.\d|\s*[×x])', re.I)
_BREAK = re.compile(r'[.!?;]\s+')
_HYPHENATED = re.compile(r'(?<=[A-Za-z])-\s+(?=[a-z])')


# 只在检索副本中合并 PDF 断词，同时保存映射，保证引文能还原到原文本位置。
def _search_text(text):
    """Remove PDF word breaks in a shadow string, keeping a raw offset map."""
    removed = set()
    for match in _HYPHENATED.finditer(text):
        removed.update(range(match.start(), match.end()))
    offsets = [index for index in range(len(text)) if index not in removed]
    return ''.join(text[index] for index in offsets), offsets


# 按明确子句绑定卷积层号，避免把“上一层的输出”误当当前规格的主体。
def _parse_prose(text):
    """Extract all supported specifications; unknown layers/channels stay None.

    Layer binding is limited to explicit clause subjects, so an input reference
    such as 'output of the first layer' cannot overwrite the second-layer
    subject. Unsupported/ambiguous grammar is retained with layer=None.
    """
    shadow, offsets = _search_text(text)
    records = []
    previous_end = 0
    for match in _SPEC.finditer(shadow):
        breaks = list(_BREAK.finditer(shadow, previous_end, match.start()))
        start = breaks[-1].end() if breaks else previous_end
        subjects = list(_SUBJECT.finditer(shadow[start:match.start()]))
        layer = None
        quote_start = match.start()
        if len(subjects) == 1:
            subject = subjects[0]
            ordinal = subject['ordinal'].lower()
            layer = _ORDINALS.get(ordinal)
            if layer is None:
                layer = int(re.match(r'\d+', ordinal).group())
            quote_start = start + subject.start()
        elif not subjects:
            label = re.match(r'\s*(?:convolutional\s+)?layer\s+([1-9]\d*)\b',
                             shadow[start:match.start()], re.I)
            if label:
                layer = int(label[1])
                quote_start = start + label.start()
        raw_start = offsets[quote_start]
        raw_end = offsets[match.end() - 1] + 1
        records.append({
            'kind': 'convolution_specification',
            'layer': layer, 'kernel_count': int(match['count']),
            'spatial_kernel_size': [int(match['h']), int(match['w'])],
            'channels_per_kernel': int(match['c']) if match['c'] else None,
            'evidence_quote': text[raw_start:raw_end],
            'evidence_start': raw_start, 'evidence_end': raw_end,
        })
        previous_end = match.end()
    return records


_LABELLED = re.compile(
    r'(?:^|\n)\s*Layer\s+(?P<layer>[1-9]\d*):\s*(?P<count>[1-9]\d*)\s+'
    r'(?:filters|kernels);\s*kernel\s+size\s+(?P<h>[1-9]\d*)\s*[×x]\s*'
    r'(?P<w>[1-9]\d*);\s*input\s+channels\s+(?P<c>[1-9]\d*)(?!\d|\.\d)', re.I)


def _record(text, start, end, layer, count, h, w, channels):
    return {'kind': 'convolution_specification', 'layer': int(layer),
            'kernel_count': int(count), 'spatial_kernel_size': [int(h), int(w)],
            'channels_per_kernel': int(channels) if channels else None,
            'evidence_start': start, 'evidence_end': end,
            'evidence_quote': text[start:end]}


# 只接受表头和数值格式均明确的四列表格，不能猜测任意 PDF 表格结构。
def _parse_tables(text):
    lines = text.splitlines(keepends=True)
    offset, header_start, header = 0, None, None
    for line in lines:
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        keys = [c.lower() for c in cells]
        if len(keys) == 4 and keys[0] == 'layer' and keys[1] in ('filters', 'kernels', 'kernel count') and keys[2] in ('kernel size', 'spatial size') and keys[3] in ('input channels', 'channels per kernel'):
            header_start, header = offset, keys
        elif header is not None and line.lstrip().startswith('|'):
            if all(re.fullmatch(r'[:\- ]+', c) for c in cells):
                pass
            elif len(cells) == 4 and all(re.fullmatch(r'[1-9]\d*', cells[i]) for i in (0, 1, 3)):
                size = re.fullmatch(r'([1-9]\d*)\s*[×x]\s*([1-9]\d*)', cells[2], re.I)
                if size:
                    yield _record(text, header_start, offset + len(line.rstrip('\r\n')),
                                  cells[0], cells[1], size[1], size[2], cells[3])
            else:
                header = None
        else:
            header = None
        offset += len(line)


# 汇总三种支持格式的解析结果，未知层号/通道不按架构常识补全。
def parse_convolution_specs(text):
    """Parse declared prose, labelled fields, and explicit Markdown tables.

    Unrecognised grammar is not completed from architecture defaults. Support
    remains deliberately bounded; this is not a scientific-text understanding
    engine. Every output includes an exact raw quotation and offsets.
    """
    records = _parse_prose(text)
    for match in _LABELLED.finditer(text):
        records.append(_record(text, match.start(), match.end(), match['layer'],
                               match['count'], match['h'], match['w'], match['c']))
    records.extend(_parse_tables(text))
    return sorted(records, key=lambda r: (r['evidence_start'], r['evidence_end']))
