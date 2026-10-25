Yes, the model is compared to baselines.

The paper's QBM model is compared against baselines including Q-Q Mean, Q-Q Max, and Bag-con, and it performs best among them [1]. The baselines were designed from two aspects: a Q-Q matching based baseline (with instances Q-Q Max and Q-Q Mean, using max or mean matching probability of query-question pairs) [13] and a query-bag matching based baseline (Bag-con, which concatenates the questions in the bag and applies hCNN) [7][5]. Experiments on AliMe and Quora datasets show gains of 0.05 and 0.03 R10@1 over the strongest baseline [4].
