import ast
import sqlite3
import json
import os

from pathlib import Path

DB_PATH = Path(__file__).parent.parent.resolve() / "data"
CONN = sqlite3.connect(DB_PATH / "sophie.db")


async def _create_db():
    """"""
    cur = CONN.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_step_states
              (user_id INT, step INT)
        """
    )
    CONN.commit()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_topics_temp
              (user_id INT, topics TEXT)
        """
    )
    CONN.commit()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_states_temp
              (user_id INT, states TEXT)
        """
    )
    CONN.commit()
    return


async def _get_user_states(user_id, field):
    """"""
    cur = CONN.cursor()
    if field == "topics":
        query = f"""
            SELECT
                topics
            FROM user_topics_temp
            WHERE user_id = {user_id}
        """
    else:
        query = f"""
            SELECT
                states
            FROM user_states_temp
            WHERE user_id = {user_id}
        """
    cur.execute(query)
    data = cur.fetchall()
    CONN.commit()
    data = ast.literal_eval(data[0][0])

    return data if data else []


async def _update_user_states(user_id, field, data):
    """"""
    data = json.dumps(data)
    cur = CONN.cursor()
    if field == "topics":
        query = f"""
            SELECT
                user_id
            FROM user_topics_temp
            WHERE user_id = {user_id}
        """
        cur.execute(query)
        result = cur.fetchall()
        if result:
            query = f"""
                UPDATE user_topics_temp
                SET topics = '{data}'
                WHERE user_id = {user_id}
            """
        else:
            query = f"""
                INSERT INTO user_topics_temp (user_id, topics) 
                VALUES ({user_id}, '{data}') 
            """
    else:
        query = f"""
            SELECT
                user_id
            FROM user_states_temp
            WHERE user_id = {user_id}
        """
        cur.execute(query)
        result = cur.fetchall()
        if result:
            query = f"""
                UPDATE user_states_temp
                SET states = '{data}'
                WHERE user_id = {user_id}
            """
        else:
            query = f"""
                INSERT INTO user_states_temp (user_id, states) 
                VALUES ({user_id}, '{data}') 
            """
    cur.execute(query)
    CONN.commit()
    return


async def _get_current_user_step(user_id):
    cur = CONN.cursor()
    query = f"""
        SELECT
            step
        FROM user_step_states
        WHERE user_id = {user_id}
    """
    cur.execute(query)
    data = cur.fetchall()
    CONN.commit()

    return int(data[0][0])


async def _truncate_table():
    cur = CONN.cursor()
    query = f"""
        DELETE FROM user_step_states
    """
    cur.execute(query)
    CONN.commit()
    return


async def _update_current_user_step(user_id: int, step: int):
    cur = CONN.cursor()
    query = f"""
        SELECT
            step
        FROM user_step_states
        WHERE user_id = {user_id}
    """
    cur.execute(query)
    data = cur.fetchall()

    if len(data) == 0:
        query = f"""
            INSERT INTO user_step_states
            (user_id, step) VALUES ({user_id}, {step})
        """
        cur.execute(query)
        CONN.commit()
    else:
        query = f"""
            UPDATE user_step_states
            SET step = {step}
            WHERE user_id = {user_id}
        """
        cur.execute(query)
        CONN.commit()
    return
