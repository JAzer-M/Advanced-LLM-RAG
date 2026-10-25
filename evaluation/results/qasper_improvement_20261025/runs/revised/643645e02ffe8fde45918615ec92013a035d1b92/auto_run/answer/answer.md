The primary corpus is the Japanese–English (Ja-En) ASPEC dataset, with a subset of 500K sentence pairs used for training; the method is also applied to the WMT English–German (En-De) dataset, using news-test2014 as a development set and news-test2015/2016 as test sets. [1][2]

The Ja-En models use subword units based on byte pair encoding, and BLEU is computed with Moses' multi-bleu.pl to match WAT evaluation; En-De BLEU is computed with mteval-v13a.pl as in WMT. [1][2]
