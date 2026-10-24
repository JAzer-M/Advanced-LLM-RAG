# n05 / irrelevant_evidence

Which BERT encoders are used by the original RAG retriever and DPR, and what representation does DPR extract from each encoder?

The provided evidence is insufficient. The passages mention a lightweight retrieval evaluator and confidence degrees triggering Correct, Incorrect, or Ambiguous actions [1][2], but they do not identify which BERT encoders the original RAG retriever or DPR use, nor what representation DPR extracts from each encoder.

## Source passages

[1] 2401.15884v3.pdf, PDF p.1
Specifically, a lightweight retrieval evaluator is designed to assess the overall quality of retrieved documents for a query, returning a confidence degree based on which different knowledge retrieval ac- tions can be triggered. Since retrieval from static and limited corpora can only return sub- optimal documents, large-scale web searches are utilized as an extension for augmenting the retrieval results.

[2] 2401.15884v3.pdf, PDF p.2
confidence degree is quantified based on which different knowledge retrieval actions of {Correct, Incorrect, Ambiguous} can be triggered. For the latter two actions, large-scale web searches (Piktus et al., 2021; Komeili et al., 2022) are integrated as a strategic extension, since retrieval from static and limited corpora can only return sub-optimal documents in terms of scope and diversity.
