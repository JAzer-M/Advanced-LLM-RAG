# n03 / irrelevant_evidence

How does ColBERT augment a short query, and is the same augmentation applied to document inputs?

The provided evidence is insufficient. The passages describe SELF-RAG’s retrieval-token decoding and critic-based training, but they do not mention ColBERT, short-query augmentation, or whether any augmentation is applied to document inputs.

## Source passages

[1] 2310.11511v1.pdf, PDF p.4
Figure 1 and Algorithm 1 present an overview of SELF-RAG at inference. For every x and preceding generation y<t, the model decodes a retrieval token to evaluate the utility of retrieval. If retrieval is not required, the model predicts the next output segment, as it does in a standard LM.

[2] 2310.11511v1.pdf, PDF p.4
We train C to generate reflection tokens for evaluating retrieved passages and the quality of a given task output (Section 3.2.1). Using the critic model, we update the training corpus by inserting reflection tokens into task outputs offline. Subsequently, we train the final generator model (M) using the conventional LM objective (Section 3.2.2) to enable M to generate reflection tokens by itself without relying on the critic at inference time.
