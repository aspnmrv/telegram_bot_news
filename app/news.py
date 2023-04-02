import requests
import time
import config

from telethon.tl.functions.messages import GetHistoryRequest


bot_api = config.bot_api


class News:
    def __init__(self, client):
        self.client = client

    @staticmethod
    async def get_channel_info(forward_channel_id):
        """"""
        time.sleep(2)
        channel_info = requests.get(
            f"https://api.telegram.org/{bot_api}/getChat?chat_id={forward_channel_id}"
        ).json()

        return channel_info

    async def get_history_channel(self, channel_entity, offset_id=0, limit=100, offset_date=None):
        """"""
        time.sleep(1)
        posts = await self.client(
            GetHistoryRequest(
                peer=channel_entity,
                offset_id=offset_id,
                limit=limit,
                offset_date=offset_date,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            )
        )
        return posts

    async def get_posts(self, channel_id, offset_id=0, limit=100):
        """"""
        time.sleep(1)
        channel_info = await self.get_channel_info(channel_id)
        username_forward_channel = channel_info["result"]["username"]
        time.sleep(3)
        channel_entity = await self.client.get_entity(username_forward_channel)

        posts = await self.get_history_channel(channel_entity, offset_id, limit)

        return posts

    @staticmethod
    async def build_news_bucket(content):
        """"""
        result = {
            "id": [],
            "message": [],
            "date": [],
            "is_post": [],
            "is_fwd_from": [],
            "views": [],
            "forwards": [],
            "reactions": []
        }

        for obj in content:
            for post in obj.messages:
                if post.message:
                    result["message"].append(post.message)
                    result["id"].append(post.id)
                    result["date"].append(post.date)
                    result["is_post"].append(post.post)
                    result["is_fwd_from"].append(post.fwd_from)
                    result["views"].append(post.views)
                    result["forwards"].append(post.forwards)
                    reactions_list = []
                    if post.reactions:
                        for i in range(len(post.reactions.results)):
                            reactions_list.append((post.reactions.results[i].reaction, post.reactions.results[i].count))
                    result["reactions"].append(reactions_list)

        return result

    async def get_news(self, posts, num_dozen, forward_channel_id):
        """"""
        last_post_id = posts.messages[-1].id
        any_posts = list()

        for _ in range(num_dozen):
            time.sleep(2)
            new_posts = await self.get_posts(forward_channel_id, offset_id=last_post_id, limit=100)
            any_posts.append(new_posts)
            last_post_id -= 100

        result = await self.build_news_bucket(any_posts)

        return result

    async def get_bucket_posts(self, num_dozen, channel_name):
        """"""
        any_posts = list()

        for _ in range(num_dozen):
            time.sleep(3)
            channel_entity = await self.client.get_entity(channel_name)
            new_posts = await self.get_history_channel(self.client, channel_entity, limit=10)
            any_posts.append(new_posts)

        result = await self.build_news_bucket(any_posts)

        return result

    async def get_sender_posts(self, channel_name, min_id=0, is_first=False):
        """"""
        time.sleep(3)
        channel_entity = await self.client.get_entity(channel_name)
        time.sleep(3)
        if not is_first:
            posts = await self.client(
                GetHistoryRequest(
                    peer=channel_entity,
                    offset_id=0,
                    limit=50,
                    offset_date=None,
                    max_id=0,
                    min_id=min_id,
                    add_offset=0,
                    hash=0
                )
            )
        else:
            posts = await self.client(
                GetHistoryRequest(
                    peer=channel_entity,
                    offset_id=0,
                    limit=10,
                    offset_date=None,
                    max_id=0,
                    min_id=0,
                    add_offset=0,
                    hash=0
                )
            )
        result = await self.build_news_bucket([posts])
        return result
