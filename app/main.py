import fasttext
import re
import time
import fnmatch
import config
from news import News

from sender import Sender
from telethon.tl.custom import Button
from telethon import TelegramClient, events, sync, functions
from globals import TOPICS

from tools import read_data, save_data, \
    is_expected_steps, get_keyboard, match_topics_name, remove_file
from db_tools import _update_current_user_step, _update_user_states, _get_user_states, _get_current_user_step, _truncate_table, _create_db
# from news import get_posts, get_news, get_channel_info
from prepare_data import prepare_data
from topics import get_state_markup, update_text_from_state_markup, build_markup, get_proposal_topics, get_available_topics
from pathlib import Path
from db import *


api_id = config.app_id
api_hash = config.api_hash
bot_token = config.bot_token
PASS = config.password
login = config.login
model_name = config.model_name


MODEL_PATH = Path(__file__).parent.resolve() / "model" / model_name
# DB_PATH = Path(__file__).parent.resolve() / "data" / "sophie_test8.db"

PATH = Path(__file__).parent.resolve() / "data"


model = fasttext.load_model(f"{MODEL_PATH}")

bot = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)

session_dir = Path(__file__).parent.parent.resolve()
client = TelegramClient(
    str(session_dir / "app" / "session_name.session"),
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
            client.sign_in(login, input('Enter code: '))
        except:
            client.sign_in(password=PASS)
print(client.is_user_authorized())


@bot.on(events.NewMessage(pattern="/(?i)admin"))
async def admin(event):
    user_id = event.message.peer_id.user_id
    user_topics = await get_user_topics_db(user_id)
    sender = Sender(client, bot, model)
    data = await sender.get_table()
    print("data", data)
    await sender.form_sender(data, user_topics)
    return


@bot.on(events.NewMessage(pattern="/(?i)start"))
async def start(event):
    await _create_db()
    try:
        await _get_current_user_step(event.message.peer_id.user_id)
    except:
        print("wow")
    sender_info = await event.get_sender()
    user_id = event.message.peer_id.user_id
    if not await is_user_exist_db(user_id):
        await update_data_users_db(sender_info)
    await _update_current_user_step(user_id, 1)

    keyboard = get_keyboard(["Начнем?", "Обо мне"])
    await event.client.send_message(event.chat_id, "Выбери что-нибудь :)", buttons=keyboard)
    return


@bot.on(events.NewMessage(pattern="Начнем?"))
async def get_begin(event):
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [3]):
        keyboard = get_keyboard(["Это все", "Назад"])
        await _update_current_user_step(user_id, 2)
        await event.client.send_message(
            event.chat_id,
            "Пришли мне по одному репосту из каналов, которые ты хочешь читать",
            buttons=keyboard
        )
    elif await is_expected_steps(user_id, [1]):
        await _update_current_user_step(user_id, 2)
        back_button = get_keyboard(["Назад"])
        await event.client.send_message(
            event.sender_id,
            "Пришли мне по одному репосту из каналов, которые ты хочешь читать",
            buttons=back_button
        )
    else:
        await event.client.send_message(event.chat_id, "Нет такого варианта")
    return


@bot.on(events.CallbackQuery())
async def handler(event):
    print(event)
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
        await event.client.edit_message(event.sender_id, event.message_id, "Спасибо)")
        print(event.data.decode("utf-8"))
        data = event.data.decode("utf-8")
        uid = data[:-2]
        score = int(data.split("-")[-1])
        await insert_score_db(uid, score)


