# <a href="www.melissaellamil.com">Bubble Popper</a>
### Breaking out of the news filter bubble

#### Using Bubble Popper

Given a Twitter handle (yourname or @YourName) and comfort level (same-same, kinda different, or way out there), the app will scrape your timeline to understand your bubble: What articles and publications do you read? The app will then recommend articles from publications you do not normally read: How far away from your bubble do you want to explore?

#### Why Bubble Popper?

Social media is a major source of news for a lot of people. However, it tends to show only content from friends and outlets with the same opinions -- the so-called filter bubble. Currently, people have to actively seek out content with different perspectives. How can these platforms recommend content outside of people's usual news feeds to help them break out of their filter bubble? With *Bubble Popper*, Twitter users can find articles about the topics they are interested in but from publications with a different ideology.

#### How It Works

*1. Defining bubbles: Article topics*

One aspect of a Twitter user's bubble is the topics of the articles they read. Therefore, the model identified 20 topics from 30,000 articles published by 30 major news outlets (shared on their Twitter feeds). Using latent Dirichlet allocation, words from the articles that tended to occur together were grouped into topics. Each article was then assigned topic probabilities based on its content.

*2. Defining bubbles: Publication audience*

Another aspect of a Twitter user's bubble is the ideology of the publications the articles are from. Therefore, the model grouped the 30,000 articles into 4 ideologies. Using k-means clustering, groups of articles were identified according to the audience profiles of their source publications: a) majority ideology of people who get their news from a given publication, and b) majority ideology of people who trust a given publication as a news source [Pew Research Center Report: Political Polarization and Media Habits]. Each article was assigned to either the mostly liberal, mixed liberal, mixed conservative, or mostly conservative clusters.

*3. Defining bubbles: Twitter user*

After the app pulls a Twitter user's shared articles, the model assigns 20 topic probabilities to the contents of each article and assigns 2 ideology scores to each article according to its source publication. The model then predicts which of the 4 ideology clusters described previously the Twitter user falls into.

*4. Bursting bubbles: Article recommendations*

After the model predicts the Twitter user's ideology cluster, it selects an alternate cluster to retrieve articles from according to the Twitter user's comfort level: same-same (similar ideology), kinda different, or way out there (opposite ideology). The model then ranks the articles in this cluster according to the highest topic similarity (measured by the cosine similarity of topic probabilities between the Twitter user and each article in the corpus). The top five articles are in turn ranked according to the highest ideology distance (measured by the Euclidean distance of publication scores between the user and each article in the corpus).
