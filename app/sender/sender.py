import sys
import os

sys.path.append(os.path.dirname(__file__))
sys.path.insert(1, os.path.realpath(os.path.pardir))

import uuid
import re

from app.db.db import *
from app.news.news import News
from app.tools.prepare_data import prepare_data, get_pred_labels, check_keywords
from app.tools.tools import match_topics_name, get_estimate_markup, \
    unmatch_topic_name, model_predict, get_model_summary, get_emoji_topics
from datetime import datetime


class Sender:
    def __init__(self, client, bot):
        self.client = client
        self.bot = bot


    @staticmethod
    async def generate_last_msg_users(user_last_messages: dict) -> dict:
        """Returns the ids of the last N posts from the channel for subsequent sending"""

        channels = dict()

        for channel, post_id in user_last_messages.items():
            channels[channel] = post_id

        return channels

    @staticmethod
    async def generate_message_to_send(form):
        """Generation of messages to send to the user"""

        news_bucket = dict()

        for channel, messages in form.items():
            channel_messages = list()
            for message in messages:
                channel_messages.append(list(message.keys())[0])
            news_bucket[channel] = channel_messages

        channel_summary = dict()
        for channel, messages in news_bucket.items():
            result = list()
            if messages:
                for message in messages:
                    if len(message.split(" ")) > 10:
                        summary_result = await get_model_summary(message)
                        if len(message.split(" ")) > 8:
                            result.append(summary_result)
            channel_summary[channel] = result

        sent_messages = dict()

        for channel, summary_text in channel_summary.items():
            format_text = "\n"
            for text in summary_text:
                text = text.split("\n")[0]
                if len(text.split(" ")) > 5:
                    format_text += "🟣 " + text + "\n\n"
                    sent_messages[channel] = format_text
                else:
                    pass
        return sent_messages

    async def generate_format_message_to_send(self, user_id: int, user_channels: list, user_topics: list,
                                       last_msg_users: dict, is_summary: bool) -> dict:
        """ Generating a message with aggregated posts for a user"""

        form = dict()
        channel_last_posts_log = dict()
        topics_filter_posts = 0
        keywords_filter_posts = 0

        for channel in user_channels:
            print("channel", channel)
            posts = list()
            channel_id = await get_channel_id_by_name_db(channel)
            news = News(self.client)
            if channel in last_msg_users.keys():
                print("if channel in last_msg_users.keys():")
                print("last_msg_users[channel]", last_msg_users[channel])
                result = await news.get_sender_posts(channel_id=channel_id, channel_name=channel,
                                                     min_id=last_msg_users[channel], is_first=False)
                print("result", result)
            else:
                result = await news.get_sender_posts(channel_id=channel_id, channel_name=channel,
                                                     min_id=0, is_first=True)
                print("else result", result)
            clean_messages = await prepare_data(result["message"])
            print("clean_messages", clean_messages)
            preds = await model_predict(clean_messages)
            print("preds", preds)
            labels = await get_pred_labels(preds)
            print("labels", labels)

            if result["id"]:
                print("if result[id]:")
                # if channel not in last_msg_users.keys():
                max_post_id = max(result["id"])
                channel_last_posts_log[channel] = max_post_id
                print("channel_last_posts_log", channel_last_posts_log)
            else:
                max_post_id = last_msg_users[channel]
                channel_last_posts_log[channel] = max_post_id
            # else:
            #     pass

            if is_summary:
                for idx, (label, post) in enumerate(zip(labels, result["id"])):
                    if label not in user_topics:
                        topics_filter_posts += 1
                    if await check_keywords(user_id, clean_messages[idx]):
                        keywords_filter_posts += 1
                    if label in user_topics and post not in [list(k.keys())[0] for k in posts] \
                            and not await check_keywords(user_id, clean_messages[idx]):
                        label_ru = await match_topics_name([label])
                        posts.append({result["message"][idx]: label_ru[0]})
                form[channel] = posts
            else:
                is_summary = False
                for idx, (label, post) in enumerate(zip(labels, result["id"])):
                    if label not in user_topics:
                        topics_filter_posts += 1
                    if await check_keywords(user_id, clean_messages[idx]):
                        keywords_filter_posts += 1
                    if label in user_topics and post not in [list(k.keys())[0] for k in posts] \
                            and not await check_keywords(user_id, clean_messages[idx]):
                        label_ru = await match_topics_name([label])
                        posts.append({post: label_ru[0]})
                form[channel] = posts
        await update_stat_db(user_id, topics_filter_posts, keywords_filter_posts)

        if form:
            print("if form:!!!!!!!!")
            await update_user_last_post_db(user_id, channel_last_posts_log)
        return form

    async def send_aggregate_news(self, user_id: int, user_channels: list,
                                  user_topics: list, is_summary: bool):
        """Sending a message to a user with aggregated / summarized posts"""

        user_last_messages = await get_user_last_post_db(user_id)
        print("user_last_messages", user_last_messages)

        if is_summary:
            form = await self.generate_format_message_to_send(user_id, user_channels,
                                                              user_topics, user_last_messages, True)
            uid = uuid.uuid4()
            markup = self.bot.build_reply_markup(await get_estimate_markup(uid))
            sent_messages = await self.generate_message_to_send(form)
            print("sent_messages", sent_messages)
            if sent_messages:
                sent_limit = 0
                for channel, text in sent_messages.items():
                    sent_text = f"Суммаризация из канала: @{channel}\n" + text + "\n\n"
                    if sent_limit < 5:
                        await self.bot.send_message(user_id, sent_text, silent=True)
                        sent_limit += 1
                await self.bot.send_message(user_id, "Буду рад оценке 🐱", buttons=markup, silent=True)
                await update_stat_use_db(user_id, is_summary=True, is_sent=True)
                await insert_messages_score_db(uid, user_id, "_summary", 0, "")
            else:
                sent_text = "Из свеженького по выбранным темам ничего не нашлось!"
                await self.bot.send_message(user_id, sent_text, silent=True)
                await update_stat_use_db(user_id, is_summary=True, is_sent=False)
        else:
            form = await self.generate_format_message_to_send(user_id, user_channels, user_topics,
                                                              user_last_messages, False)
            print("form", form)
            num_of_channels = len(user_channels)
            print("num_of_channels", num_of_channels)
            sent_limit = 0
            for channel, post_ids in form.items():
                print("channel", channel)
                data = dict()
                if post_ids:
                    for post_id in post_ids:
                        if sent_limit < 50:
                            uid = uuid.uuid4()
                            markup = self.bot.build_reply_markup(await get_estimate_markup(uid))
                            await self.bot.send_message(user_id, await get_emoji_topics(list(post_id.values())[0]),
                                                        silent=True)
                            await self.bot.forward_messages(user_id, list(post_id.keys())[0], channel, silent=True)
                            await self.bot.send_message(user_id, "Буду рад оценке 🐱", buttons=markup, silent=True)
                            await insert_messages_score_db(uid, user_id, channel,
                                                           list(post_id.keys())[0], list(post_id.values())[0])
                            sent_limit += 1

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
                        if [item for sublist in list(data.values()) for item in sublist]:
                            await update_send_messages_db(user_id, data)
                else:
                    num_of_channels -= 1
            if num_of_channels == 0:
                await self.bot.send_message(user_id, "По выбранным темам ничего не нашлось 🤐", silent=True)
                await update_stat_use_db(user_id, is_summary=False, is_sent=False)
            else:
                await update_stat_use_db(user_id, is_summary=False, is_sent=True)
        return
