"""回答语言：默认跟随提问语言；问题里明确要求某种语言时按要求。

输入：原始问题文本。输出：'zh' 或 'en'。只用于程序插入回答的固定提示文字（如“补查未完成”）；
回答正文的语言由提示词里的 LANGUAGE_RULE 要求模型遵守，规则相同。
含两个及以上汉字视为中文提问；其他语言的提问，固定提示文字用英文。
"""
import re

LANGUAGE_RULE = ("Respond in the same language as the user's question. If the question explicitly "
                 "asks for a particular language, use that language instead. Keep technical names "
                 "in their original form.")

_CJK = re.compile(r'[㐀-䶿一-鿿]')
_ASK_EN = re.compile(r'(?:用|以|使用|请用|改用)\s*(?:英文|英语)|(?:英文|英语)(?:回答|作答|回复)'
                     r'|\b(?:answer|respond|reply|write)\b[^.?!\n]{0,24}\bin English\b', re.I)
_ASK_ZH = re.compile(r'(?:用|以|使用|请用|改用)\s*(?:中文|汉语|简体中文)|(?:中文|汉语)(?:回答|作答|回复)'
                     r'|\b(?:answer|respond|reply|write)\b[^.?!\n]{0,24}\bin (?:Chinese|Mandarin)\b', re.I)


def answer_language(question):
    text = question if isinstance(question, str) else ''
    if _ASK_EN.search(text):
        return 'en'
    if _ASK_ZH.search(text):
        return 'zh'
    return 'zh' if len(_CJK.findall(text)) >= 2 else 'en'


def localized(question, zh, en):
    """按回答语言选择程序插入的固定文字。"""
    return zh if answer_language(question) == 'zh' else en