@bot.on(events.NewMessage(pattern="Это все"))
async def get_end(event):
    """"""
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [4]):
        await _update_current_user_step(user_id, 3)
        user_cur_states = await _get_user_states(user_id, "states")
        user_cur_topics = await _get_user_states(user_id, "topics")
        user_cur_topics = await match_topics_name(user_cur_topics)
        markup = bot.build_reply_markup(await get_proposal_topics(user_cur_topics, user_cur_states))

        await get_state_markup(markup, user_id)
        success_button = get_keyboard(["Готово!", "Назад"])
        await event.client.send_message(event.chat_id, "Выбери интересующие темы", buttons=markup)
        await event.client.send_message(event.sender_id, "Когда закончишь с выбором, жми готово :)", buttons=success_button)
    elif await is_expected_steps(user_id, [8]):
        await _update_current_user_step(user_id, 31)
        user_cur_states = await _get_user_states(user_id, "states")
        user_cur_topics = await _get_user_states(user_id, "topics")
        user_cur_topics = await match_topics_name(user_cur_topics)
        markup = bot.build_reply_markup(await get_proposal_topics(user_cur_topics, user_cur_states))

        await get_state_markup(markup, user_id)
        success_button = get_keyboard(["Готово!"])
        await event.client.send_message(event.chat_id, "Выбери интересующие темы", buttons=markup)
        await event.client.send_message(event.sender_id, "Когда закончишь с выбором, жми готово :)",
                                        buttons=success_button)
    elif await is_expected_steps(user_id, [2, 9]):
        await _update_current_user_step(user_id, 3)
        print(PATH)
        files = fnmatch.filter(os.listdir(PATH), f'data_{user_id}_*.pkl')
        print("files", files)
        dfs = list()
        for file in files:
            print(file)
            data = await read_data(file)
            dfs += data
        for file in files:
            await remove_file(file)

        clean_messages = await prepare_data(dfs)

        all_topics = await get_available_topics(model, clean_messages)
        proposal_topics = list(sorted(set(all_topics)))
        total_topics = list(TOPICS.keys())
        best_topics = set.intersection(set(total_topics), set(proposal_topics))

        await _update_user_states(user_id, "topics", total_topics)
        await _update_user_states(user_id, "states", ["" for _ in range(len(total_topics))])

        proposal_topics = await match_topics_name(total_topics)
        markup = bot.build_reply_markup(await get_proposal_topics(proposal_topics))

        await get_state_markup(markup, user_id)
        success_button = get_keyboard(["Готово!", "Назад"])
        if len(best_topics) == 0:
            text = "Выбери любые интересующие темы"
        elif len(total_topics) - len(best_topics) < 3:
            text = "Выбери любые интересующие темы. Но, кажется, этот набор каналов не похож на новостной"
        else:
            text = "Выбери любые интересующие темы. Для этого набора каналов отлично подходят темы:" \
                   f"{', '.join(list(best_topics))}"
        await event.client.send_message(event.chat_id, text, buttons=markup)
        await event.client.send_message(event.sender_id, "Когда закончишь с выбором, жми готово :)", buttons=success_button)
    else:
        await event.client.send_message(event.chat_id, "Нет такой команды")
    return


async def wait_post(event):
    """"""
    keyboard = get_keyboard(["Это все"])
    await event.client.send_message(event.chat_id, "Принял. Еще?", buttons=keyboard, parse_mode="html")

    return


