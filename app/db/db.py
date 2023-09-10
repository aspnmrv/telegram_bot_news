import os
import sys

sys.path.append(os.path.dirname(__file__))
sys.path.insert(1, os.path.realpath(os.path.pardir))

from psycopg2 import pool
from app.globals import MINCONN, MAXCONN
from datetime import datetime

import psycopg2
import json


# For a stable connection to database
def connect_from_config(file):
    keepalive_kwargs = {
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 5,
        "keepalives_count": 5,
    }
    with open(file, 'r') as fp:
        config = json.load(fp)
        print("config", config)
    return psycopg2.connect(**config, **keepalive_kwargs)


def create_pool_from_config(minconn, maxconn, file):
    with open(file, 'r') as fp:
        config = json.load(fp)
    return pool.SimpleConnectionPool(minconn, maxconn, **config)


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
GLOBAL_POOL = create_pool_from_config(MINCONN, MAXCONN, CONFIG_PATH)


def reconnect():
    """"""
    global CONN_GLOBAL
    if CONN_GLOBAL.closed == 1:
        CONN_GLOBAL = connect_from_config(CONFIG_PATH)


async def is_exist_temp_db(table_name: str, user_id: int, field: str = "user_id") -> bool:
    """Check exist value in table"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            {field}
        FROM {table_name}
        WHERE {field} = {user_id}
    """
    cur.execute(query)
    data = cur.fetchall()
    GLOBAL_POOL.putconn(conn)
    if data:
        return True
    else:
        return False


async def is_user_exist_db(user_id: int) -> bool:
    """Check exist user_id in database"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            id
        FROM public.users
        WHERE id = {user_id}
    """
    cur.execute(query)
    data = cur.fetchall()
    GLOBAL_POOL.putconn(conn)
    if data:
        return True
    else:
        return False


async def update_data_users_db(data) -> None:
    """"""
    id = data.id
    first_name = data.first_name
    last_name = data.last_name
    is_bot = data.bot
    premium = data.premium
    username = data.username
    lang = data.lang_code
    created_at = datetime.now()

    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        INSERT INTO public.users (id, created_at, first_name, last_name, is_bot, premium, username, lang)
        VALUES ({id}, '{created_at}', '{first_name}', '{last_name}', {is_bot}, {premium}, '{username}', '{lang}')
    """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def get_user_topics_db(user_id):
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            topics
        FROM public.user_topics
        WHERE user_id = {user_id}
    """
    cur.execute(query)
    data = cur.fetchall()
    GLOBAL_POOL.putconn(conn)
    if data:
        return data[0][0]
    else:
        return []


async def update_data_topics_db(user_id, topics) -> None:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            user_id
        FROM public.user_topics
        WHERE user_id = {user_id}
    """
    cur.execute(query)
    df = cur.fetchall()
    if df:
        created_at = datetime.now()
        query = f"""
            UPDATE public.user_topics
            SET topics = ARRAY{topics}, updated_at = '{created_at}'
            WHERE user_id = {user_id}
        """
    else:
        created_at = datetime.now()
        query = f"""
            INSERT INTO public.user_topics (user_id, updated_at, topics)
            VALUES ({user_id}, '{created_at}', ARRAY{topics})
        """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def update_user_keywords_db(user_id, keywords) -> None:
    """"""
    created_at = datetime.now()
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            user_id
        FROM public.user_keywords
        WHERE user_id = {user_id}
    """
    cur.execute(query)
    data = cur.fetchall()
    if data:
        query = f"""
            UPDATE public.user_keywords
            SET keywords = ARRAY{keywords}
            WHERE user_id = {user_id}
        """
    else:
        query = f"""
            INSERT INTO public.user_keywords (user_id, updated_at, keywords)
            VALUES ({user_id}, '{created_at}', ARRAY{keywords})
        """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def get_user_keywords_db(user_id):
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            keywords
        FROM public.user_keywords
        WHERE user_id = {user_id}
    """
    cur.execute(query)
    data = cur.fetchall()
    GLOBAL_POOL.putconn(conn)
    if data:
        return data[0][0]
    else:
        return []


async def update_user_channels_db(user_id, channel) -> None:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            user_id
        FROM public.user_channels
        WHERE user_id = {user_id}
    """
    cur.execute(query)
    df = cur.fetchall()
    if df:
        created_at = datetime.now()
        query = f"""
            INSERT INTO public.user_channels (user_id, created_at, channel)
            VALUES ({user_id}, '{created_at}', '{channel}')
        """
    else:
        created_at = datetime.now()
        query = f"""
            INSERT INTO public.user_channels (user_id, created_at, channel)
            VALUES ({user_id}, '{created_at}', '{channel}')
        """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def get_user_channels_db(user_id):
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            array_agg(channel) as channels
        FROM public.user_channels
        WHERE user_id = {user_id}
        GROUP BY user_id
    """
    cur.execute(query)
    data = cur.fetchall()
    GLOBAL_POOL.putconn(conn)
    if data:
        return data[0][0]
    else:
        return []


async def get_data_channels_db(user_id):
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            array_agg(distinct channel) as channels
        FROM public.user_channels
        WHERE user_id = {user_id}
        GROUP BY user_id
    """
    cur.execute(query)
    data = cur.fetchall()
    GLOBAL_POOL.putconn(conn)
    if data:
        return data[0][0]
    else:
        return []


