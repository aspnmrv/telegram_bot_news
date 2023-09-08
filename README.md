# Telegram Bot News (Bernard)

Bernard is a telegram bot that helps filter and summarize news from selected channels on selected topics.

## Description

The bot receives a list of channels from the user, specifies the user’s interests (science / politics / sports, etc.) and filters news from selected channels in two modes:

- reposts: classifies posts according to selected topics from news channels and makes reposts for the user
- summarization: classifies posts according to selected topics from news channels and summarizes posts for the user

You can start using it [here](https://t.me/news_filtering_bot)

## About the code:

This project is a modular bot, made using Python 3 and the following:

- [Telethon Library (Client API & Bot API)](https://github.com/LonamiWebs/Telethon)
- ML models for classification and summarization, located in a [separate repository](https://github.com/artemryzhkov/news_predictions) and on a separate server

## Bot features:

The purpose of this bot is to provide Telegram users with an easy way to filter news, get short excerpts on topics of interest to the user from different Telegram channels in one place.

The bot can work with any news channels in Russian (since the classification model is trained on a sample of news in Russian). You can contribute and add your own languages if you want :)

Some more features of the bot:

- It is possible to add keywords if you do not want to see news containing the selected keywords
- Ability to view statistics with the amount of time saved reading news and popular topics and keywords that users choose
- Ability to change selected channels/interests and keywords

## Usage

- run (/start)
- add channels you want to follow
- choose your interests
- optionally add keywords to exclude
- start news filtering in repost or summarization mode

## Setting up the bot

Before all, clone this repository.

You need to add a config with filled parameters for the telegram api:

```
BOT_TOKEN: ""
APP_ID: 
API_HASH: ""
PASSWORD: ""
LOGIN: ""
BOT_API: ""
```

You also need to fill in the parameters for accessing the API model 
(currently there is a classification model and a configured summarization model on a separate server and in a [separate repository](https://github.com/artemryzhkov/news_predictions)):

```
MODEL_PREDICT_PATH: "http://localhost:5000/predict"
MODEL_SUMMARY_PATH: "http://localhost:5000/summary"
```

### Using Docker

Simply, run the following command:
```
docker-compose up --build -d
```

### Database

The bot depends on sqlite database and Postgres database hosted in AWS RDS.

For the bot to work, you need to connect to the Postgres database by filling out the telegram_bot_news/app/db/config.json:

```
{"dbname": "", "user": "", "password": "", "host": ""}
```

Database structure:




### Without Docker [NOT RECOMMENDED]

Run main file telegram_bot_news/app/main.py => python3 main.py || nohup python3 main.py &

## Authors

Contributors names and contact info

ex. Artem Ponomarev
ex. [@aspnmrv](https://t.me/aspnmrv)