@bot.on(events.NewMessage(forwards=True))
async def forwards_message(event):
    user_id = event.message.peer_id.user_id
    if await is_expected_steps(user_id, [2, 9]):
        # if user_id == 1377533848 or await is_expected_steps(user_id, [9]):
        if await is_expected_steps(user_id, [2, 9]):
            await remove_from_db("user_channels", user_id)
        if event.message.message == "":
            time.sleep(1)
        else:
            await event.client.send_message(event.chat_id, "Обрабатываю..", buttons=Button.clear())
            current_step = await _get_current_user_step(user_id)
            forward_channel_id = int(str("100") + str(event.message.fwd_from.from_id.channel_id)) * -1
            channel_info = await News.get_channel_info(forward_channel_id)
            print(channel_info)
            username_forward_channel = channel_info["result"]["username"]
            user_channels = await get_user_channels_db(user_id)
            channels_unique = set(user_channels)
            if len(channels_unique) == 3:
                await update_data_events_db(user_id, "forward_error",
                                         {"step": current_step,
                                          "channel_id": forward_channel_id, "error": "limit"})
                text = "Пока нельзя добавлять больше 3-х каналов, но список в любой момент можно изменить по команде"
                keyboard = get_keyboard(["Это все"])
                await event.client.send_message(event.chat_id, text, buttons=keyboard)
            if str(forward_channel_id) in list(channels_unique):
                await update_data_events_db(user_id, "forward_error",
                                         {"step": current_step,
                                          "channel_id": forward_channel_id, "error": "exist"})
                keyboard = get_keyboard(["Это все"])
                await event.client.send_message(event.chat_id, "Этот канал уже добавлен", buttons=keyboard)
            else:
                await update_data_events_db(user_id, "forward_message",
                                         {"step": current_step, "channel_id": forward_channel_id})
                await update_user_channels_db(user_id, str(username_forward_channel))
                news = News(client=client)
                posts = await news.get_posts(forward_channel_id, limit=3)
                result = await news.get_news(posts=posts, num_dozen=1, forward_channel_id=forward_channel_id)

                await save_data(result["message"], str(user_id) + "_" + str(forward_channel_id))
                await wait_post(event)
    else:
        pass


@bot.on(events.NewMessage(pattern="Готово!"))
async def get_done(event):
    """"""
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [6, 5, 11]):
        await _update_current_user_step(user_id, 4)
        text = "Могу исключить из отправок публикации, " \
               "содержащие выбранные тобой ключевые слова. Продолжим?"
        keyboard = get_keyboard(["Добавить", "Не нужно", "Назад"])
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
        else:
            pass

        if await is_expected_steps(user_id, [3]):
            text = "Отличный выбор! \nМогу исключить из отправок публикации, " \
                   "содержащие выбранные тобой ключевые слова. Вдруг новости про футбол или " \
                   "очередной вирус уже надоели :) Продолжим?"
            keyboard = get_keyboard(["Добавить", "Не нужно", "Назад"])
            await _update_current_user_step(user_id, 4)
            await event.client.send_message(event.chat_id, text, buttons=keyboard)
        else:
            text = "Отличный выбор!"
            keyboard = get_keyboard(["Запустить"])
            await _update_current_user_step(user_id, 4)
            await event.client.send_message(event.chat_id, text, buttons=keyboard)
    elif await is_expected_steps(user_id, [31]):
        user_cur_states = await _get_user_states(user_id, "states")
        user_cur_topics = await _get_user_states(user_id, "topics")
        chooses_topic = list()
        for state, topic in zip(user_cur_states, user_cur_topics):
            if state != "":
                chooses_topic.append(topic)

        if len(chooses_topic) != 0:
            await update_data_topics_db(user_id, chooses_topic)
            text = "Обновил список тем"
        else:
            text = "Не выбрано ни одной темы"

        await event.client.send_message(event.chat_id, text, buttons=Button.clear())
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="Добавить"))
async def get_add_keywords(event):
    """"""
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [4]):
        await remove_from_db("user_keywords", user_id)
        await _update_current_user_step(user_id, 5)
        text = "Хорошо! Напиши мне все ключевые слова через запятую (минимум два слова), " \
               "чтобы я мог исключить новости, в которых они встречаются \nНапример: футбол, война, криптовалюты"
        await event.client.send_message(event.chat_id, text)
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


