"""Citation syntax and source lookup only; never a semantic entailment score."""

import json
import re


def check_citations(answer, registry, require_citations=True):
    markers = re.findall(r'\[([^\[\]\n]+)\]', answer)
    numbers = sorted({int(value) for value in markers if re.fullmatch(r'\d+', value)})
    # 数学区间（如 [256; 512]）属于正文，不是格式错误的引用。
    interval = r'\s*[+-]?\d+(?:\.\d+)?\s*;\s*[+-]?\d+(?:\.\d+)?\s*'
    malformed = [value for value in markers
                 if re.match(r'(?:\d|E\d)', value) and not re.fullmatch(r'\d+', value)
                 and not re.fullmatch(interval, value)]
    invalid = [number for number in numbers if not 1 <= number <= len(registry)]
    return {
        'cited_numbers': numbers,
        'invalid_numbers': invalid,
        'malformed_markers': malformed,
        'has_citations': bool(numbers),
        'require_citations': require_citations,
        'structure_passed': not invalid and not malformed and (bool(numbers) or not require_citations),
        'cited_sources': [
            {'citation': number, 'chunk_id': registry[number - 1]['chunk_id'],
             'source': registry[number - 1]['source'], 'page': registry[number - 1]['page'],
             'text': registry[number - 1]['text']}
            for number in numbers if 1 <= number <= len(registry)],
        'semantic_support': 'requires_manual_review',
    }


def is_evidence_refusal(answer):
    """Recognize explicit evidence-insufficiency wording, not answer correctness."""
    return bool(re.search(
        r'\b(?:provided\s+)?(?:context|evidence|sources|documents)\s+'
        r'(?:does not|do not)\s+(?:contain|provide|include)\b'
        r'|\binsufficient (?:evidence|information)\b'
        r'|(?:现有|提供的|当前)(?:资料|材料|证据|上下文).{0,12}(?:不足|未提供|没有|不包含)',
        answer, re.I))


def repair_citations_once(query, context, answer, registry, generate):
    """Try one source-ID mapping; keep wording and expose semantic uncertainty."""
    initial = check_citations(answer, registry, require_citations=not is_evidence_refusal(answer))
    result = {'answer': answer, 'original_answer': answer, 'repair_candidate': None,
              'initial_check': initial, 'final_check': initial, 'repair_attempted': False,
              'repair_applied': False, 'repair_response': None, 'repair_prompt': None,
              'unresolved_blocks': [], 'status': 'not_needed',
              'note': 'Citation structure only; source relevance and claim meaning are not automatically verified.'}
    if initial['structure_passed']:
        return result

    # Preserve separators and wording; replace only citation-like markers.
    cleaned = re.sub(r'\[(?:\d[\d\s,.-]*|E\d+)\]', '', answer)
    parts = re.split(r'(\n\s*\n|\n(?=\s*(?:[-*]|\d+\.)\s))', cleaned)
    indices = [i for i in range(0, len(parts), 2) if parts[i].strip()]
    blocks = '\n\n'.join(f'B{number}: {parts[index].strip()}'
                           for number, index in enumerate(indices, 1))
    prompt = (
        'Assign source citations to the existing answer blocks. Do not rewrite the answer. '
        'Use only sources that directly support the factual statements in each block. '
        'If a block is not supported, assign an empty list; do not guess citations. '
        f'There are exactly {len(indices)} answer blocks. The JSON keys must be exactly '
        + ', '.join(f'B{n}' for n in range(1, len(indices) + 1)) + '. '
        'Map these answer block IDs to lists of integer source numbers, '
        'for example {"B1": [2], "B2": []}. Source numbers are values, not keys. '
        'Do not include explanations or markdown fences.\n\n'
        f'Question: {query}\n\nSources:\n{context}\n\nAnswer blocks:\n{blocks}\n\nJSON:')
    response = generate(prompt)
    result.update(repair_attempted=True, repair_prompt=prompt, repair_response=response)
    try:
        mapping = json.loads(response)
    except json.JSONDecodeError:
        result['status'] = 'invalid_response'
        return result
    expected = {f'B{n}' for n in range(1, len(indices) + 1)}
    if (not isinstance(mapping, dict) or set(mapping) != expected
            or any(not isinstance(values, list)
                   or any(type(n) is not int or not 1 <= n <= len(registry) for n in values)
                   for values in mapping.values())):
        result['status'] = 'invalid_response'
        return result
    for number, index in enumerate(indices, 1):
        numbers = list(dict.fromkeys(mapping[f'B{number}']))
        if numbers:
            content = parts[index].rstrip()
            parts[index] = content + ' ' + ''.join(f'[{n}]' for n in numbers) + parts[index][len(content):]
        else:
            result['unresolved_blocks'].append(number)
    candidate = ''.join(parts)
    result['repair_candidate'] = candidate
    checked = check_citations(candidate, registry)
    if result['unresolved_blocks'] or not checked['structure_passed']:
        result['status'] = 'incomplete_support'
        return result
    result.update(answer=candidate, final_check=checked, repair_applied=True,
                  status='applied_format_only')
    return result
