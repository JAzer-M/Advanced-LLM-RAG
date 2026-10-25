Yes, the query-bag matching model uses neural networks.

The QBM model uses an hCNN, a CNN-based matching model, which takes a query and a question from the bag, feeds them into a CNN respectively, and processes a cross-attention matrix with another CNN to get the interaction representation [4]. The model also uses TF-IDF to collect important words in a bag to form a new "question," which is modeled with the hCNN to obtain a matching representation [5]. The paper's introduction notes that researchers have adopted deep neural networks to model matching relationships in related tasks [1].
