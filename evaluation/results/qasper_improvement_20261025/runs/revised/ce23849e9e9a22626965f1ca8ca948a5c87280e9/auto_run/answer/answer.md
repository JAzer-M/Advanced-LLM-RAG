The paper's MTL model (the proposed sifted multi-task model) uses: word embedding size 200 and position embedding size 100; in the transformer encoder, attention heads set to 6 (11) and blocks set to 2; multi-head attention dropout 0.7; minibatch size 64; initial learning rate 0.001; dropout rate 0.3; and task weight λ = 0.6 for fake news detection, with N = 2 tasks [19][9].

All hyperparameters were strictly tuned on the validation dataset, achieving best performance via a small grid search [1].
