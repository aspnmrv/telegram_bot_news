import sys
import os

sys.path.append(os.path.dirname(__file__))
sys.path.insert(1, os.path.realpath(os.path.pardir))
print("news")
import requests
import config
import asyncio

from app.db.db import check_channel_entity_db, insert_channel_entity_db, \
    check_channel_info_db, insert_channel_info_db, insert_internal_info_db
print("news2")
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import InputPeerChannel


bot_api = config.bot_api


class News:
    def __init__(self, client):
        self.client = client

    @staticmethod
    async def get_channel_info(channel_id: int) -> str:
        """
        Returns the username of the channel by the channel id after calling the api
        """
        await asyncio.sleep(7)
        check_channel_exist = await check_channel_info_db(str(channel_id))
        print("check_channel_exist", check_channel_exist)
        if not check_channel_exist:
            channel_info = requests.get(
                f"https://api.telegram.org/{bot_api}/getChat?chat_id={channel_id}"
            ).json()
            print("channel_info", channel_info)
            username_channel = channel_info["result"]["username"]
            print("username_channel", username_channel)
            await insert_internal_info_db(1, "get_channel_info", False)
            await insert_channel_info_db(channel_id, username_channel)
        else:
            username_channel = await check_channel_info_db(str(channel_id))
            username_channel = username_channel[0][1]
            await insert_internal_info_db(1, "get_channel_info", True)

        return username_channel if username_channel else None

    async def get_channel_entity(self, channel_id: str, channel_name: str) -> InputPeerChannel:
        """
        Returns the entity of the channel by username after calling the client api
        """
        await asyncio.sleep(7)
        if channel_id:
            channel_id = int(channel_id[4:])
            # Checking for the existence of an entity in the database
            check_channel_entity = await check_channel_entity_db(channel_id)
            # If entity does not exist, we make an appeal to the api
            if not check_channel_entity:
                channel_entity = await self.client.get_entity(channel_name)
                id = channel_entity.id
                hash = channel_entity.access_hash
                entity = InputPeerChannel(id, hash)
                await insert_channel_entity_db(id, hash)
                await insert_internal_info_db(3, "get_channel_entity", False)
            # If entity already exists, take the entity from the database
            else:
                access_hash = int(check_channel_entity[0][0])
                entity = InputPeerChannel(channel_id, access_hash)
                await insert_internal_info_db(3, "get_channel_entity", True)
        else:
            channel_entity = await self.client.get_entity(channel_name)
            id = channel_entity.id
            hash = channel_entity.access_hash
            entity = InputPeerChannel(id, hash)
            check_channel_entity = await check_channel_entity_db(channel_id)
            await insert_internal_info_db(3, "get_channel_entity", False)

            # If the entity was not yet in the database, add data about the entity
            if not check_channel_entity:
                await insert_channel_entity_db(id, hash)
        await asyncio.sleep(3)

        return entity

    @staticmethod
    async def build_news_bucket(content: list) -> dict:
        """Formation of a dictionary with posts in the required format with post parameters"""

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

    async def get_sender_posts(self, channel_id: str, channel_name: str,
                               min_id: int = 0, is_first: bool = False) -> dict:
        """Generate last N posts from channel in dictionary format"""

        print("get_sender_posts")
        await asyncio.sleep(6)
        channel_entity = await self.get_channel_entity(channel_id, channel_name)
        print("channel_entity", channel_entity)
        await insert_internal_info_db(2, "get_sender_posts", True)
        await asyncio.sleep(3)
        if not is_first:
            posts = await self.client(
                GetHistoryRequest(
                    peer=channel_entity,
                    offset_id=0,
                    limit=20,
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
                    limit=30,
                    offset_date=None,
                    max_id=0,
                    min_id=0,
                    add_offset=0,
                    hash=0
                )
            )
        result = await self.build_news_bucket([posts])

        return result
