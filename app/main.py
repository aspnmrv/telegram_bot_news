import re
import asyncio
import logging
import config
import ssl

from news.news import News
from sender.sender import Sender
from telethon.tl.custom import Button
from telethon import TelegramClient, events, sync, functions
from telethon.tl.types import InputPeerChannel
from globals import TOPICS, LIMIT_REQUESTS, MAX_LENGTH_KEYWORDS, FLOOD_SECONDS
from tools.tools import read_data, \
    is_expected_steps, get_keyboard, match_topics_name, \
    get_stat_interests, get_stat_keywords, send_user_main_stat, send_user_file_stat, get_choose_topics, is_ru_language,\
    get_code_fill_form, get_diff_between_ts
from db.db_tools import _update_current_user_step, _update_user_states, _get_user_states, \
    _get_current_user_step, _create_db
from topics.topics import get_state_markup, update_text_from_state_markup, build_markup, get_proposal_topics, get_available_topics
from pathlib import Path
from db.db import *

logging.basicConfig(filename=Path(__file__).parent.resolve() / "data" / "logs.log", level=logging.INFO)
logging.info("start")


api_id = config.app_id
api_hash = config.api_hash
bot_token = config.bot_token
PASS = config.password
login = config.login

PATH = Path(__file__).parent.resolve() / "data"

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

bot = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)

session_dir = Path(__file__).parent.resolve()

client = TelegramClient(
    str("session_name.session"),
    api_id,
    api_hash
)

client.connect()

print(client.is_user_authorized())

if not client.is_user_authorized():
    try:
        client.sign_in(password=PASS)
    except:
        print("Error")
        client.send_code_request(phone=login, force_sms=False)
        print(client)
        try:
            client.sign_in(login, input("Enter code: "))
        except:
            client.sign_in(password=PASS)
print(client.is_user_authorized())


@bot.on(events.NewMessage(pattern="/news"))
async def get_news(event):
    print(event)
    user_id = event.message.peer_id.user_id
    if await get_code_fill_form(user_id) == -1:
        await event.client.send_message(event.chat_id,
                                        "Еще не выбраны настройки 🙃\n\nНажимай на /start", buttons=Button.clear())
        await update_data_events_db(user_id, "news", {"step": -1, "error": "without users"})
    elif await get_code_fill_form(user_id) == 1:
        keyboard = await get_keyboard(["Добавить каналы", "Не нужно"])
        await _update_current_user_step(user_id, 824)
        await event.client.send_message(event.chat_id, "Кажется, у нас еще ничего не заполнено!\n\n"
                                                       "Сначала нужно выбрать набор каналов ☺️", buttons=keyboard)
        await update_data_events_db(user_id, "news", {"step": -1, "error": "without channels"})
    elif await get_code_fill_form(user_id) == 2:
        keyboard = await get_keyboard(["Добавить темы", "Не нужно"])
        await _update_current_user_step(user_id, 823)
        await event.client.send_message(event.chat_id, "Еще не выбраны интересы. Сделаем это прямо сейчас? ☺️", buttons=keyboard)
        await update_data_events_db(user_id, "news", {"step": -1, "error": "without channels"})
    else:
        last_ts_event = await get_event_from_db(user_id, "news")
        print("last_ts_event", last_ts_event)
        if await get_diff_between_ts(str(last_ts_event)) <= FLOOD_SECONDS:
            print("flood")
            await event.client.send_message(event.chat_id, "Слишком частые запросы!\n\nПопробуй "
                                                           "через несколько минут 🙂", buttons=Button.clear())
            await update_data_events_db(user_id, "news", {"step": -1, "error": "flood"})
        else:
            cnt_uses = await get_stat_use_db(user_id)
            if cnt_uses < LIMIT_REQUESTS:
                await event.client.send_message(event.chat_id, "Обрабатываю..Мне потребуется до 6 минут ☺️",
                                                buttons=Button.clear())
                await update_data_events_db(user_id, "news", {"step": -1})

                user_topics = await get_user_topics_db(user_id)
                if user_topics:
                    sender = Sender(client, bot)
                    data = await get_data_channels_db(user_id)
                    await sender.send_aggregate_news(user_id, data, user_topics, False)
                else:
                    await event.client.send_message(event.chat_id,
                                                    "Добавленных каналов еще нет 🙃\n\n"
                                                    "Изменить список каналов можно "
                                                    "по команде /channels", buttons=Button.clear())
            else:
                await event.client.send_message(event.chat_id,
                                                "Слишком много запросов за сегодня 🤓", buttons=Button.clear())
    return


