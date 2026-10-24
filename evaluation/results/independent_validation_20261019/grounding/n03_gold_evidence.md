# n03 / gold_evidence

How does ColBERT augment a short query, and is the same augmentation applied to document inputs?

ColBERT pads a query with fewer than a predefined number Nq tokens using BERT’s special [mask] tokens up to length Nq; otherwise it truncates the query to the first Nq tokens [1]. This padding with masked tokens is called query augmentation and allows BERT to produce query-based embeddings at the positions corresponding to these masks [1]. The same augmentation is not applied to documents: unlike queries, ColBERT does not append [mask] tokens to documents [2].

## Source passages

[1] 2004.12832v2.pdf, PDF p.4
If the query has fewer than a pre-deﬁned number of tokens Nq, we pad it with BERT’s special [mask] tokens up to length Nq (otherwise, we truncate it to the ﬁrst Nq tokens). Tis padded sequence of input tokens is then passed into BERT’s deep transformer architecture, which computes a contextualized representation of each token. We denote the padding with masked tokens as query augmen- tation, a step that allows BERT to produce query-based embeddings at the positions corresponding to these masks.

[2] 2004.12832v2.pdf, PDF p.4
Document Encoder. Our document encoder has a very similar architecture. We ﬁrst segment a document d into its constituent to- kens d1d2...dm, to which we prepend BERT’s start token [CLS] fol- lowed by our special token [D] that indicates a document sequence. Unlike queries, we do not append [mask] tokens to documents.