async def update_data_events_db(user_id, event, params) -> None:
    """"""
    created_at = datetime.now()
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        INSERT INTO public.events (user_id, created_at, event, params)
        VALUES ({user_id}, '{created_at}', '{event}', '{json.dumps(params)}')
    """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def remove_from_db(table_name, user_id) -> None:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        DELETE FROM public.{table_name}
        WHERE user_id = {user_id}
    """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def update_send_messages_db(user_id, data) -> None:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            user_id
        FROM public.send_messages
        WHERE user_id = {user_id}
    """
    cur.execute(query)
    df = cur.fetchall()
    if df:
        query = f"""
             UPDATE public.send_messages
             SET data = '{json.dumps(data)}'
             WHERE user_id = {user_id}
         """
    else:
        created_at = datetime.now()
        query = f"""
            INSERT INTO public.send_messages (user_id, created_at, data)
            VALUES ({user_id}, '{created_at}', '{json.dumps(data)}')
        """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def update_user_last_post_db(user_id, data):
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    created_at = datetime.now()
    query = f"""
        SELECT
            user_id
        FROM public.user_last_post
        WHERE user_id = {user_id}
    """
    cur.execute(query)
    df = cur.fetchall()
    if df:
        query = f"""
             UPDATE public.user_last_post
             SET data = '{json.dumps(data)}',
             updated_at = '{created_at}'
             WHERE user_id = {user_id}
         """
    else:
        query = f"""
            INSERT INTO public.user_last_post (user_id, updated_at, data)
            VALUES ({user_id}, '{created_at}', '{json.dumps(data)}')
        """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def get_user_last_post_db(user_id):
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            data
        FROM user_last_post
        where user_id = {user_id}
    """
    cur.execute(query)
    data = cur.fetchall()
    conn.commit()
    GLOBAL_POOL.putconn(conn)

    return data[0][0] if data else {}


async def insert_messages_score_db(uuid, user_id, channel, post_id, topic) -> None:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    created_at = datetime.now()
    query = f"""
        INSERT INTO public.send_messages_scores (uuid, created_at, user_id, channel, post_id, topic)
        VALUES ('{uuid}', '{created_at}', {user_id}, '{channel}', {post_id}, '{topic}')
    """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def insert_score_db(uuid, score) -> None:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    created_at = datetime.now()
    query = f"""
        INSERT INTO public.messages_scores (uuid, score, created_at)
        VALUES ('{uuid}', {score}, '{created_at}')
    """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def get_stat_topics_db():
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            user_id,
            unnest(topics) as topic
        FROM public.user_topics
        GROUP BY user_id
    """
    cur.execute(query)
    data = cur.fetchall()
    GLOBAL_POOL.putconn(conn)
    if data:
        return data
    else:
        return -1


async def get_stat_keywords_db():
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            keyword,
            count(distinct user_id) as users
        FROM (
            SELECT
                user_id,
                unnest(keywords) as keyword
            FROM public.user_keywords
            GROUP BY user_id
        ) AS subq
        GROUP BY keyword
        ORDER BY users DESC
        LIMIT 8
    """
    cur.execute(query)
    data = cur.fetchall()
    GLOBAL_POOL.putconn(conn)

    return data


async def update_stat_db(user_id, topic_filter_posts, keywords_filter_posts) -> None:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    created_at = datetime.now()
    query = f"""
        INSERT INTO public.stat_info (user_id, created_at, topics_filter_posts, keywords_filter_posts)
        VALUES ({user_id}, '{created_at}', {topic_filter_posts}, {keywords_filter_posts})
    """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def update_stat_use_db(user_id, is_summary, is_sent) -> None:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    created_at = datetime.now()
    query = f"""
        INSERT INTO public.stat_uses (user_id, created_at, is_summary, is_sent)
        VALUES ({user_id}, '{created_at}', {is_summary}, {is_sent})
    """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def get_stat_use_db(user_id) -> None:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    date = datetime.today().strftime("%Y-%m-%d")
    query = f"""
        SELECT
            count(*) as cnt
        FROM public.stat_uses
        WHERE user_id = {user_id}
            and created_at::date = '{date}'
    """
    cur.execute(query)
    data = cur.fetchall()
    conn.commit()
    GLOBAL_POOL.putconn(conn)

    return data[0][0] if data else None