@bot.on(events.NewMessage(pattern="/summary"))
async def get_summary(event):
    print(event)
    user_id = event.message.peer_id.user_id
    if await get_code_fill_form(user_id) == -1:
        await event.client.send_message(event.chat_id,
                                        "Еще не выбраны настройки 🙃\n\nНажимай на /start", buttons=Button.clear())
        await update_data_events_db(user_id, "summary", {"step": -1, "error": "without users"})
    elif await get_code_fill_form(user_id) == 1:
        keyboard = await get_keyboard(["Добавить каналы", "Не нужно"])
        await _update_current_user_step(user_id, 824)
        await event.client.send_message(event.chat_id, "Кажется, у нас еще ничего не заполнено!\n\n"
                                                       "Сначала нужно выбрать набор каналов ☺️", buttons=keyboard)
        await update_data_events_db(user_id, "summary", {"step": -1, "error": "without channels"})
    elif await get_code_fill_form(user_id) == 2:
        keyboard = await get_keyboard(["Добавить темы", "Не нужно"])
        await _update_current_user_step(user_id, 823)
        await event.client.send_message(event.chat_id, "Еще не выбраны интересы. Сделаем это прямо сейчас? ☺️", buttons=keyboard)
        await update_data_events_db(user_id, "summary", {"step": -1, "error": "without channels"})
    else:
        print("else")
        last_ts_event = await get_event_from_db(user_id, "summary")
        print("last_ts_event", last_ts_event)
        if await get_diff_between_ts(str(last_ts_event)) <= FLOOD_SECONDS:
            print("get_diff_between_ts")
            await event.client.send_message(event.chat_id, "Слишком частые запросы!\n\nПопробуй "
                                                           "через несколько минут 🙂", buttons=Button.clear())
            await update_data_events_db(user_id, "summary", {"step": -1, "error": "flood"})
        else:
            print("else 2")
            await update_data_events_db(user_id, "summary", {"step": -1})
            cnt_uses = await get_stat_use_db(user_id)
            if cnt_uses < LIMIT_REQUESTS:
                await event.client.send_message(event.chat_id, "Обрабатываю..Мне потребуется до 6 минут ☺️",
                                                buttons=Button.clear())
                user_topics = await get_user_topics_db(user_id)
                if user_topics:
                    sender = Sender(client, bot)
                    data = await get_data_channels_db(user_id)
                    await sender.send_aggregate_news(user_id, data, user_topics, True)
                else:
                    await event.client.send_message(event.chat_id,
                                                    "Добавленных каналов еще нет 🙃\n\n"
                                                    "Изменить список каналов можно "
                                                    "по команде /channels", buttons=Button.clear())
            else:
                await event.client.send_message(event.chat_id,
                                                "Слишком много запросов за сегодня 🤓", buttons=Button.clear())
    return


@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await _create_db()
    try:
        await _get_current_user_step(event.message.peer_id.user_id)
    except:
        pass

    sender_info = await event.get_sender()
    user_id = event.message.peer_id.user_id
    if not await is_user_exist_db(user_id):
        await update_data_users_db(sender_info)
    await _update_current_user_step(user_id, 1)

    keyboard = await get_keyboard(["Начать 🚀", "Обо мне"])
    text = """Привет! 👋\n\nЯ могу помочь фильтровать новостные посты из твоих любимых каналов. \nЗаполним список каналов, выберем интересы 📝\n\nНачнем?"""
    await event.client.send_message(event.chat_id, text, buttons=keyboard)
    await update_data_events_db(user_id, "start", {"step": -1})
    return


@bot.on(events.NewMessage(pattern="Начать 🚀"))
async def get_begin(event):
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [3, 24]):
        keyboard = await get_keyboard(["Продолжить", "Назад"])
        await _update_current_user_step(user_id, 2)
        await event.client.send_message(
            event.chat_id,
            "Присылай мне по одному репосту из каналов, которые ты хочешь читать! Я их запомню и буду "
            "искать новости там 🕵️.\n\nНо выбери только самые интересные каналы! Пока можно"
            " добавлять не более 3-х каналов 😇\n\n"
            "Я умею работать только с русскоязычными новостными каналами. Можешь добавить, "
            "конечно, любые, но тогда я буду бесполезен 😔",
            buttons=keyboard
        )
    elif await is_expected_steps(user_id, [1]):
        await _update_current_user_step(user_id, 2)
        back_button = await get_keyboard(["Назад"])
        await event.client.send_message(
            event.sender_id,
            "Присылай мне по одному репосту из каналов, которые ты хочешь читать! Я их запомню и буду "
            "искать новости там 🕵️.\n\nНо выбери только самые интересные каналы! Пока можно"
            " добавлять не более 3-х каналов 😇\n\n"
            "Я умею работать только с русскоязычными новостными каналами. Можешь добавить, "
            "конечно, любые, но тогда я буду бесполезен 😔",
            buttons=back_button
        )
    else:
        pass
    return


