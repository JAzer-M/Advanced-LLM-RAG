"""解析模型返回的 JSON：只去掉包住整段回复的一层 Markdown 代码块（```json … ```）。

不同模型对“只返回 JSON”的遵守程度不同（例如 glm 常把 JSON 包在代码块里）。这里只剥掉
这一层外壳，不做其他修补；剩下的内容仍须是合法 JSON，并继续经过各调用点原有的字段校验。
输入：模型回复文本。输出：json.loads 的结果；不合法时照常抛出 json.JSONDecodeError。
"""
import json
import re

_FENCE = re.compile(r'```[ \t]*(?:json)?[ \t]*\r?\n?(.*?)\r?\n?[ \t]*```', re.S | re.I)


def loads_model_json(text):
    if isinstance(text, str):
        text = text.strip()
        match = _FENCE.fullmatch(text)
        if match:
            text = match.group(1)
    return json.loads(text)
