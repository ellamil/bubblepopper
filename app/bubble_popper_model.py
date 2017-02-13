from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
import psycopg2

import tweepy
import newspaper

import gensim
from gensim import corpora, models
from nltk.stem import WordNetLemmatizer
from stop_words import get_stop_words

from sklearn import cluster
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances

import pandas as pd
import numpy as np

import re
from time import sleep

import pickle


def twitter_profile(screen_name,api,num_tweets=1000,num_friends=1000):
    
    tweets = []
    for tweet in tweepy.Cursor(api.user_timeline, screen_name=screen_name, count=200, include_rts=True).pages(num_tweets/200):
        tweets += tweet
    tweets = [[tweet.text,[url['expanded_url'] for url in tweet.entities['urls']]] for tweet in tweets]
    
    friends = []
    for friend in tweepy.Cursor(api.friends, screen_name=screen_name, count=200).pages(num_friends/200):
        friends += friend
    friends = [friend.screen_name for friend in friends]
    
    return tweets,friends


def twitter_links(tweets,conn):
    
    query = """SELECT * FROM pub_twitter_new"""
    pub_twitter = pd.read_sql(query,conn)
    
    url1 = pub_twitter['short_url'][pub_twitter['short_url'].notnull() 
                     & ~(pub_twitter['short_url'].isin(['http','bit.ly','ow.ly','buff.ly',
                                                         'trib.al','yhoo.it','buzzfeed.com']))].values.tolist() 
    url2 = pub_twitter['long_url'].values.tolist()
    pattern = '|'.join(map(re.escape,url1+url2))
    
    tweets = pd.DataFrame(tweets)
    tweets.columns = ['text','url']
    tweets['url'] = tweets['url'].apply(lambda x: ', '.join(x))
    
    links = tweets['url'][tweets['url'].str.contains(pattern)].values.tolist()
    links = [link.split(',')[0] for link in links]
    
    return links,tweets


def twitter_articles(links,num_articles=30,sleep_time=0):
    
    articles = []
    badlinks = []
    for i,link in enumerate(links):
        if i < num_articles:
            try:
                article = newspaper.Article(link)
                article.download()
                article.parse()
                articles.append(article)
                sleep(sleep_time)
            except:
                badlinks.append(link)
                continue
        else:
            break
        
    return articles,badlinks


def clean_articles(articles,tweets):
    
    # get article or tweet texts
    if len(articles) > 0:
        doc_set = [article.text for article in articles]
    else:
        doc_set = tweets['text'].values.tolist()      
        
    # remove backslashes
    doc_set = [doc.replace("\n"," ") for doc in doc_set]
    doc_set = [doc.replace("\'","") for doc in doc_set]

    # lowercases and tokenizes documents
    doc_set = [gensim.utils.simple_preprocess(doc) for doc in doc_set]

    # stems / lemmatizes documents
    wordnet_lemmatizer = WordNetLemmatizer()
    doc_set = [[wordnet_lemmatizer.lemmatize(word) for word in doc] for doc in doc_set]
    doc_set = [[wordnet_lemmatizer.lemmatize(word,pos='v') for word in doc] for doc in doc_set]

    # remove stop words and misc words    
    en_stop = get_stop_words('en')
    letters = ["a","b","c","d","e","f","g","h","i","j","k","l","m","n","o","p","q","r","s","t","u","v","w","x","y","z"]
    other = ["wa","ha","one","two","id","re","http","com","mr","image","photo","caption","don","sen","pic","co",
         "source","watch","play","duration","video","momentjs","getty","images","newsletter"]
    doc_set = [[word for word in doc if not word in (en_stop+letters+other)] for doc in doc_set]
    
    return doc_set


def article_topics(documents,ldafile='ldamodels_bow_20.lda',num_topics=20):
    
    ldamodel = gensim.models.ldamodel.LdaModel.load(ldafile)

    doc_probs = []
    for doc in documents:
        doc_dict = gensim.corpora.Dictionary([doc])
        doc_corp = doc_dict.doc2bow(doc)
        doc_probs.append(ldamodel[doc_corp])

    doc_data = pd.DataFrame()
    for i in range(0,num_topics):
        doc_data['topic'+str(i)] = 0.0

    for i,doc in enumerate(doc_probs):
        for probs in doc:
            doc_data.set_value(i,'topic'+str(probs[0]),probs[1])
    doc_data = doc_data.fillna(0.0)
    
    doc_data = np.array(doc_data.mean(axis=0))

    return doc_data