@bot.on(events.CallbackQuery())
async def handler(event):
    data_filter = event.data.decode("utf-8").split("-")
    if len(data_filter) < 2:
        user_id = event.sender_id
        current_topics = await _get_user_states(user_id, "topics")
        current_state = await _get_user_states(user_id, "states")
        current_topics = await match_topics_name(current_topics)
        topic_clicked = (event.data.split(b'$')[0]).decode("utf-8")

        markup = bot.build_reply_markup(await build_markup(current_topics, current_state))
        await update_text_from_state_markup(markup, current_state, current_topics, topic_clicked)
        await get_state_markup(markup, user_id)

        await event.client.edit_message(event.sender_id, event.message_id, buttons=markup)
    else:
        await event.client.edit_message(event.sender_id, event.message_id, "Спасибо ☺️")
        data = event.data.decode("utf-8")
        uid = data[:-2]
        score = int(data.split("-")[-1])
        await insert_score_db(uid, score)


@bot.on(events.NewMessage(pattern="Продолжить"))
async def get_end(event):
    """"""
    user_id = event.message.peer_id.user_id
    await update_data_events_db(user_id, "its_all", {"step": -1})

    if await is_expected_steps(user_id, [4]):
        await _update_current_user_step(user_id, 3)
        user_cur_states = await _get_user_states(user_id, "states")

        user_cur_topics = await _get_user_states(user_id, "topics")

        user_cur_topics = await match_topics_name(user_cur_topics)
        markup = bot.build_reply_markup(await get_proposal_topics(user_cur_topics, user_cur_states))

        await get_state_markup(markup, user_id)
        success_button = await get_keyboard(["Готово!", "Назад"])
        await event.client.send_message(event.chat_id, "Выбери интересующие темы 🐥\n", buttons=markup)
        await event.client.send_message(event.sender_id, "Когда закончишь с выбором, жми Готово!", buttons=success_button)
    elif await is_expected_steps(user_id, [8]):
        await _update_current_user_step(user_id, 31)
        user_cur_states = await _get_user_states(user_id, "states")
        user_cur_topics = await _get_user_states(user_id, "topics")
        user_cur_topics = await match_topics_name(user_cur_topics)
        markup = bot.build_reply_markup(await get_proposal_topics(user_cur_topics, user_cur_states))

        await get_state_markup(markup, user_id)
        success_button = await get_keyboard(["Готово!"])
        await event.client.send_message(event.chat_id, "Выбери интересующие темы 🐥\n", buttons=markup)
        await event.client.send_message(event.sender_id, "Когда закончишь с выбором, жми Готово!",
                                        buttons=success_button)
    elif await is_expected_steps(user_id, [2, 9]):
        await _update_current_user_step(user_id, 3)
        total_topics = list(TOPICS.keys())

        await _update_user_states(user_id, "topics", total_topics)
        await _update_user_states(user_id, "states", ["" for _ in range(len(total_topics))])

        proposal_topics = await match_topics_name(total_topics)
        markup = bot.build_reply_markup(await get_proposal_topics(proposal_topics))

        await get_state_markup(markup, user_id)
        success_button = await get_keyboard(["Готово!", "Назад"])
        text = "Выбери интересующие темы 🐥\n"
        await event.client.send_message(event.chat_id, text, buttons=markup)
        await event.client.send_message(event.sender_id,
                                        "Когда закончишь с выбором, жми Готово 👇", buttons=success_button)
    else:
        pass
    return


async def wait_post(event):
    """"""
    keyboard = await get_keyboard(["Продолжить"])
    await event.client.send_message(event.chat_id, "Принял. Еще?😏", buttons=keyboard)

    return


