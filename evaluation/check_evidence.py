import json
import re
import unicodedata
from pathlib import Path

def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip().lower()

project_dir = Path(__file__).resolve().parent.parent

question_path = project_dir/"evaluation"/"questions.json"
chunks_path = project_dir/"data"/"processed"/"chunks.json"

# 加载数据
with open(question_path, "r", encoding="utf-8") as f:
    questions = json.load(f)
with open(chunks_path, "r", encoding="utf-8") as f:
    chunks = json.load(f)

# 匹配gold evidence
for question in questions:

    print(f"\n === {question['id']} ===")

    for evidence in question.get("gold_evidence", []):

        quote = normalize_text(evidence["quote"])

        matched_chunks = []
        for i, chunk in enumerate(chunks):
            if(
                chunk["source"] == evidence["source"]
                and chunk["page"] == evidence["page"]
            ):
                chunk_text = normalize_text(chunk["text"])

                if quote in chunk_text:
                    matched_chunks.append(i)

        print(f"Source: {evidence['source']}")
        print(f"Page: {evidence['page']}")
        print(f"Matched chunks IDs: {matched_chunks}")

        if not matched_chunks:
            print(f"No matches found for {evidence['source']}")

        print()