def publication_scores(links,badlinks,friends,conn,num_articles=30,dimensions=['source','trust']):
      
    query = """SELECT * FROM pub_scores"""
    pub_scores = pd.read_sql(query,conn)

    query = """SELECT * FROM pub_twitter_new"""
    pub_twitter = pd.read_sql(query,conn)
        
    url1 = pub_twitter[['handle','short_url']][pub_twitter['short_url'].notnull() 
                 & ~(pub_twitter['short_url'].isin(['http','bit.ly','ow.ly','buff.ly',
                                                     'trib.al','yhoo.it','buzzfeed.com']))].values.tolist() 
    url2 = pub_twitter[['handle','long_url']].values.tolist()

    urlList = pd.DataFrame(url1+url2)
    urlList.columns = ['handle','url']
    
    url_boolean = [[url in link for url in urlList.url.values.tolist()] for link in links[0:num_articles] if link not in badlinks]
    url_index = [[i for i,x in enumerate(url) if x] for url in url_boolean]
    
    url_shared = []
    for i in url_index:
        try:
            url_shared.append(urlList.handle.values.tolist()[i[0]])
        except IndexError:
            continue
    
    if len(links) == 0 or len(url_shared) == 0:
        pub_matches = [pub for pub in pub_scores.twitter if pub in friends]
        if len(pub_matches) == 0:
            url_score = np.array([3,3])
        else:        
            url_score = np.array([pub_scores[dimensions].loc[pub_scores.twitter.isin(pub_matches)].mean(axis=0)])
        return url_score

    url_score = [pub_scores[dimensions][pub_scores['twitter']==handle].values.tolist()[0] for handle in url_shared]
    url_score = pd.DataFrame(url_score)
    url_score.columns = dimensions
    
    url_score = np.array(url_score.mean(axis=0))
    
    return url_score


def define_bubble(pub_data,doc_data,kmeansfile='pub_kmeans_clean_cluster4.pkl'):

    user_score = np.concatenate([pub_data,doc_data],axis=0)
    
    kmeans_model,kmeans,kmeans_clusters,kmeans_distances = pickle.load(open(kmeansfile,'rb'))   
    user_bubble = kmeans.predict(user_score.reshape(1,-1))
    
    # 0 = liberal, 1 = conservative, 2 = mixed, 3 = wsj    
    return user_score,user_bubble


def burst_bubble(user_score,user_bubble,comfort_level,conn,kmeansfile='pub_kmeans_clean_cluster4.pkl',dimensions=['source','trust'],num_topics=20):
    
    query = """SELECT * FROM article_data"""
    article_data = pd.read_sql(query,conn)
    
    topic_list = ['topic'+str(i) for i in range(0,num_topics)]
    topic_data = article_data[topic_list]
    pub_data = article_data[dimensions]

    # 0 = liberal, 1 = conservative, 2 = mixed, 3 = wsj
    if user_bubble == 0:
        if comfort_level == 0: alt_bubble = 0
        elif comfort_level == 1: alt_bubble = 3
        elif comfort_level == 2: alt_bubble = 1
    elif user_bubble == 1:
        if comfort_level == 0: alt_bubble = 1
        elif comfort_level == 1: alt_bubble = 2
        elif comfort_level == 2: alt_bubble = 0
    elif user_bubble == 2:
        if comfort_level == 0: alt_bubble = 2
        elif comfort_level == 1: alt_bubble = 3
        elif comfort_level == 2: alt_bubble = 1
    elif user_bubble == 3:
        if comfort_level == 0: alt_bubble = 3
        elif comfort_level == 1: alt_bubble = 2
        elif comfort_level == 2: alt_bubble = 0    
    
    kmeans_model,kmeans,kmeans_clusters,kmeans_distances = pickle.load(open(kmeansfile,'rb'))    
    topic_data = topic_data.iloc[np.where(kmeans_clusters == alt_bubble)]
    pub_data = pub_data.iloc[np.where(kmeans_clusters == alt_bubble)]
    
    topic_user = user_score[len(dimensions):]
    topic_user = np.tile(topic_user,(len(topic_data),1))
    pub_user = user_score[:len(dimensions)]
    pub_user = np.tile(pub_user,(len(topic_data),1))
    
    topic_dist = cosine_similarity(topic_user,topic_data.values)[0,:]
    pub_dist = euclidean_distances(pub_user,pub_data.values)[0,:]

    query = """SELECT * FROM pub_articles_clean"""
    article_content = pd.read_sql(query,conn)
    
    recs = pd.DataFrame()
    recs['topic_dist'] = topic_dist
    recs['pub_dist'] = pub_dist
    recs['publication'] = article_data['publication'].iloc[np.where(kmeans_clusters == alt_bubble)].values
    recs['title'] = article_content['title'].iloc[np.where(kmeans_clusters == alt_bubble)].values
    recs['content'] = article_content['content'].iloc[np.where(kmeans_clusters == alt_bubble)].values
    recs['url'] = article_content['url'].iloc[np.where(kmeans_clusters == alt_bubble)].values
    
    recs.sort_values('topic_dist',ascending=False,inplace=True)
    recs = recs.head()
    recs.sort_values('pub_dist',ascending=True,inplace=True)
    
    return recs, alt_bubble


def run_popper(twitter_name,comfort_level,api,conn):

    recs = None
    user_score = None
    user_bubble = None
    alt_bubble = None
    message = ''
    
    try:
        tweets,friends = twitter_profile(twitter_name,api)
    except tweepy.error.TweepError:
        message = 'Uh-oh, this user does not exist or their timeline is empty. Please try again.'
        return recs,user_score,user_bubble,alt_bubble,message
    
    links,tweets = twitter_links(tweets,conn)
    articles,badlinks = twitter_articles(links)
    doc_set = clean_articles(articles,tweets)
    doc_data = article_topics(doc_set)
    pub_data = publication_scores(links,badlinks,friends,conn)    
    user_score,user_bubble = define_bubble(pub_data.squeeze(),doc_data)
    recs, alt_bubble = burst_bubble(user_score,user_bubble,comfort_level,conn)
   
    return recs,user_score,user_bubble,alt_bubble,message
