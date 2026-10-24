# n05 / closed_book

Which BERT encoders are used by the original RAG retriever and DPR, and what representation does DPR extract from each encoder?

The original RAG retriever uses DPR, which employs two BERT-base encoders: a **document encoder** (BERT-base) and a **query encoder** (BERT-base). Each encoder extracts a single **dense vector representation**: DPR takes the final hidden state corresponding to the **[CLS] token** as the fixed-dimensional embedding for an entire passage or question. Similarity between query and passage vectors is computed via dot product.

## Source passages

(No source passages supplied.)
