# n05: metadata-only replay

The provided evidence is insufficient.

The passages identify that DPR uses BERTBASE document and query encoders [2], and that DPR's question and passage encoders are independent BERT base uncased networks taking the [CLS] token representation with d = 768 [1]. However, they do not state which BERT encoders the original RAG retriever uses beyond saying its retrieval component is based on DPR [2], nor do they fully specify what representation DPR extracts from each encoder—only that d(z) and q(x) are dense representations produced by the document and query encoders [2], with [1] describing the [CLS] token for the question and passage encoders.
