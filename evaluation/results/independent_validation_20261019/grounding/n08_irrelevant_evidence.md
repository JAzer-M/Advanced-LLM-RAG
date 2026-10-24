# n08 / irrelevant_evidence

How do Self-RAG and CRAG decide whether retrieval or additional knowledge is needed, and what happens when retrieval is unnecessary or judged incorrect?

The provided evidence is insufficient. The passages describe query padding/truncation with [mask] tokens and query augmentation [1], document encoding with [CLS] and [D] tokens and no [mask] appending [2], and an offline batched indexing procedure [3]. They do not mention Self-RAG or CRAG, nor how either decides whether retrieval or additional knowledge is needed, nor what happens when retrieval is unnecessary or judged incorrect.

## Source passages

[1] 2004.12832v2.pdf, PDF p.4
If the query has fewer than a pre-deﬁned number of tokens Nq, we pad it with BERT’s special [mask] tokens up to length Nq (otherwise, we truncate it to the ﬁrst Nq tokens). Tis padded sequence of input tokens is then passed into BERT’s deep transformer architecture, which computes a contextualized representation of each token. We denote the padding with masked tokens as query augmen- tation, a step that allows BERT to produce query-based embeddings at the positions corresponding to these masks.

[2] 2004.12832v2.pdf, PDF p.4
Document Encoder. Our document encoder has a very similar architecture. We ﬁrst segment a document d into its constituent to- kens d1d2...dm, to which we prepend BERT’s start token [CLS] fol- lowed by our special token [D] that indicates a document sequence. Unlike queries, we do not append [mask] tokens to documents.

[3] 2004.12832v2.pdf, PDF p.5
At a high level, our indexing procedure is straight-forward: we proceed over the documents in the collection in batches, running our document encoder fD on each batch and storing the output embeddings per document. Although indexing a set of documents is an oﬄine process, we incorporate a few simple optimizations for enhancing the throughput of indexing. As we show in §4.5, these optimizations can considerably reduce the oﬄine cost of indexing.