@bot.on(events.NewMessage(forwards=True))
async def forwards_message(event):
    user_id = event.message.peer_id.user_id
    if await is_expected_steps(user_id, [2, 9]):
        if await is_expected_steps(user_id, [9]):
            await remove_from_db("user_channels", user_id)
        if event.message.message == "":
            await asyncio.sleep(1)
        else:
            await event.client.send_message(event.chat_id, "Обрабатываю..", buttons=Button.clear())
            current_step = await _get_current_user_step(user_id)
            try:
                forward_channel_id = int(str("100") + str(event.message.fwd_from.from_id.channel_id)) * -1
                channel_info = await News.get_channel_info(forward_channel_id)
                if not channel_info:
                    await asyncio.sleep(2)
                    channel_info = await News.get_channel_info(forward_channel_id)
                    username_forward_channel = channel_info
                else:
                    username_forward_channel = channel_info
            except Exception as e:
                username_forward_channel = ""
                forward_channel_id = -1
                await event.client.send_message(user_id, "Такс, либо это совсем "
                                                         "не канал, либо канал, но закрытый. "
                                                         "Попробуем что-то другое? 🙂", buttons=Button.clear())
                await update_data_events_db(user_id, "forward_error",
                                            {"step": current_step,
                                             "channel_id": int(forward_channel_id), "error": "wrong_channel"})
            if username_forward_channel and forward_channel_id != -1:
                user_channels = await get_user_channels_db(user_id)
                channels_unique = set(user_channels)
                if str(username_forward_channel) in list(channels_unique):
                    await update_data_events_db(user_id, "forward_error",
                                             {"step": current_step,
                                              "channel_id": int(forward_channel_id), "error": "exist"})
                    keyboard = await get_keyboard(["Продолжить"])
                    await event.client.send_message(event.chat_id,
                                                    "Этот канал уже добавлен! Но мы можем добавить другой 🙃",
                                                    buttons=keyboard)
                elif len(channels_unique) == 3 and str(username_forward_channel) not in channels_unique:
                    await update_data_events_db(user_id, "forward_error",
                                             {"step": current_step,
                                              "channel_id": int(forward_channel_id), "error": "limit"})
                    text = "Пока нельзя добавлять больше 3-х каналов. 😔\n\n" \
                           "Но список в любой момент можно изменить по команде из меню"
                    keyboard = await get_keyboard(["Продолжить"])
                    await event.client.send_message(event.chat_id, text, buttons=keyboard)
                else:
                    message_from_channel = event.message.message
                    is_ru_channel = True
                    if message_from_channel and len(message_from_channel) > 10:
                        if not await is_ru_language([message_from_channel]):
                            is_ru_channel = False

                    if not is_ru_channel:
                        keyboard = await get_keyboard(["Продолжить"])
                        await event.client.send_message(
                            event.chat_id,
                            "Кажется, этот канал содержит много постов на другом языке, "
                            "а я пока умею работать только с ru-текстом 😔\n\nПопробуем что-то другое?)",
                            buttons=keyboard
                        )
                        await update_data_events_db(user_id, "forward_error",
                                                    {"step": current_step,
                                                     "channel_id": int(forward_channel_id), "error": "no_ru"})
                    else:
                        await update_data_events_db(user_id, "forward_message",
                                                 {"step": current_step, "channel_id": forward_channel_id})
                        await update_user_channels_db(user_id, str(username_forward_channel))
                        await wait_post(event)
                        if await is_expected_steps(user_id, [9]):
                            await event.client.send_message(event.chat_id, "Кстати, не забудь добавить все каналы, "
                                                                     "которые тебе нужны 📝\n\nПредыдущий список каналов "
                                                                     "я очистил")
                        await _update_current_user_step(user_id, 2)
            else:
                pass
    else:
        pass


