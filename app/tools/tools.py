import sys
import os
import asyncio

sys.path.append(os.path.dirname(__file__))
sys.path.insert(1, os.path.realpath(os.path.pardir))

import pickle
import os
import requests
import config
import tempfile
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from datetime import datetime
from telethon.tl.custom import Button
from app.db.db_tools import _get_current_user_step
from app.globals import TOPICS, EMOJI_TOPICS
from pathlib import Path
from typing import List
from tempfile import NamedTemporaryFile
from app.db.db import get_stat_topics_db, get_stat_keywords_db, update_data_topics_db, get_user_channels_db, \
    get_user_topics_db, is_user_exist_db
from langdetect import detect, detect_langs

PATH = Path(__file__).parent.resolve() / "data"


model_predict_path = config.model_predict_path
model_summary_path = config.model_summary_path


async def read_data(filename):
    """"""
    with open("/data/" + filename, "rb") as f:
        data = pickle.load(f)
    return data


async def union_dicts(dicts):
    """"""
    values = list()
    result = dict()

    for key in dicts[0].keys():
        for d in dicts:
            values += [val for val in d[key]]
        result[key] = values
        values = list()

    return result


async def is_expected_steps(user_id: int, expected_steps: list) -> bool:
    """Checking if a user exists in certain steps"""
    current_step = await _get_current_user_step(user_id)

    if current_step in expected_steps:
        return True
    else:
        return False


async def get_keyboard(text_keys: list) -> list:
    """Returns a keyboard object with the given values"""
    keyboard = list()
    for key in range(len(text_keys)):
        keyboard.append([Button.text(text_keys[key], resize=True)])
    return keyboard


async def match_topics_name(topics: list) -> list:
    """Topic name matching"""
    match_topics = list()
    for topic in topics:
        match_topics.append(TOPICS[topic])
    return match_topics


async def unmatch_topic_name(topic: str) -> str:
    """Topic Name Reverse Matching"""
    unmatch = {v: k for k, v in TOPICS.items()}
    return unmatch[topic]


async def remove_file(filename: str) -> None:
    """"""
    os.remove(PATH / filename)
    return


async def get_estimate_markup(data) -> list:
    """Formation of buttons for evaluating the result"""
    markup = [
        [
            Button.inline(text="👍", data=str(data) + "-" + "1"),
            Button.inline(text="👎", data=str(data) + "-" + "0")
        ]
    ]

    return markup


async def model_predict(data: List[str]):
    """Request and response to a text classification model"""
    try:
        header = {
            "content-type": "application/json",
            "Connection": "keep-alive",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
        }
        result = requests.post(model_predict_path, json={"news": data}, headers=header).json()
        await asyncio.sleep(1)
        return result
    except Exception as e:
        return f"The server is not responding\n{e}"


async def get_model_summary(data: str):
    """Request and response to a text summarization model"""
    try:
        header = {
            "content-type": "application/json; charset=utf-8",
            "Connection": "keep-alive"
        }
        result = requests.post(model_summary_path, json={"text": data}, headers=header).text
        await asyncio.sleep(1)
        return result
    except Exception as e:
        return f"The server is not responding\n{e}"


async def get_bar_plot(df: pd.DataFrame, x: str, y: str, xlabel: str, ylabel: str, title: str):
    """Building a bar graph for statistics"""
    sns.set_context("paper")

    plt.figure(figsize=(12, 10), dpi=150, frameon=False)

    sns.barplot(x=x, y=y, data=df, palette="magma")
    plt.xlabel(xlabel, size=20)
    plt.ylabel(ylabel, size=30)
    plt.title(title, size=40)
    plt.xticks(rotation=15, size=12)
    plt.yticks([])
    plt.box(False)
    file = NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(file.name)
    plt.clf()
    plt.close()

    return file


