import sys
import os
print("topics")
sys.path.append(os.path.dirname(__file__))
sys.path.insert(1, os.path.realpath(os.path.pardir))

from telethon.tl.custom import Button
from app.db.db_tools import _update_user_states
print("topics2")
from app.tools.tools import model_predict
print("topics3")

async def get_state_markup(markup, user_id):
    """"""
    state = list()

    for row in range(len(markup.rows)):
        text = markup.rows[row].buttons[0].text
        state.append('✅' if '✅' in text else "")

    await _update_user_states(user_id, "states", state)

    return state


async def update_text_from_state_markup(markup, state, topics, name):
    """"""
    for elem in range(len(state)):
        if topics[elem] == name:
            if "✅" not in markup.rows[elem].buttons[0].text:
                markup.rows[elem].buttons[0].text += " ✅"
            else:
                markup.rows[elem].buttons[0].text = markup.rows[elem].buttons[0].text.split("✅")[0]
        else:
            markup.rows[elem].buttons[0].text = markup.rows[elem].buttons[0].text
    return markup


async def build_markup(topics, current_state):
    """"""
    markup = [
        [
            Button.inline(text=topics[i] + current_state[i], data=topics[i])
        ] for i in range(len(topics))
    ]

    return markup


async def get_proposal_topics(topics, states=None):
    """"""
    if states is None:
        buttons = [[Button.inline(text=topic, data=topic)] for topic in topics]
    else:
        buttons = [[Button.inline(text=topic + " " + state, data=topic)] for topic, state in zip(topics, states)]

    return buttons


async def get_available_topics(messages):
    """"""
    preds = await model_predict(messages)

    result = list()
    for pred in preds:
        result.append(pred[0].split("__label__")[1])
    return result