@bot.on(events.NewMessage(pattern="Готово!"))
async def get_done(event):
    """"""
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [6, 5, 11]):
        await _update_current_user_step(user_id, 4)
        text = "Могу исключить из отправок публикации, " \
               "содержащие выбранные тобой ключевые слова. Не буду присылать тебе посты, в которых их " \
               "найду 🕵️\n"
        keyboard = await get_keyboard(["Добавить", "Не нужно", "Назад"])
        await event.client.send_message(event.chat_id, text, buttons=keyboard)
    elif await is_expected_steps(user_id, [3, 4]):
        current_step = await _get_current_user_step(user_id)
        user_cur_states = await _get_user_states(user_id, "states")
        user_cur_topics = await _get_user_states(user_id, "topics")
        chooses_topic = list()

        for state, topic in zip(user_cur_states, user_cur_topics):
            if state != "":
                chooses_topic.append(topic)

        if len(chooses_topic) != 0:
            await update_data_events_db(user_id, "choose_topic", {"step": current_step, "topics": chooses_topic})
            await update_data_topics_db(user_id, chooses_topic)
            if await is_expected_steps(user_id, [3]):
                user_cur_topics = await _get_user_states(user_id, "topics")
                if len(user_cur_topics) != 0:
                    text = "Запомнил! \n\nМогу исключить из отправок публикации, " \
                   "содержащие выбранные тобой ключевые слова. Не буду присылать тебе посты, в которых " \
                   "найду такое слово 🕵️\n"
                    keyboard = await get_keyboard(["Добавить", "Не нужно", "Назад"])
                    await _update_current_user_step(user_id, 4)
                    await event.client.send_message(event.chat_id, text, buttons=keyboard)
                else:
                    text = "Не выбрано ни одной темы..🦦"
                    keyboard = await get_keyboard(["Готово!"])
                    await event.client.send_message(event.chat_id, text, buttons=keyboard)
                    await get_end(event)
            else:
                text = "Запомнил!"
                keyboard = await get_keyboard(["Запустить"])
                await _update_current_user_step(user_id, 4)
                await event.client.send_message(event.chat_id, text, buttons=keyboard)
        else:
            text = "Не выбрано ни одной темы..🦦"
            keyboard = await get_keyboard(["Готово!"])
            await event.client.send_message(event.chat_id, text, buttons=keyboard)
    elif await is_expected_steps(user_id, [31]):
        user_cur_states = await _get_user_states(user_id, "states")
        user_cur_topics = await _get_user_states(user_id, "topics")

        chooses_topics = await get_choose_topics(user_cur_states, user_cur_topics)

        if chooses_topics:
            await update_data_topics_db(user_id, chooses_topics)
            text = "Обновил список тем 💫"
        else:
            text = "Не выбрано ни одной темы..🦦"
            keyboard = await get_keyboard(["Готово!"])
            await event.client.send_message(event.chat_id, text, buttons=keyboard)

        await event.client.send_message(event.chat_id, text, buttons=Button.clear())
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="Добавить"))
async def get_add_keywords(event):
    """"""
    user_id = event.message.peer_id.user_id
    current_step = await _get_current_user_step(user_id)
    await update_data_events_db(user_id, "add_keywords", {"step": current_step})

    if await is_expected_steps(user_id, [4]):
        await _update_current_user_step(user_id, 5)
        text = "Напиши мне все ключевые слова через запятую (минимум два слова), " \
               "чтобы я мог исключить новости, в которых они встречаются \n" \
               "Например: `футбол, война, криптовалюты`"
        await event.client.send_message(event.chat_id, text, buttons=Button.clear())
    elif await is_expected_steps(user_id, [7]):
        text = f"Введи через запятую новые ключевые слова " \
               f"(минимум, два слова)"
        await event.client.send_message(event.chat_id, text, buttons=Button.clear())
    else:
        pass

    return


async def filter_keywords(event):
    """"""
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [5, 7, 14]) and event.message.message != "Добавить":
        return True
    else:
        return False


