The MTL ("Ours") model's hyperparameters are: word embedding size 200, position embedding size 100, 6 attention heads, 2 transformer encoder blocks, multi-head attention dropout 0.7, minibatch size 64, initial learning rate 0.001, dropout rate 0.3, and task weight λ = 0.6 for fake news detection [14].

All hyperparameters were tuned on the validation dataset, with the best performance achieved via a small grid search [1].
