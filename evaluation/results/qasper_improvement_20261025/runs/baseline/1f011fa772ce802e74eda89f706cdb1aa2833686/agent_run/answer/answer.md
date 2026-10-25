The paper uses a rich set of textual features to identify IRA trolls [8], organized as follows:

- **Thematic information:** The textual features utilize thematic information, deduced in an unsupervised way; the users' textual features are modeled with respect to each theme to capture emotional, stance, and other changes in the users' tweets [1], [3].
- **NLI (Native Language Identification) features:** Aimed at detecting the writing pattern of non-native English speakers, the NLI feature set consists of a bag of stopwords, Part-of-speech tags (POS), and syntactic dependency relations (DEPREL) [4], [13], extracted using spaCy [14].
- **Stylistic features:** Following authorship attribution works, they include counts of special characters, consecutive characters and letters, URLs, hashtags, and users' mentions, plus the uppercase ratio and the tweet length [15].

The extracted themes boosted the model's performance when coupled with other surface text features, and the NLI features, which identify IRA trolls from their writing style, proved very effective [9].
