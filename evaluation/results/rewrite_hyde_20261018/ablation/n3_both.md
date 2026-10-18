# n3 / both

How does the VGG paper distinguish scale jittering during training from multi-scale evaluation at test time?

## 原始答案

The VGG paper treats training-time scale jittering and test-time multi-scale evaluation as distinct procedures. During training, scale jittering means each training image is individually rescaled by randomly sampling S from a range [Smin, Smax], using Smin = 256 and Smax = 512 [5]. At test time, multi-scale evaluation consists of running a model over several rescaled versions of a test image (corresponding to different values of Q), followed by averaging the resulting class posteriors [6]. For models trained with fixed S, evaluation uses three test image sizes close to the training one: Q = {S − 32, S, S + 32} [6], whereas a model trained with variable S ∈ [Smin; Smax] was evaluated over Q = {Smin, 0.5(Smin + Smax), Smax} [1]. The paper reports that scale jittering at test time leads to better performance compared to evaluating the same model at a single scale [3], and that training-time scale jittering (S ∈ [256; 512]) leads to significantly better results than training on images with a fixed smallest side (S = 256 or S = 384), even though a single scale is used at test time [2].

## 引用原文

### [1] VGG.pdf, p.6 (chunk 288)

At the same time, scale jittering at training time allows the network to be applied to a wider range of scales at test time, so the model trained with variable S ∈[Smin; Smax] was evaluated over a larger range of sizes Q = {Smin, 0.5(Smin + Smax), Smax}.

### [2] VGG.pdf, p.6 (chunk 283)

The top-1 error of the shallow net was measured to be 7% higher than that of B (on a center crop), which conﬁrms that a deep net with small ﬁlters outperforms a shallow net with larger ﬁlters. Finally, scale jittering at training time (S ∈[256; 512]) leads to signiﬁcantly better results than training on images with ﬁxed smallest side (S = 256 or S = 384), even though a single scale is used at test time.

### [3] VGG.pdf, p.7 (chunk 289)

Published as a conference paper at ICLR 2015 The results, presented in Table 4, indicate that scale jittering at test time leads to better performance (as compared to evaluating the same model at a single scale, shown in Table 3). As before, the deepest conﬁgurations (D and E) perform the best, and scale jittering is better than training with a ﬁxed smallest side S. Our best single-network performance on the validation set is 24.8%/7.5% top-1/top-5 error (highlighted in bold in Table 4).

### [4] VGG.pdf, p.6 (chunk 284)

This conﬁrms that training set augmentation by scale jittering is indeed helpful for capturing multi-scale image statistics. Table 3: ConvNet performance at a single test scale. ConvNet conﬁg.

### [5] VGG.pdf, p.4 (chunk 262)

In our experiments, we evaluated models trained at two ﬁxed scales: S = 256 (which has been widely used in the prior art (Krizhevsky et al., 2012; Zeiler & Fergus, 2013; Sermanet et al., 2014)) and S = 384. Given a ConvNet conﬁguration, we ﬁrst trained the network using S = 256. To speed-up training of the S = 384 network, it was initialised with the weights pre-trained with S = 256, and we used a smaller initial learning rate of 10−3. The second approach to setting S is multi-scale training, where each training image is individually rescaled by randomly sampling S from a certain range [Smin, Smax] (we used Smin = 256 and Smax = 512).

### [6] VGG.pdf, p.6 (chunk 287)

It consists of running a model over several rescaled versions of a test image (corresponding to different values of Q), followed by averaging the resulting class posteriors. Considering that a large discrepancy between training and testing scales leads to a drop in performance, the models trained with ﬁxed S were evaluated over three test image sizes, close to the training one: Q = {S −32, S, S + 32}.

### [7] VGG.pdf, p.5 (chunk 264)

Published as a conference paper at ICLR 2015 model is trained to recognise objects over a wide range of scales. For speed reasons, we trained multi-scale models by ﬁne-tuning all layers of a single-scale model with the same conﬁguration, pre-trained with ﬁxed S = 384.

### [8] VGG.pdf, p.14 (chunk 376)

v1 Initial version. Presents the experiments carried out before the ILSVRC submission. v2 Adds post-submission ILSVRC experiments with training set augmentation using scale jittering, which improves the performance. v3 Adds generalisation experiments (Appendix B) on PASCAL VOC and Caltech image classiﬁca- tion datasets. The models used for these experiments are publicly available. v4 The paper is converted to ICLR-2015 submission format.

### [9] VGG.pdf, p.12 (chunk 354)

4.2, evaluation over multiple scales is beneﬁcial, so we extract features over several scales Q. The resulting multi-scale features can be either stacked or pooled across scales. Stacking allows a subsequent classiﬁer to learn how to optimally combine image statistics over a range of scales; this, however, comes at the cost of the increased descriptor dimensionality. We return to the discussion of this design choice in the experiments below.

### [10] VGG.pdf, p.6 (chunk 286)

4.2 MULTI-SCALE EVALUATION Having evaluated the ConvNet models at a single scale, we now assess the effect of scale jittering at test time.

### [11] VGG.pdf, p.6 (chunk 282)

The error rate of our architecture saturates when the depth reaches 19 layers, but even deeper models might be beneﬁcial for larger datasets. We also compared the net B with a shallow net with ﬁve 5 × 5 conv. layers, which was derived from B by replacing each pair of 3 × 3 conv. layers with a single 5 × 5 conv. layer (which has the same receptive ﬁeld as explained in Sect.