@bot.on(events.NewMessage(pattern=r'[^,]+(,[^,]+)+', forwards=False))
async def create_keywords(event):
    """"""
    keywords = event.message.message
    user_id = event.message.peer_id.user_id
    current_step = await _get_current_user_step(user_id)

    if await is_expected_steps(user_id, [5]):
        await _update_current_user_step(user_id, 6)
        if len(keywords) > MAX_LENGTH_KEYWORDS:
            await event.client.send_message(event.chat_id, "Слишком много слов, "
                                                           "давай попробуем сократить список 🌝")
            await update_data_events_db(user_id, "input_keywords", {"step": current_step, "error": "too_many"})
        else:
            pattern = re.compile(r'\s+')
            keywords = re.sub(pattern, '', keywords)
            if len(keywords.split(",")) > 0:
                keywords = keywords.split(",")
                keywords = [word.lower() for word in keywords if word != ""]
            await update_user_keywords_db(user_id, keywords)

            text = "Отлично! Я добавил выбранные ключевые слова 🗝\n\n" \
                   "Давай проверим все настройки 😌"
            keyboard = await get_keyboard(["Проверить", "Назад"])
            await event.client.send_message(event.chat_id, text, buttons=keyboard)
            await update_data_events_db(user_id, "input_keywords", {"step": current_step})
    elif await is_expected_steps(user_id, [7]):
        await remove_from_db("user_keywords", user_id)
        await _update_current_user_step(user_id, 6)
        if len(keywords) > MAX_LENGTH_KEYWORDS:
            await event.client.send_message(event.chat_id, "Слишком много слов, давай попробуем сократить список 🌝")
            await update_data_events_db(user_id, "input_keywords", {"step": current_step, "error": "too_many"})
        else:
            pattern = re.compile(r'\s+')
            keywords = re.sub(pattern, '', keywords)
            if len(keywords.split(",")) > 0:
                keywords = keywords.split(",")
                keywords = [word.lower() for word in keywords if word != ""]
            await update_user_keywords_db(user_id, keywords)

            text = "Отлично! Я добавил выбранные ключевые слова 🗝\n\n" \
                   "Давай проверим все настройки 😌"
            keyboard = await get_keyboard(["Проверить"])
            await event.client.send_message(event.chat_id, text, buttons=keyboard)
            await update_data_events_db(user_id, "input_keywords", {"step": current_step})
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="Не нужно"))
async def get_dont_keywords(event):
    """"""
    user_id = event.message.peer_id.user_id
    current_step = await _get_current_user_step(user_id)
    await update_data_events_db(user_id, "no_keywords", {"step": current_step})

    await remove_from_db("user_keywords", user_id)
    if await is_expected_steps(user_id, [4, 6]):
        await _update_current_user_step(user_id, 5)
        keyboard = await get_keyboard(["Проверить", "Назад"])
        text = "Оки. Тогда давай еще раз все проверим!"
        await event.client.send_message(event.chat_id, text, buttons=keyboard)
    elif await is_expected_steps(user_id, [7]):
        text = "Оки!"
        keyboard = await get_keyboard(["Проверить"])
        await event.client.send_message(event.chat_id, text, buttons=keyboard)
    elif await is_expected_steps(user_id, [823, 824]):
        text = "Оки!"
        await event.client.send_message(event.chat_id, text, buttons=Button.clear())
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="Проверить"))
async def get_go(event):
    """"""
    user_id = event.message.peer_id.user_id
    if await is_expected_steps(user_id, [5, 6, 13, 7]):
        await _update_current_user_step(user_id, 11)
        channels = await get_user_channels_db(user_id)
        channels = set(channels)
        channels = ", ".join([f"@{channel}" for channel in channels])
        topics = await get_user_topics_db(user_id)
        topics = await match_topics_name(topics)
        topics = ", ".join(topics)
        keywords = await get_user_keywords_db(user_id)
        keywords = ", ".join(keywords)

        text = f"Давай все проверим!\n\n\n💌 **Выбранные каналы:** {channels or 'Не выбрано'} \n\n" \
               f"📝 **Темы:** {topics or 'Не выбрано'} \n\n" \
               f"🗝 **Ключевые слова для исключения:** {keywords or 'Не выбрано'}\n"
        keyboard = await get_keyboard(["Все верно ✅", "Изменить"])

        await event.client.send_message(event.chat_id, text, buttons=keyboard)
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="Все верно ✅"))
async def get_accept(event):
    """"""
    user_id = event.message.peer_id.user_id
    current_step = await _get_current_user_step(user_id)

    if await is_expected_steps(user_id, [11]):
        await _update_current_user_step(user_id, 12)
        text = "Ура, почти все готово!😇\n\nЧтобы запустить фильтрацию новостей, выбирай из списка команд" \
               " /summary, этом режиме я сделаю обобщение длинных новостей " \
               "по выбранным темам в короткие выдержки 🤗\n\n" \
               "Также можно запустить фильтрацию новостей с репостами из каналов по команде /news. " \
               "В этом режиме я буду пересылать посты по выбранным темам из твоих каналов\n\n" \
               "Рассылка будет приходить по твоему запросу в выбранном виде (краткие выдержки или репосты)\n\n" \
               "Кстати, набор каналов / темы / ключевые слова всегда можно изменить по командам из меню слева," \
               "Информация по дополнительным командам доступна по команде /help 💜\n" \
               "Также можно посмотреть интересную статистику по команде /stat 📊\n\n" \
               "Теперь можно смело отписываться от кучи новостей 😏"
        await event.client.send_message(event.chat_id, text, buttons=Button.clear())
        await update_data_events_db(user_id, "is_success", {"step": current_step})
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="Изменить"))
async def get_change(event):
    """"""
    user_id = event.message.peer_id.user_id
    current_step = await _get_current_user_step(user_id)

    if await is_expected_steps(user_id, [11, 12]):
        await _update_current_user_step(user_id, 13)
        text = "Чтобы изменить параметры, воспользуйся командами\n\n" \
               "/interests - сброс и изменение тем\n" \
               "/channels - смена читаемых каналов\n" \
               "/keywords - изменение ключевых слов для исключения\n" \
               "/help - помощь по боту"
        keyboard = await get_keyboard(["Назад"])
        await event.client.send_message(event.chat_id, text, buttons=keyboard)
        await update_data_events_db(user_id, "change", {"step": current_step})
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="Далее"))
async def get_next(event):
    """"""
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [11]):
        await get_go(event)

    return


@bot.on(events.NewMessage(pattern="Добавить темы"))
async def add_topics_from_empty(event):
    """"""
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [823]):
        await _update_current_user_step(user_id, 2)
        await get_end(event)

    return


@bot.on(events.NewMessage(pattern="Добавить каналы"))
async def add_channels_from_empty(event):
    """"""
    user_id = event.message.peer_id.user_id
    if await is_expected_steps(user_id, [824]):
        await _update_current_user_step(user_id, 1)
        await get_begin(event)

    return


