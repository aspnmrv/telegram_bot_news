import psycopg2
import json
import os
import pandas.io.sql as sqlio

from psycopg2 import pool
from globals import MINCONN, MAXCONN
from datetime import datetime


def connect_from_config(file):
    keepalive_kwargs = {
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 5,
        "keepalives_count": 5,
    }
    with open(file, 'r') as fp:
        config = json.load(fp)
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
        return -1


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
    df = cur.fetchall()
    if df:
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
        # query = f"""
        #     UPDATE public.user_channels
        #     SET channel = '{channel}'
        #     WHERE user_id = {user_id}
        # """
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


async def get_data_channels_db():
    """"""
    conn = GLOBAL_POOL.getconn()
    query = f"""
        SELECT
            user_id,
            array_agg(distinct channel) as channels
        FROM public.user_channels
        GROUP BY user_id
    """
    data = sqlio.read_sql_query(query, conn)
    GLOBAL_POOL.putconn(conn)
    if data.shape[0] > 0:
        users = data["user_id"]
        channels = data["channels"]
        result = dict()
        for user, channel in zip(users, channels):
            result[user] = channel
        return result
    else:
        return dict()


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
             SET data = '{json.dumps(data)}'
             WHERE user_id = {user_id}
         """
    else:
        query = f"""
            INSERT INTO public.user_last_post (user_id, data)
            VALUES ({user_id}, '{json.dumps(data)}')
        """
    cur.execute(query)
    conn.commit()
    GLOBAL_POOL.putconn(conn)
    return None


async def get_user_last_post_db():
    conn = GLOBAL_POOL.getconn()
    cur = conn.cursor()
    query = f"""
        SELECT
            user_id,
            data
        FROM user_last_post
    """
    cur.execute(query)
    data = cur.fetchall()
    conn.commit()
    GLOBAL_POOL.putconn(conn)

    return data


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
