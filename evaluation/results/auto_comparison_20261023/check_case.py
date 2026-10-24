"""检查这道开发题的用户症状；仅验收输出，不给运行中的模型提供答案。"""
import json
import re
import sys
from pathlib import Path


folder = Path(sys.argv[1])
result = json.loads((folder / "result.json").read_text())
answer = result["answer"]
issues = []
if result.get('answer_status') == 'insufficient_evidence' or answer.startswith('当前证据不足'):
    issues.append('本地定义已可支持比较，却仍然拒答')
if re.search(r"VGG\s*之间|RAG\s*之间|不能据此.*差异|无法据此归纳.*差异|没有对二者进行直接比较", answer):
    issues.append("把跨对象比较变成内部版本比较，或因没有直接比较论文而拒答")
question = folder / "pipeline/loop/question.json"
if question.exists():
    plan = json.loads(question.read_text())["plan"]
    for item in plan["requirements"]:
        need = item["need"].lower()
        if "difference between" in need and not ("vgg" in need and "rag" in need):
            issues.append("比较需求丢失另一对象: " + need)
attempts = result["api_summary"]["attempts"]
if attempts > 3:
    issues.append(f"本地概念比较过度升级: {attempts}次模型调用")
print(json.dumps({"pass": not issues, "issues": issues, "calls": attempts}, ensure_ascii=False, indent=2))
sys.exit(bool(issues))
