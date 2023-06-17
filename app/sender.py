import uuid

from db import get_data_channels_db, update_send_messages_db, \
    update_user_last_post_db, get_user_last_post_db, insert_messages_score_db
from news import News
from prepare_data import prepare_data, get_pred_labels, check_keywords
from tools import match_topics_name, get_estimate_markup, unmatch_topic_name, model_predict
from datetime import datetime


class Sender:
    def __init__(self, client, bot):
        self.client = client
        self.bot = bot

    @staticmethod
    async def get_table():
        """"""
        data = await get_data_channels_db()

        return data

    @staticmethod
    async def generate_last_msg_users(user_last_messages):
        """"""
        last_msg_users = dict()

        for user in user_last_messages:
            channels = dict()
            for channel, post_id in user[1].items():
                channels[channel] = post_id
            last_msg_users[user[0]] = channels
        return last_msg_users

    async def generate_form(self, user_channels, user_topics, last_msg_users):
        """"""
        form = dict()
        for user, channels in user_channels.items():
            temp = {}
            channel_last_posts_log = dict()
            for channel in channels:
                posts = list()
                if user in last_msg_users and channel in last_msg_users[user].keys():
                    min_id = last_msg_users[user][channel]
                    is_first = False
                else:
                    min_id = 0
                    is_first = True
                news = News(self.client)
                result = await news.get_sender_posts(channel_name=channel, min_id=min_id, is_first=is_first)

                clean_messages = await prepare_data(result["message"])
                print(clean_messages)

                preds = await model_predict(clean_messages)
                print("preds", preds)
                labels = await get_pred_labels(preds)
                if result["id"]:
                    print("if result[id]:")
                    max_post_id = max(result["id"])
                    channel_last_posts_log[channel] = max_post_id

                for idx, (label, post) in enumerate(zip(labels, result["id"])):
                    print(label, post)
                    if label in user_topics and post not in [list(k.keys())[0] for k in posts] \
                            and not await check_keywords(user, clean_messages[idx]):
                        label_ru = await match_topics_name([label])
                        posts.append({post: label_ru[0]})
                temp[channel] = posts

            form[user] = temp
            if channel_last_posts_log:
                await update_user_last_post_db(user, channel_last_posts_log)
        return form

    async def form_sender(self, user_channels, user_topics):
        """"""
        user_last_messages = await get_user_last_post_db()
        last_msg_users = await self.generate_last_msg_users(user_last_messages)
        print("last_msg_users", last_msg_users)

        form = await self.generate_form(user_channels, user_topics, last_msg_users)
        print(form)

        for user, values in form.items():
            if user == 1377533848:
                data = dict()
                for channel, post_ids in values.items():
                    if post_ids:
                        for post_id in post_ids:
                            print(post_id)
                            uid = uuid.uuid4()
                            markup = self.bot.build_reply_markup(await get_estimate_markup(uid))
                            await self.bot.send_message(user, f"[{list(post_id.values())[0]}]")
                            await self.bot.forward_messages(user, list(post_id.keys())[0], channel)
                            await self.bot.send_message(user, "Оцени", buttons=markup)
                            await insert_messages_score_db(uid, user, channel,
                                                           list(post_id.keys())[0], list(post_id.values())[0])
                        if not data:
                            data = {
                                channel: {
                                    "ts": datetime.now().isoformat(sep=" "),
                                    "post_ids": [
                                        {
                                            list(post.keys())[0]: await unmatch_topic_name(post[list(post.keys())[0]])}
                                        for post in post_ids
                                    ]
                                }
                            }
                        else:
                            data.update(
                                {
                                    channel: {
                                        "ts": datetime.now().isoformat(sep=" "),
                                        "post_ids": [
                                            {
                                                list(post.keys())[0]: await unmatch_topic_name(post[list(post.keys())[0]])}
                                            for post in post_ids
                                        ]
                                    }
                                }
                            )
                    else:
                        # pass
                        await self.bot.send_message(user, "По выбранным темам ничего не нашлось :(")
                if [item for sublist in list(data.values()) for item in sublist]:
                    await update_send_messages_db(user, data)
        return
