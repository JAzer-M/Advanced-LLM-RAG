# n1 / both

In the Transformer decoder, how do the shifted target embeddings and masked self-attention prevent access to future target tokens during training?

## 原始答案

Based on the provided context, the Transformer decoder prevents access to future target tokens during training through two primary mechanisms: shifted target embeddings and masked self-attention.

**Shifted Target Embeddings**
The decoder employs shifted target embeddings, which are offset by one position relative to the input sequence. This configuration ensures that the predictions for position $i$ can depend only on the known outputs at positions less than $i$. Consequently, the model is unable to attend to future positions, effectively preventing access to tokens that have not yet been generated.

**Masked Self-Attention**
To further enforce this constraint, the decoder's self-attention mechanism is modified to prevent positions from attending to subsequent positions. This is achieved by implementing a masking scheme that sets values in the input of the softmax to $-\infty$ for illegal connections. This masking prevents the model from attending to future tokens, thereby preserving the auto-regressive property of the decoder.

**Comparison of Mechanisms**
While the shifted target embeddings rely on positional offsetting to limit dependencies, the masked self-attention relies on explicit value masking to block specific connections. Both mechanisms work in conjunction to ensure that the output at any given position is generated solely from information available at previous positions.


## 引用原文

### [1] Attention is all you need.pdf, p.3 (chunk 25)

Similar to the encoder, we employ residual connections around each of the sub-layers, followed by layer normalization. We also modify the self-attention sub-layer in the decoder stack to prevent positions from attending to subsequent positions. This masking, combined with fact that the output embeddings are offset by one position, ensures that the predictions for position i can depend only on the known outputs at positions less than i.

### [2] Attention is all you need.pdf, p.9 (chunk 81)

7 Conclusion In this work, we presented the Transformer, the ﬁrst sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention. For translation tasks, the Transformer can be trained signiﬁcantly faster than architectures based on recurrent or convolutional layers. On both WMT 2014 English-to-German and WMT 2014 English-to-French translation tasks, we achieve a new state of the art.

### [3] Attention is all you need.pdf, p.2 (chunk 20)

The Transformer follows this overall architecture using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder, shown in the left and right halves of Figure 1, respectively.

### [4] Attention is all you need.pdf, p.2 (chunk 15)

In the Transformer this is reduced to a constant number of operations, albeit at the cost of reduced effective resolution due to averaging attention-weighted positions, an effect we counteract with Multi-Head Attention as described in section 3.2. Self-attention, sometimes called intra-attention is an attention mechanism relating different positions of a single sequence in order to compute a representation of the sequence.

### [5] Attention is all you need.pdf, p.2 (chunk 17)

To the best of our knowledge, however, the Transformer is the ﬁrst transduction model relying entirely on self-attention to compute representations of its input and output without using sequence- aligned RNNs or convolution. In the following sections, we will describe the Transformer, motivate self-attention and discuss its advantages over models such as [14, 15] and [8].

### [6] Attention is all you need.pdf, p.5 (chunk 39)

• The encoder contains self-attention layers. In a self-attention layer all of the keys, values and queries come from the same place, in this case, the output of the previous layer in the encoder. Each position in the encoder can attend to all positions in the previous layer of the encoder. • Similarly, self-attention layers in the decoder allow each position in the decoder to attend to all positions in the decoder up to and including that position.

### [7] Attention is all you need.pdf, p.5 (chunk 38)

3.2.3 Applications of Attention in our Model The Transformer uses multi-head attention in three different ways: • In "encoder-decoder attention" layers, the queries come from the previous decoder layer, and the memory keys and values come from the output of the encoder. This allows every position in the decoder to attend over all positions in the input sequence. This mimics the typical encoder-decoder attention mechanisms in sequence-to-sequence models such as [31, 2, 8].

### [8] Attention is all you need.pdf, p.5 (chunk 40)

We need to prevent leftward information ﬂow in the decoder to preserve the auto-regressive property. We implement this inside of scaled dot-product attention by masking out (setting to −∞) all values in the input of the softmax which correspond to illegal connections.

### [9] Attention is all you need.pdf, p.5 (chunk 43)

3.4 Embeddings and Softmax Similarly to other sequence transduction models, we use learned embeddings to convert the input tokens and output tokens to vectors of dimension dmodel. We also use the usual learned linear transfor- mation and softmax function to convert the decoder output to predicted next-token probabilities.

### [10] Attention is all you need.pdf, p.7 (chunk 67)

5.4 Regularization We employ three types of regularization during training: Residual Dropout We apply dropout [27] to the output of each sub-layer, before it is added to the sub-layer input and normalized. In addition, we apply dropout to the sums of the embeddings and the positional encodings in both the encoder and decoder stacks.
