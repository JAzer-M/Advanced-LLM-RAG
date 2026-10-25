They determine this via two experiments: varying layer depth and comparing convergence speed, both showing the encoder's task is harder.

First, they vary the number of layers for the encoder and decoder respectively; adding more layers to the encoder achieves larger improvements than to the decoder, and deeper components with more gains indicate a task needing more representation capability, which is harder to learn [2][9].

Second, they compare convergence speed by fixing the parameters of a well-trained decoder (encoder) and just updating the parameters of the encoder (decoder), reasoning that a component needing more training time handles a more difficult task; measuring BLEU scores along the training process on all four datasets shows the decoder converges faster than the encoder [2][7][10]. Together these results suggest the decoder handles an easier task than the encoder in NMT [2][8].