#pattern=r'[^,]+(,[^,]+)+'
@bot.on(events.NewMessage(pattern=r'[^,]+(,[^,]+)+', forwards=False))
async def create_keywords(event):
    """"""
    keywords = event.message.message
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [5]):
        await _update_current_user_step(user_id, 6)
        if len(keywords) > 1000:
            event.client.send_message(event.chat_id, "Слишком много слов, давай попробуем сократить список :)")
        else:
            pattern = re.compile(r'\s+')
            keywords = re.sub(pattern, '', keywords)
            keywords = keywords.split(",")
            await update_user_keywords_db(user_id, keywords)

            text = "Отлично! Я добавил выбранные ключевые слова\n\n"
            keyboard = get_keyboard(["Далее", "Назад"])
            await event.client.send_message(event.chat_id, text, buttons=keyboard)
    elif await is_expected_steps(user_id, [7, 14]):
        await remove_from_db("user_channels", user_id)
        await _update_current_user_step(user_id, 6)
        if len(keywords) > 1000:
            event.client.send_message(event.chat_id, "Слишком много слов, давай попробуем сократить список :)")
        else:
            pattern = re.compile(r'\s+')
            keywords = re.sub(pattern, '', keywords)
            keywords = keywords.split(",")

            await update_user_keywords_db(user_id, keywords)

            text = "Отлично! Я добавил выбранные ключевые слова\n\n"
            keyboard = get_keyboard(["Запустить"])
            await event.client.send_message(event.chat_id, text, buttons=keyboard)
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="Не нужно"))
async def get_dont_keywords(event):
    """"""
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [4, 6]):
        await _update_current_user_step(user_id, 5)
        keyboard = get_keyboard(["Запустить", "Назад"])
        text = "Хорошо. Тогда жмякай на запуск!"
        await event.client.send_message(event.chat_id, text, buttons=keyboard)
    elif await is_expected_steps(user_id, [7]):
        text = "Хорошо"
        keyboard = get_keyboard(["Запустить"])
        await event.client.send_message(event.chat_id, text, buttons=keyboard)
    else:
        await event.client.send_message(event.chat_id, "Нет такой команды")

    return


@bot.on(events.NewMessage(pattern="Запустить"))
async def get_go(event):
    """"""
    user_id = event.message.peer_id.user_id
    if await is_expected_steps(user_id, [5, 6, 13]):
        await _update_current_user_step(user_id, 11)
        channels = await get_user_channels_db(user_id)
        channels = set(channels)
        channels = ", ".join([f"@{channel}" for channel in channels])
        topics = await get_user_topics_db(user_id)
        topics = await match_topics_name(topics)
        topics = ", ".join(topics)
        keywords = await get_user_keywords_db(user_id)
        keywords = ", ".join(keywords)

        text = f"Давай все проверим\n\n\nВыбранные каналы: {channels} \n\n" \
               f"Темы: {topics} \n\n" \
               f"Ключевые слова для исключения: {keywords}\n"
        keyboard = get_keyboard(["Все верно", "Изменить"])

        await event.client.send_message(event.chat_id, text, buttons=keyboard)
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="Все верно"))
async def get_accept(event):
    """"""
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [11]):
        await _update_current_user_step(user_id, 12)
        text = "Фильтрация новостей запущена:)\n\nПримерно раз в час я буду присылать" \
               " отфильтрованные новости из твоих источников. \n\nЧтобы отключить меня, используй" \
               " команду /stop"
        await event.client.send_message(event.chat_id, text, buttons=Button.clear())
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="Изменить"))
async def get_change(event):
    """"""
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [11, 12]):
        await _update_current_user_step(user_id, 13)
        text = "Чтобы изменить параметры, воспользуйся командами\n\n" \
               "/interests - изменение тем\n" \
               "/channels - смена читаемых каналов\n" \
               "/keywords - изменение ключевых слов для исключения\n" \
               "/help - помощь по боту"
        keyboard = get_keyboard(["Назад"])
        await event.client.send_message(event.chat_id, text, buttons=keyboard)
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="Далее"))
async def get_next(event):
    """"""
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [6]):
        await get_dont_keywords(event)
    elif await is_expected_steps(user_id, [11]):
        await get_go(event)

    return


