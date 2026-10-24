关于 RAG-Sequence 的 Thorough Decoding：对某个候选假设 y，若它未出现在某文档 z 的 beam 中，则对该文档额外做一次前向计算，将生成器概率与 pη(z|x) 相乘，再跨各 beam 求和得到边际概率（[7]）。

关于 Self-RAG 的评审 token 概率评分：对每个评审 token 组 G（如 ISREL），以最理想反思 token 的生成概率在该组所有 token 概率中的占比作为该组得分 sG t（[3]）；段得分由生成概率 p(yt|x, d, y<t) 加上各评审组得分的加权线性和 S(Critique)=Σ_{G∈G} wG·sG t（G={ISREL, ISSUP, ISUSE}）构成（[3]）。该加权线性和的段得分用于段级 beam search，从而按用户偏好定制模型行为（[4]）。