async def get_stat_filter_db(user_id) -> None:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            sum(topics_filter_posts) as topics_filter_posts,
            sum(keywords_filter_posts) as keywords_filter_posts
        FROM public.stat_info
        WHERE user_id = {user_id}
            and created_at::date >= (now() - interval '30 days')
    """
    cur.execute(query)
    data = cur.fetchall()
    conn.commit()
    GLOBAL_POOL.putconn(conn)

    return data if data else None


async def get_stat_popular_db(user_id) -> None:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            sum(topics_filter_posts) as topics_filter_posts,
            sum(keywords_filter_posts) as keywords_filter_posts
        FROM public.stat_uses
        WHERE user_id = {user_id}
            and created_at::date >= (now() - interval '7 day')
    """
    cur.execute(query)
    data = cur.fetchall()
    conn.commit()
    GLOBAL_POOL.putconn(conn)

    return data if data else None


async def update_channel_info_db(channel_id, channel_name) -> None:
    """"""
    created_at = datetime.now()
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
         UPDATE public.channels
         SET username = '{channel_name}',
         updated_at = '{created_at}'
         WHERE channel_id = '{channel_id}'
     """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def insert_channel_info_db(channel_id, channel_name) -> None:
    """"""
    created_at = datetime.now()
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        INSERT INTO public.channels (channel_id, username, created_at, updated_at)
        VALUES ('{channel_id}', '{channel_name}', '{created_at}', '{created_at}')
    """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def check_channel_info_db(channel_id) -> tuple or bool:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            channel_id,
            username
        FROM public.channels
        WHERE channel_id = '{channel_id}'
    """
    cur.execute(query)
    data = cur.fetchall()

    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return data if data else False


async def insert_channel_entity_db(channel_id, access_hash) -> None:
    """"""
    created_at = datetime.now()
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        INSERT INTO public.channels_entity (channel_id, access_hash, created_at, updated_at)
        VALUES ('{channel_id}', {access_hash}, '{created_at}', '{created_at}')
    """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def update_channel_entity_db(channel_id, access_hash) -> None:
    """"""
    created_at = datetime.now()
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
                 UPDATE public.channels_entity
                 SET access_hash = {access_hash},
                 updated_at = '{created_at}'
                 WHERE channel_id = '{channel_id}'
             """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def check_channel_entity_db(channel_id) -> tuple or bool:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            access_hash
        FROM public.channels_entity
        WHERE channel_id = '{channel_id}'
    """
    cur.execute(query)
    data = cur.fetchall()

    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return data if data else False


async def get_channel_id_by_name_db(channel_name) -> tuple or bool:
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            channel_id
        FROM public.channels
        WHERE username = '{channel_name}'
    """
    cur.execute(query)
    data = cur.fetchall()

    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return data[0][0] if data else False


async def insert_internal_info_db(action_type, func_name, is_exist, user_id=0) -> None:
    """"""
    created_at = datetime.now()
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        INSERT INTO public.internal_info (created_at, user_id, type, is_exist, func)
        VALUES ('{created_at}', {user_id}, {action_type}, {is_exist}, '{func_name}')
    """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def get_event_from_db(user_id, event):
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            max(created_at) as created_at
        FROM events
        WHERE user_id = {user_id}
            AND event = '{event}'
    """
    cur.execute(query)
    data = cur.fetchall()
    conn.commit()
    GLOBAL_POOL.putconn(conn)

    return data[0][0] if data else None


async def get_user_for_notify_db():
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            array_agg(id)
        FROM public.users
        WHERE id in (1167990839, 288939647, 123480322, 85544995, 267560138, 1233172454, 1193478)
    """
    cur.execute(query)
    data = cur.fetchall()
    GLOBAL_POOL.putconn(conn)
    if data:
        return data[0][0]
    else:
        return None


async def update_chats_db(user_id, chat_id):
    """"""
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    created_at = datetime.now()
    query = f"""
        SELECT
            user_id
        FROM public.users_chats
        WHERE user_id = {user_id}
    """
    cur.execute(query)
    df = cur.fetchall()
    if df:
        query = f"""
             UPDATE public.users_chats
             SET chat_id = {created_at},
             updated_at = '{created_at}'
             WHERE user_id = {user_id}
         """
    else:
        query = f"""
            INSERT INTO public.users_chats (user_id, updated_at, chat_id)
            VALUES ({user_id}, '{created_at}', {chat_id})
        """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None
