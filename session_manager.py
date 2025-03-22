import redis # type: ignore
from config import REDIS_HOST, REDIS_PORT, REDIS_DB
from logger import logger

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

SESSION_PREFIX = "thread_id:"

def _key(user_id: int) -> str:
    return f"{SESSION_PREFIX}{user_id}"

def get_thread_id(user_id: int) -> str | None:
    try:
        return r.get(_key(user_id))
    except Exception as e:
        logger.error(f"Redis error in get_thread_id: {e}")
        return None

def set_thread_id(user_id: int, thread_id: str):
    try:
        r.set(_key(user_id), thread_id)
    except Exception as e:
        logger.error(f"Redis error in set_thread_id: {e}")

def reset_thread(user_id: int):
    try:
        r.delete(_key(user_id))
    except Exception as e:
        logger.error(f"Redis error in reset_thread: {e}")
