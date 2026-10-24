Extra evidence checking did not finish. The answer below uses only the initial evidence and keeps its existing gaps:
The context describes several different ways sentence representations are produced, but it does not give a single unified answer to "how sentence embeddings are generated."

- One approach builds sentence representations using learned embeddings based on neural networks, where the learned word embeddings form a feature space into which the examined sentence is mapped [4].
- Word vectors obtained via word embeddings are averaged within a sentence, using the same scheme as in the AVGWVEC model [7].
- In the sentiment-lexicon work, word embeddings are estimated on Wikipedia rather than Twitter corpora, because across languages Tweets can cover different events from different countries, reducing overlap [10]; these embeddings are trained with skip-gram (window size 7, 5 iterations, dimension 200) [1].
- In the cross-lingual NLG work, XNLG is a pre-trained sequence-to-sequence model based on Transformer [11]; given a sentence and its language tag, XNLG encodes the input into vector representations, and the decoder conditions on the encoding vectors and a specific language tag to generate output in the target language [6].

The context does not specify a single sentence-embedding generation method; the evidence supports the above approaches but does not establish which is the general answer.
