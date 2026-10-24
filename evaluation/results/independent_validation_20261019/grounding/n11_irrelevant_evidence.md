# n11 / irrelevant_evidence

What measured P95 end-to-end latency did this project achieve with Top-10 on an M3 Mac under eight concurrent users? Give the exact milliseconds.

The provided evidence is insufficient. The passages only describe three types of negative passages (Random, BM25, Gold) and state that the best model uses gold passages from the same mini-batch plus one BM25 negative passage [1]. They contain no information about measured P95 end-to-end latency, Top-10 performance, an M3 Mac, eight concurrent users, or any millisecond figures.

## Source passages

[1] 2004.04906v3.pdf, PDF p.3
We consider three different types of negatives: (1) Random: any random passage from the corpus; (2) BM25: top passages returned by BM25 which don’t contain the answer but match most question tokens; (3) Gold: positive passages paired with other questions which appear in the training set. We will discuss the impact of different types of negative passages and training schemes in Section 5.2. Our best model uses gold passages from the same mini-batch and one BM25 negative passage.
