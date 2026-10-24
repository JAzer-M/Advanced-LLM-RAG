import argparse
import json
import re
import unicodedata
from pathlib import Path
from src.knowledge_base import load_knowledge_base

def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip().lower()

def main():
    parser = argparse.ArgumentParser(description='在当前或指定知识库版本中核对 Gold 引文。')
    parser.add_argument('--kb-version')
    args = parser.parse_args()
    project_dir = Path(__file__).resolve().parent.parent

    question_path = project_dir/"evaluation"/"questions.json"

    # 加载数据
    with open(question_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
    _, chunks, knowledge_base = load_knowledge_base(project_dir / 'data/processed', args.kb_version)
    print('Knowledge Base:', knowledge_base['version'])

    # 匹配gold evidence
    for question in questions:

        print(f"\n === {question['id']} ===")

        for evidence in question.get("gold_evidence", []):

            quote = normalize_text(evidence["quote"])

            matched_chunks = []
            for chunk in chunks:
                if (
                        chunk["source"] == evidence["source"]
                        and chunk["page"] == evidence["page"]
                ):
                    chunk_text = normalize_text(chunk["text"])

                    if quote in chunk_text:
                        matched_chunks.append(chunk["chunk_id"])

            print(f"Source: {evidence['source']}")
            print(f"Page: {evidence['page']}")
            print(f"Matched chunks IDs: {matched_chunks}")

            if not matched_chunks:
                print(f"No matches found for {evidence['source']}")

            print()

if __name__ == "__main__":
    main()
