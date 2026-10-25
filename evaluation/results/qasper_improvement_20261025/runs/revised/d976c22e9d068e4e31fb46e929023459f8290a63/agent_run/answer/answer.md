Yes. In the LSTM and gated CNN method (Section 3.1), the two paragraphs are encoded independently: "paragraphs are encoded separately, and the concatenation of the resulted encoding is going through the classifier," with each paragraph encoded by LSTM followed by a gated CNN to produce a single encoding per paragraph [1].

Note that this applies to the LSTM/gated CNN method; the BERT approach instead represents the two paragraphs as a single packed sequence, not independently [7].
