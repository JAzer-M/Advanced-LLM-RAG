# n08 / closed_book

How do Self-RAG and CRAG decide whether retrieval or additional knowledge is needed, and what happens when retrieval is unnecessary or judged incorrect?

Self-RAG trains the LLM to emit reflection tokens—Retrieve (yes/no/continue), IsRel (relevant), IsSup (supported), and IsUse (useful)—so the model itself decides per segment whether retrieval is needed and judges retrieved passages. If retrieval is unnecessary, it skips retrieval and generates directly; irrelevant passages are ignored, and unsupported/ low-utility generations are revised or rejected via these tokens.

CRAG adds a lightweight retrieval evaluator that scores retrieved documents as Correct, Incorrect, or Ambiguous. Correct documents are refined (decompose-then-recompose) and used; Incorrect ones trigger web search or are discarded; Ambiguous ones combine both. Thus CRAG decides by evaluator confidence rather than LLM self-reflection. Exact thresholds/implementation details for either method are not specified here.

## Source passages

(No source passages supplied.)
