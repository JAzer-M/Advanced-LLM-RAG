import pymupdf
from pathlib import Path

def load_pdf(pdf_path):

    documents = []

    with pymupdf.open(pdf_path) as pdf:

        for page_number, page in enumerate(pdf, start=1):

            text = page.get_text()

            document = {
                "text": text,
                "page": page_number,
                "source": Path(pdf_path).name,
            }

            documents.append(document)

    return documents

def load_pdfs(folder_path):
    all_documents = []

    pdf_files = sorted(Path(folder_path).glob("*.pdf"))

    for pdf_path in pdf_files:

        documents = load_pdf(pdf_path)

        all_documents.extend(documents)

    return all_documents


if __name__ == "__main__":
    folder_path = Path(__file__).resolve().parent.parent / "data" / "raw"

    documents = load_pdfs(folder_path)

    print("总页数:", len(documents))

    for document in documents:
        print(document["source"], "Page", document["page"])