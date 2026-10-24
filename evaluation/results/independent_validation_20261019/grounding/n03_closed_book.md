# n03 / closed_book

How does ColBERT augment a short query, and is the same augmentation applied to document inputs?

ColBERT augments a short query by appending a special `[Q]` marker (query augmentation token) to the query’s token sequence before encoding it with BERT. This `[MASK]`/`[Q]`-style token lets the model produce an additional context-enriched embedding that helps bridge the query–document vocabulary gap. The query is also padded to a fixed length (often to N tokens) with `[MASK]` tokens in the original ColBERT formulation.

No—the same augmentation is not applied to documents. Document inputs are encoded without the `[Q]` query-augmentation token and without query-style padding; they are simply tokenized and passed through BERT (with `[D]`/document markers depending on the variant), then filtered/padded to a maximum document length. Thus query augmentation is query-specific and asymmetric between queries and documents.

## Source passages

(No source passages supplied.)
