from bubble_popper_model import twitter_profile,twitter_links,twitter_articles
from bubble_popper_model import clean_articles,article_topics,publication_scores
from bubble_popper_model import define_bubble,burst_bubble,run_popper

from bubble_popper import app

from flask import render_template, redirect, url_for
from flask import request

import tweepy

from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
import psycopg2
import pandas as pd


with open ("bubble_popper_twitter.txt","r") as myfile:
    lines = [line.replace("\n","") for line in myfile.readlines()]
consumer_key, consumer_secret = lines[0], lines[1]
auth = tweepy.AppAuthHandler(consumer_key, consumer_secret)
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
while (not api):
    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)


with open ("bubble_popper_postgres.txt","r") as myfile:
    lines = [line.replace("\n","") for line in myfile.readlines()] 
db, us ,pw = 'bubble_popper', lines[0], lines[1]                     
engine = create_engine('postgresql://%s:%s@localhost:5432/%s'%(us,pw,db))
connstr = "dbname='%s' user='%s' host='localhost' password='%s'"%(db,us,pw)
conn = None; conn = psycopg2.connect(connstr)


@app.route('/')
@app.route('/index')
def index():
    return render_template("index.html")


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/how')
def how():
    return render_template("how.html")


@app.route('/results')
def results():
  
    twitter_user,comfort_level = '',''
    comfort_text = ''
    user_ideo,pub_ideo = '',''
    articles = []
   
    twitter_user = request.args.get('twitter_handle')    
    comfort_level = request.args.get('comfort_level')
  
    if twitter_user is None: twitter_user = ''
    elif comfort_level is None: comfort_level = ''
  
    flag = 0
    if len(twitter_user) == 0 and len(comfort_level) == 0: 
        flag = 1
    elif len(twitter_user) != 0 and len(comfort_level) == 0: 
        twitter_user = twitter_user.replace('@','')
        flag = 1
    elif len(twitter_user) == 0 and len(comfort_level) != 0:
        comfort_text = comfort_level
        flag = 1
    
    if flag == 1:
        message = 'Uh-oh, you did not enter your Twitter name or choose your comfort level. Please try again.'
        return render_template("results.html", articles=articles, twitter_user=twitter_user, comfort_text=comfort_text, user_ideo=user_ideo, pub_ideo=pub_ideo, message=message)  

    twitter_user = twitter_user.replace('@','')
    comfort_text = comfort_level
    if comfort_level == 'same, same': comfort_level = 0
    elif comfort_level == 'kinda different': comfort_level = 1
    elif comfort_level == 'way out there': comfort_level = 2
  
    recs,user_score,user_bubble,alt_bubble,message = run_popper(twitter_user,comfort_level,api,conn)

    # 0 = mostly liberal, 1 = mostly conservative, 2 = mixed liberal, 3 = mixed conservative
    if user_bubble == 0: user_ideo = 'mostly liberal'
    elif user_bubble == 1: user_ideo = 'mostly conservative'
    elif user_bubble == 2: user_ideo = 'mixed liberal'
    elif user_bubble == 3: user_ideo = 'mixed conservative'
    
    if alt_bubble == 0: pub_ideo = 'mostly liberal'
    elif alt_bubble == 1: pub_ideo = 'mostly conservative'
    elif alt_bubble == 2: pub_ideo = 'mixed liberal'
    elif alt_bubble == 3: pub_ideo = 'mixed conservative'

    if len(message) == 0:
        for i in range(len(recs)):
            articles.append(dict(publication=recs['publication'].iloc[i],title=recs['title'].iloc[i],content=recs['content'].iloc[i][0:240],url=recs['url'].iloc[i]))  
  
    return render_template("results.html", articles=articles, twitter_user=twitter_user, comfort_text=comfort_text, user_ideo=user_ideo, pub_ideo=pub_ideo, message=message)