@bot.on(events.NewMessage(pattern="Обо мне"))
async def get_next(event):
    """"""
    user_id = event.message.peer_id.user_id
    current_step = await _get_current_user_step(user_id)

    if await is_expected_steps(user_id, [1]):
        await _update_current_user_step(user_id, 10)
        keyboard = await get_keyboard(["Назад"])
        text = "AI Бот, который поможет фильтровать новости из разных каналов" \
               " по выбранным интересам.\n\nВ наше время бывает трудно остановиться," \
               " читая все новости подряд и легко словить меланхолию от прочитанного 😔\n" \
               "После выбора каналов, интересов и выбора ~~стопслов~~ ключевых слов, можно воспользоваться" \
               " мной в двух режимах:\nЯ могу присылать репосты из " \
               "выбранных каналов по выбранным интересам, а также присылать краткие выдержки" \
               " новостей из выбранных каналов по выбранным интересам\n\nПомощь доступна " \
               "по команде /help\n\nРад быть полезным 🫡"
        await event.client.send_message(event.chat_id, text, buttons=keyboard)
        await update_data_events_db(user_id, "about_me", {"step": current_step})
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="Назад"))
async def get_back(event):
    """"""

    user_id = event.message.peer_id.user_id
    if await is_expected_steps(user_id, [2]):
        await start(event)
    elif await is_expected_steps(user_id, [3]):
        await get_begin(event)
    elif await is_expected_steps(user_id, [4]):
        await get_end(event)
    elif await is_expected_steps(user_id, [6, 5]):
        await get_done(event)
    elif await is_expected_steps(user_id, [10]):
        await start(event)
    elif await is_expected_steps(user_id, [11]):
        await get_done(event)
    elif await is_expected_steps(user_id, [13]):
        await get_go(event)
    elif await is_expected_steps(user_id, [9]):
        await change_settings(event)

    return


@bot.on(events.NewMessage(pattern="/keywords"))
async def change_keywords(event):
    user_id = event.message.peer_id.user_id
    await update_data_events_db(user_id, "change_keywords", {"step": -1})
    await _update_current_user_step(user_id, 7)
    if not await get_user_keywords_db(user_id):
        keyboard = await get_keyboard(["Добавить", "Не нужно"])
        await event.client.send_message(event.chat_id, "Список ключевых слов пуст 🙃", buttons=keyboard)
    else:
        keyboard = await get_keyboard(["Удалить слова"])
        keywords = await get_user_keywords_db(user_id)
        keywords = ", ".join(keywords)
        text = f"Текущий список ключевых слов: {keywords} \n\nВведи через запятую новые ключевые слова " \
               f"(минимум, два слова)"
        await event.client.send_message(event.chat_id, text, buttons=keyboard)

    return


@bot.on(events.NewMessage(pattern="/interests"))
async def change_topics(event):
    user_id = event.message.peer_id.user_id

    await update_data_events_db(user_id, "change_interests", {"step": -1})
    if await get_code_fill_form(user_id) == -1:
        await event.client.send_message(event.chat_id,
                                        "Еще не выбраны настройки ☺️\n\nНажимай на /start", buttons=Button.clear())
        await update_data_events_db(user_id, "change_interests", {"step": -1, "error": "without users"})
    elif await get_code_fill_form(user_id) == 1:
        keyboard = await get_keyboard(["Добавить каналы", "Не нужно"])
        await _update_current_user_step(user_id, 824)
        await event.client.send_message(event.chat_id, "Кажется, у нас еще ничего не заполнено!\n\n"
                                                       "Сначала нужно выбрать набор каналов ☺️", buttons=keyboard)
        await update_data_events_db(user_id, "change_interests", {"step": -1, "error": "without channels"})
    elif await get_code_fill_form(user_id) == 2:
        keyboard = await get_keyboard(["Добавить темы", "Не нужно"])
        await _update_current_user_step(user_id, 823)
        await event.client.send_message(event.chat_id, "Еще не выбраны интересы. Сделаем это прямо сейчас? ☺️", buttons=keyboard)
        await update_data_events_db(user_id, "change_interests", {"step": -1, "error": "without channels"})
    else:
        await _update_current_user_step(user_id, 8)
        await get_end(event)

    return