async def get_stat_interests():
    """Formation of a graph with statistics on selected topics"""
    data = await get_stat_topics_db()
    df = pd.DataFrame(data, columns=["user_id", "topic"])
    if df.shape[0] == 0:
        return ""
    else:
        remove_list = ["science_technology", "sports", "society", "science_technology", "other", "economy"]
        df = df[~df["topic"].isin(remove_list)]
        df = df.groupby(["topic"])["user_id"].count().reset_index()
        df["topic"] = await match_topics_name(list(df.topic))
        file = await get_bar_plot(df, "topic", "user_id", "", "", "Top Interests")

    return file


async def get_stat_keywords():
    """Formation of a graph with statistics on selected keywords"""
    data = await get_stat_keywords_db()
    df = pd.DataFrame(data, columns=["keyword", "users"])

    if df.shape[0] == 0:
        return ""
    else:
        file = await get_bar_plot(df, "keyword", "users", "", "", "Top Keywords")

    return file


async def send_user_main_stat(event, filter_stat):
    """Formation of text for sending statistics"""

    saved_time_topics = round(10 * filter_stat[0][0] // 60, 0)
    saved_time_keywords = round(10 * filter_stat[0][1] // 60, 0)

    if saved_time_topics > 0:
        text_filter_topics = f"💜 Столько времени вы сэкономили, " \
                             f"благодаря фильтрации постов " \
                             f"по интересам за последний месяц: **{saved_time_topics} минут**"
        await event.client.send_message(event.chat_id, text_filter_topics,
                                        buttons=Button.clear(), parse_mode="Markdown")
    if saved_time_keywords > 0:
        text_filter_keywords = f"💜 💜 А столько времени вы сэкономили, благодаря фильтрации постов по " \
                               f"ключевым словам за последний месяц: **{saved_time_keywords} минут**"
        await event.client.send_message(event.chat_id, text_filter_keywords, buttons=Button.clear(),
                                        parse_mode="Markdown")
    return


async def send_user_file_stat(event, file, text):
    """"""
    if file:
        await event.client.send_file(event.chat_id, file.name,
                                     caption=text, silent=True)

    return


async def get_choose_topics(user_cur_states: list, user_cur_topics: list) -> list:
    """Returns the selected topics and their status in formatted form"""

    chooses_topic = list()

    for state, topic in zip(user_cur_states, user_cur_topics):
        if state != "":
            chooses_topic.append(topic)

        return chooses_topic


async def get_emoji_topics(topic_name: str) -> str:
    """"""
    return EMOJI_TOPICS[topic_name] + f" {topic_name}"


async def is_ru_language(posts: list) -> bool:
    """Returns the presence flag of the ru language"""
    result = []
    for text in posts:
        result.append(str(str(detect_langs(text)[0]).split(":")[0]) == "ru")
    return all(result)


async def get_code_fill_form(user_id):
    """Returns a specific user data availability code"""

    user_channels = await get_user_channels_db(user_id)
    user_topics = await get_user_topics_db(user_id)
    user_exist = await is_user_exist_db(user_id)
    if not user_exist:
        return -1
    elif not user_channels:
        return 1
    elif not user_topics:
        return 2
    else:
        return 0


async def add_link_to_message(text: str, channel_name: str, post_id: int) -> str:
    """Add link to summarization text"""

    text_with_link = text.split(" ")
    link = f"https://t.me/{channel_name}/{post_id}"
    text_with_link[0] = f"[{text_with_link[0]}"
    text_with_link[1] = f"{text_with_link[1]}]({link})"

    return " ".join(text_with_link)


async def check_contains_url(text: str) -> bool:
    """"""
    if "http" in text or "https" in text or "://" in text:
        return True
    else:
        return False


async def get_diff_between_ts(last_ts):
    """"""
    print("kkkkk", last_ts)
    if last_ts is not None:
        current_time = datetime.now()
        last_ts = datetime.strptime(last_ts, "%Y-%m-%d %H:%M:%S.%f")
        print("lasts", last_ts)

        return (current_time - last_ts).total_seconds()
    else:
        return 1000