@bot.on(events.NewMessage(pattern="Обо мне"))
async def get_next(event):
    """"""
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [1]):
        await _update_current_user_step(user_id, 10)
        keyboard = get_keyboard(["Назад"])
        text = "Бот, который поможет фильтровать новости из разных каналов" \
               " по выбранным интересам.\n\nВ наше время бывает трудно остановиться," \
               " читая все новости подряд и легко словить меланхолию от прочитанного :)\n" \
               "После выбора каналов, интересов и выбора ~~стопслов~~ ключевых слов, примерно раз в час я буду присылать" \
               "новую порцию отфильтрованных постов из выбранных каналов\n\nЧтобы остановить меня, используй команду" \
               " /stop\nПомощь доступна по команде /help\n\nРад быть полезным :)"
        await event.client.send_message(event.chat_id, text, buttons=keyboard)
    else:
        await event.client.send_message(event.chat_id, "Нет такой команды")

    return


@bot.on(events.NewMessage(pattern="Добавить"))
async def get_next(event):
    """"""
    user_id = event.message.peer_id.user_id

    if await is_expected_steps(user_id, [7]):
        await _update_current_user_step(user_id, 14)
        text = f"Введи через запятую новые ключевые слова " \
               f"(минимум, два слова)"
        await event.client.send_message(event.chat_id, text, buttons=Button.clear())
    else:
        pass

    return


@bot.on(events.NewMessage(pattern="Назад"))
async def get_back(event):
    """"""
    print(event)
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

    return

# / commands


@bot.on(events.NewMessage(pattern="/(?i)keywords"))
async def change_keywords(event):
    user_id = event.message.peer_id.user_id
    await _update_current_user_step(user_id, 7)
    if not await get_user_keywords_db(user_id):
        keyboard = get_keyboard(["Добавить", "Не нужно"])
        await event.client.send_message(event.chat_id, "На данный момент список ключевых слов пуст", buttons=keyboard)
    else:
        keywords = await get_user_keywords_db(user_id)
        keywords = ", ".join(keywords)
        text = f"Текущий список ключевых слов: {keywords} \n\nВведи через запятую новые ключевые слова " \
               f"(минимум, два слова)"
        await event.client.send_message(event.chat_id, text, buttons=Button.clear())

    return


@bot.on(events.NewMessage(pattern="/(?i)interests"))
async def change_topics(event):
    user_id = event.message.peer_id.user_id
    if not await is_exist_temp_db("user_topics", user_id):
        await event.client.send_message(event.chat_id, "На данный момент нет выбранных тем", buttons=Button.clear())
    else:
        await _update_current_user_step(user_id, 8)
        await get_end(event)

    return


@bot.on(events.NewMessage(pattern="/(?i)channels"))
async def change_channels(event):
    user_id = event.message.peer_id.user_id
    await _update_current_user_step(user_id, 9)
    if not await get_user_channels_db(user_id):
        await event.client.send_message(event.chat_id, "На данный момент нет выбранных каналов!", buttons=Button.clear())
    else:
        channels = await get_user_channels_db(user_id)
        channels = set(channels)
        channels = [f"@{channel}" for channel in channels]
        channels = ", ".join(channels)
        text = f"Текущий список читаемых каналов: {channels} \nЧтобы выбрать новые, перешли по одному посту" \
               f" из каждого канала, который хочешь читать (не более трех каналов)\n "

        await event.client.send_message(event.chat_id, text, buttons=Button.clear())

    return


@bot.on(events.NewMessage(pattern="/(?i)help"))
async def change_channels(event):
    print(event)
    user_id = event.message.peer_id.user_id

    text = f"Помощь по использованию бота\n\n\n" \
           f"Список доступных команд:\n\n" \
           f"/settings - Показать текущие настройки\n" \
           f"/interests - изменить темы для фильтрации новостей\n" \
           f"/keywords - изменить список ключевых слов\n" \
           f"/channels - изменить список каналов для чтения\n" \
           f"/start - начать процесс заполнения настроек заново\n\n\n" \
           f"По вопросам и предложениям можно писать @aspnmrv" \
           f""

    await event.client.send_message(event.chat_id, text, buttons=Button.clear())

    return


bot.run_until_disconnected()