@bot.on(events.NewMessage(pattern="/channels"))
async def change_channels(event):
    user_id = event.message.peer_id.user_id
    await update_data_events_db(user_id, "change_channels", {"step": -1})
    if await get_code_fill_form(user_id) == -1:
        await event.client.send_message(event.chat_id,
                                        "Еще не выбраны настройки ☺️\n\nНажимай на /start", buttons=Button.clear())
        await update_data_events_db(user_id, "change_channels", {"step": -1, "error": "without users"})
    elif await get_code_fill_form(user_id) == 1:
        keyboard = await get_keyboard(["Добавить каналы", "Не нужно"])
        await _update_current_user_step(user_id, 824)
        await event.client.send_message(event.chat_id, "Кажется, у нас еще ничего не заполнено!\n\n"
                                                       "Сначала нужно выбрать набор каналов ☺️", buttons=keyboard)
        await update_data_events_db(user_id, "change_channels", {"step": -1, "error": "without channels"})
    else:
        await _update_current_user_step(user_id, 9)
        channels = await get_user_channels_db(user_id)
        channels = set(channels)
        channels = [f"@{channel}" for channel in channels]
        channels = ", ".join(channels)
        keyboard = await get_keyboard(["Назад"])
        text = f"Текущий список читаемых каналов: {channels} \nЧтобы выбрать новые, перешли по одному посту" \
               f" из каждого канала, который хочешь читать (не более трех каналов)" \
               f"\n\n"

        await event.client.send_message(event.chat_id, text, buttons=keyboard)

    return


@bot.on(events.NewMessage(pattern="/settings"))
async def change_settings(event):
    user_id = event.message.peer_id.user_id
    await update_data_events_db(user_id, "my_settings", {"step": -1})
    await _update_current_user_step(user_id, 24)
    if not await get_user_channels_db(user_id):
        keyboard = await get_keyboard(["Начнем?"])
        await event.client.send_message(event.chat_id,
                                        "Упс..настроек еще нет 🙃\n\nА значит - пора начать! /start", buttons=keyboard)
    else:
        channels = await get_user_channels_db(user_id)
        channels = set(channels)
        channels = ", ".join([f"@{channel}" for channel in channels])
        topics = await get_user_topics_db(user_id)
        if topics:
            topics = await match_topics_name(topics)
            topics = ", ".join(topics)
        else:
            topics = None
        keywords = await get_user_keywords_db(user_id)
        keywords = ", ".join(keywords)

        text = f"Текущие настройки: \n\n\n💌 **Выбранные каналы:** {channels or 'Не выбрано'} \n\n" \
               f"📝 **Темы:** {topics or 'Не выбрано'} \n\n" \
               f"🗝 **Ключевые слова для исключения:** {keywords or 'Не выбрано'}\n"

        await event.client.send_message(event.chat_id, text, buttons=Button.clear())

    return


@bot.on(events.NewMessage(pattern="/stat"))
async def get_stat(event):
    user_id = event.message.peer_id.user_id
    await update_data_events_db(user_id, "get_stat", {"step": -1})
    await _update_current_user_step(user_id, 67)

    filter_stat = await get_stat_filter_db(user_id)

    if filter_stat:
        await send_user_main_stat(event, filter_stat)
    else:
        keyboard = await get_keyboard(["Начнем?"])
        await event.client.send_message(event.chat_id, "У вас пока нет данных с личной статистикой. "
                                                       "Но никогда не поздно начать 😏", buttons=keyboard)

    file_topics = await get_stat_interests()
    await send_user_file_stat(event, file_topics, "Топ интересов, выбираемых пользователями")

    file_keywords = await get_stat_keywords()
    await send_user_file_stat(event, file_keywords, "Топ ключевых слов, выбираемых пользователями")

    return


@bot.on(events.NewMessage(pattern="Удалить слова"))
async def change_keywords(event):
    user_id = event.message.peer_id.user_id
    await update_data_events_db(user_id, "remove_keywords", {"step": -1})
    if await is_expected_steps(user_id, [7]):
        await remove_from_db("user_keywords", user_id)
        text = f"Удалил текущий список слов 💫"
        await event.client.send_message(event.chat_id, text, buttons=Button.clear())
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="/help"))
async def get_help(event):
    user_id = event.message.peer_id.user_id
    await update_data_events_db(user_id, "help", {"step": -1})

    text = f"Помощь по использованию бота\n\n\n" \
           f"Список доступных команд:\n\n" \
           f"/settings - Показать текущие настройки\n" \
           f"/interests - изменить темы для фильтрации новостей\n" \
           f"/keywords - изменить список ключевых слов\n" \
           f"/channels - сбросить и изменить список каналов для чтения\n" \
           f"/summary - запустить фильтрацию новостей с краткими выдержками\n" \
           f"/news - запустить фильтрацию новостей с пересылкой сообщений из каналов\n" \
           f"/stat - посмотреть статистику \n\n\n" \
           f""

    await event.client.send_message(event.chat_id, text, buttons=Button.clear())

    return


bot.run_until_disconnected()
client.run_until_disconnected()
