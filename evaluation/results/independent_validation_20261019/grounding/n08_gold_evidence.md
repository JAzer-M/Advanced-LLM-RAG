# n08 / gold_evidence

How do Self-RAG and CRAG decide whether retrieval or additional knowledge is needed, and what happens when retrieval is unnecessary or judged incorrect?

SELF-RAG decodes a retrieval token to evaluate retrieval utility; if retrieval is not required, it predicts the next output segment as a standard LM [1]. In the other system, the relevance score is quantified into three confidence degrees—Correct, Incorrect, Ambiguous—triggering corresponding actions [2]. If Correct is triggered, retrieved documents are refined into more precise knowledge strips via knowledge decomposition, filter, and recomposition [2]. If Incorrect is triggered, retrieved documents are discarded [2]. The provided evidence is insufficient regarding what exactly happens in SELF-RAG when retrieval is judged incorrect, and it does not name “CRAG” or describe a retrieval-necessity decision procedure for that system beyond the Correct/Incorrect/Ambiguous actions [1][2][3].

## Source passages

[1] 2310.11511v1.pdf, PDF p.4
Figure 1 and Algorithm 1 present an overview of SELF-RAG at inference. For every x and preceding generation y<t, the model decodes a retrieval token to evaluate the utility of retrieval. If retrieval is not required, the model predicts the next output segment, as it does in a standard LM.

[2] 2401.15884v3.pdf, PDF p.3
The relevance score is quantified into a total of three confidence degrees and then triggered the corresponding actions: {Correct, Incorrect, Ambiguous} (Section 4.3). If the action Correct is triggered, the retrieved documents will be re- fined into more precise knowledge strips. This refinement operation involves knowledge decom- position, filter, and recomposition (Section 4.4). If the action Incorrect is triggered, the retrieved documents will be discarded.

[3] 2401.15884v3.pdf, PDF p.3
Instead, web searches are resorted to and regarded as complementary knowledge sources for corrections (Section 4.5). Eventually, when it cannot confidently make a correct or incorrect judgment, a soft and balanced action Ambiguous which combines both of them is triggered. After optimizing the retrieval results, an arbitrary generative model can be adopted.
