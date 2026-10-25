The paper uses theme-based textual features — Emotions, Sentiment, Bad & Sexual Cues, and Stance Cues — plus NLI (native-language-identification) features.

The theme-based features are modeled independently for each extracted theme to capture emotional, stance, and other changes in users' tweets [1]:

- **Emotions**: extracted using the NRC emotions lexicon (~14K words labeled with Plutchik's eight emotions) to detect emotional manipulation attempts such as fear spreading [9].
- **Sentiment**: positive and negative sentiment extracted from NRC [12].
- **Bad & Sexual Cues**: presence of bad slang and sexual words used to mimic the language of a US citizen, modeled with a list of such words [12].
- **Stance Cues**: user stance toward the extracted topics, modeled with a set of stance lexicons from previous works [13].

Additionally, NLI features are used to capture the trolls' writing style, consisting of a bag of stopwords, part-of-speech tags (POS), and syntactic dependency relations (DEPREL) [6].
