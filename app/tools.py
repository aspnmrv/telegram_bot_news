import pickle
import os
import requests
import config
import tempfile

from io import BytesIO
from telethon.tl.custom import Button
from db_tools import _get_current_user_step
from globals import TOPICS
from pathlib import Path
from typing import List


PATH = Path(__file__).parent.resolve() / "data"
model_predict_path = config.model_predict_path


async def read_data(filename):
    """"""
    with open("/data/" + filename, "rb") as f:
        data = pickle.load(f)
    return data


async def save_data(data, suffix=""):
    """"""
    print(PATH)
    with open("/data/" + f"data_{suffix}.pkl", "wb") as f:
        pickle.dump(data, f)
    return


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


async def is_expected_steps(user_id, expected_steps):
    """"""
    current_step = await _get_current_user_step(user_id)

    if current_step in expected_steps:
        return True
    else:
        return False


def get_keyboard(text_keys: list) -> list:
    """"""
    keyboard = list()
    for key in range(len(text_keys)):
        keyboard.append([Button.text(text_keys[key], resize=True)])
    return keyboard


async def match_topics_name(topics):
    """"""
    match_topics = list()
    for topic in topics:
        match_topics.append(TOPICS[topic])
    return match_topics


async def unmatch_topic_name(topic):
    """"""
    unmatch = {v: k for k, v in TOPICS.items()}
    return unmatch[topic]


async def remove_file(filename):
    """"""
    os.remove(PATH / filename)
    return


async def get_estimate_markup(data):
    """"""
    markup = [
        [
            Button.inline(text="👍", data=str(data) + "-" + "1"),
            Button.inline(text="👎", data=str(data) + "-" + "0")
        ]
    ]

    return markup


async def model_predict(data: List[str]):
    """"""
    try:
        return requests.post(model_predict_path, json={"news": data}).json()
    except:
        return "The server is not responding"
