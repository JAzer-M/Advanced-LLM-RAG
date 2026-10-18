# n2 / base

How do overlapping pooling windows differ from non-overlapping pooling in the DCNN paper, and what effects did the authors report?

## 原始答案

In the DCNN paper, a pooling layer is described as a grid of pooling units spaced s pixels apart, each summarizing a z × z neighborhood centered on the unit; setting s = z gives traditional non-overlapping local pooling, while setting s < z gives overlapping pooling [2][5]. The network uses overlapping pooling with s = 2 and z = 3, which reduces top-1 and top-5 error rates by 0.4% and 0.3%, respectively, compared with the non-overlapping scheme s = 2, z = 2 that produces output of equivalent dimensions [1]. The authors also report that models with overlapping pooling are generally observed during training to find it slightly more difficult to overfit [1].

## 引用原文

### [1] DCNN.pdf, p.4 (chunk 153)

This is what we use throughout our network, with s = 2 and z = 3. This scheme reduces the top-1 and top-5 error rates by 0.4% and 0.3%, respectively, as compared with the non overlapping scheme s = 2, z = 2, which produces output of equivalent dimensions. We generally observe during training that models with overlapping pooling find it slightly more dif- ficult to overfit.

### [2] DCNN.pdf, p.3 (chunk 147)

4.4. Overlapping pooling Pooling layers in CNNs summarize the outputs of neighbor- ing groups of neurons in the same kernel map. Traditionally, the neighborhoods summarized by adjacent pooling units do not overlap (e.g., Refs.5, 13, 20). To be more precise, a pooling layer can be thought of as consisting of a grid of pooling units spaced s pixels apart, each summarizing a neighborhood of size z × z centered at the location of the pooling unit.

### [3] DCNN.pdf, p.3 (chunk 136)

The magnitude of the effect demonstrated here varies with network architecture, but networks with ReLUs consistently learn several times faster than equivalents with saturating neurons. 0.75 Training error rate 0.5 0.25 0 0 5 10 15 20 25 30 35 Epochs average pooling on the Caltech-101 dataset. However, on this dataset the primary concern is preventing overfitting, so the effect they are observing is different from the accelerated ability to fit the training set which we report when using ReLUs.

### [4] DCNN.pdf, p.6 (chunk 186)

Since there is no established test set, our split necessarily differs from the splits used by previous authors, but this does not affect the results appreciably. Our top-1 and top-5 error rates on this dataset are 67.4% and 40.9%, attained by the net described above but with an additional, sixth convolutional layer over the last pooling layer. The best published results on this dataset are 78.1% and 60.9%.23

### [5] DCNN.pdf, p.3 (chunk 148)

If we set s = z, we obtain traditional local pooling as commonly employed in CNNs. If we set s < z, we obtain overlapping b The one-GPU net actually has the same number of kernels as the two-GPU net in the final convolutional layer. This is because most of the net’s param- eters are in the first fully connected layer, which takes the last convolutional layer as input.

### [6] DCNN.pdf, p.4 (chunk 152)

The network’s input is 150,528-dimensional, and the number of neurons in the network’s remaining layers is given by 290,400–186,624– 64,896–64,896–43,264–4096–4096–1000. 3 5 3 5 3 11 48 11 128 27 55 13 3 5 3 224 5 13 27 3 11 3 55 11 Max Max 224 Stride 128 pooling pooling of 4 3 48 pooling.

### [7] DCNN.pdf, p.1 (chunk 104)

1. PROLOGUE Four years ago, a paper by Yann LeCun and his collaborators was rejected by the leading computer vision conference on the grounds that it used neural networks and therefore pro- vided no insight into how to design a vision system. At the time, most computer vision researchers believed that a vision system needed to be carefully hand-designed using a detailed understanding of the nature of the task.

### [8] DCNN.pdf, p.6 (chunk 183)

error rates for all the models that we tried. In the remainder of this paragraph, we use validation and test error rates inter- changeably because in our experience they do not differ by more than 0.1% (see Table 2). The CNN described in this paper achieves a top-5 error rate of 18.2%. Averaging the pre- dictions of five similar CNNs gives an error rate of 16.4%.

### [9] DCNN.pdf, p.4 (chunk 159)

The third convolutional layer has 384 kernels of size 3 × 3 × 256 connected to the (normalized, pooled) outputs 3 3 3 3 dense 2048 2048 192 192 128 13 13 3 3 3 dense dense 13 13 3 1000 Max 192 192 128 2048 2048 pooling of the second convolutional layer. The fourth convolu- tional layer has 384 kernels of size 3 × 3 × 192, and the fifth convolutional layer has 256 kernels of size 3 × 3 × 192. The fully connected layers have 4096 neurons each.

### [10] DCNN.pdf, p.1 (chunk 102)

On the test data, we achieved top-1 and top-5 error rates of 37.5% and 17.0%, respectively, which is considerably better than the previous state-of-the-art. The neural network, which has 60 million parameters and 650,000 neurons, con- sists of five convolutional layers, some of which are followed by max-pooling layers, and three fully connected layers with a final 1000-way softmax.

### [11] DCNN.pdf, p.4 (chunk 151)

Figure 2. An illustration of the architecture of our CNN, explicitly showing the delineation of responsibilities between the two GPUs. One GPU runs the layer-parts at the top of the figure while the other runs the layer-parts at the bottom. The GPUs communicate only at certain layers.

### [12] DCNN.pdf, p.4 (chunk 155)

Our net- work maximizes the multinomial logistic regression objective, which is equivalent to maximizing the average across training cases of the log-probability of the correct label under the prediction distribution.
