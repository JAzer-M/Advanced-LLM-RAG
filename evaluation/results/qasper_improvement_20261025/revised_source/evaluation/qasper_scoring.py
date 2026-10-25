"""QASPER修订口径：显式拒答、独立短答和段落空白归一；旧评测脚本保持原字节。"""
import re
import unicodedata
from evaluation.qasper_eval import clean_answer, token_f1


def normalize_evidence(text):
    return ' '.join(unicodedata.normalize('NFKC', text).split())


def paragraph_f1(prediction, reference):
    predicted = {normalize_evidence(p) for p in prediction if p.strip()}
    expected = {normalize_evidence(p) for p in reference if p.strip()}
    if not predicted and not expected:
        return 1.0
    shared = len(predicted & expected)
    return 2 * shared / (len(predicted) + len(expected)) if shared else 0.0


def answer_for_scoring(result, short=False):
    """只接受完整的显式拒答前缀/全缺失状态；局部否定和No答案不转成不可答。"""
    if result.get('status') == 'failed':
        return '', 'failed'
    text = clean_answer(result.get('answer'))
    if result.get('answer_status') == 'insufficient_evidence' or re.match(
            r'^(?:Unanswerable(?:[.!。]|$)|Insufficient evidence(?:\b|[.!:])|当前证据不足(?:[，,。:：]|$))',
            text, re.I):
        return 'Unanswerable', 'declined'
    if short:
        text = re.split(r'\n\s*\n', text, maxsplit=1)[0].strip()
        text = re.sub(r'^(?:short answer|answer|结论|答案)\s*[:：]\s*', '', text, flags=re.I)
    return text, 'answered'
