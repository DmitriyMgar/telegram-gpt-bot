import redis # type: ignore
from config import REDIS_HOST, REDIS_PORT, REDIS_DB
from logger import logger

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

SESSION_PREFIX = "thread_id:"
FILES_PREFIX = "user_files:"  # Новый префикс для файлов

def _key(user_id: int) -> str:
    return f"{SESSION_PREFIX}{user_id}"

def _files_key(user_id: int) -> str:
    return f"{FILES_PREFIX}{user_id}"

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

# === НОВЫЕ ФУНКЦИИ ДЛЯ ФАЙЛОВ ===
def add_user_file(user_id: int, file_id: str):
    """Добавляет file_id в список файлов пользователя"""
    try:
        r.sadd(_files_key(user_id), file_id)
        logger.debug(f"Added file {file_id} for user {user_id}")
    except Exception as e:
        logger.error(f"Redis error in add_user_file: {e}")

def get_user_files(user_id: int) -> list[str]:
    """Получает все file_id пользователя"""
    try:
        files = r.smembers(_files_key(user_id))
        return list(files) if files else []
    except Exception as e:
        logger.error(f"Redis error in get_user_files: {e}")
        return []

def clear_user_files(user_id: int):
    """Очищает список файлов пользователя"""
    try:
        r.delete(_files_key(user_id))
        logger.debug(f"Cleared files list for user {user_id}")
    except Exception as e:
        logger.error(f"Redis error in clear_user_files: {e}")

async def delete_user_files_from_openai(user_id: int):
    """Удаляет все файлы пользователя из OpenAI storage"""
    from openai import AsyncOpenAI
    from config import OPENAI_API_KEY
    
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    files_to_delete = get_user_files(user_id)
    
    if not files_to_delete:
        logger.debug(f"No files to delete for user {user_id}")
        return
    
    deleted_count = 0
    for file_id in files_to_delete:
        try:
            await client.files.delete(file_id)
            deleted_count += 1
            logger.debug(f"Deleted file {file_id} for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to delete file {file_id} for user {user_id}: {e}")
    
    # Очищаем список после удаления
    clear_user_files(user_id)
    logger.info(f"Deleted {deleted_count} files for user {user_id} on reset")

async def reset_thread(user_id: int):
    """Сбрасывает thread и удаляет все файлы пользователя"""
    try:
        # Удаляем файлы из OpenAI
        await delete_user_files_from_openai(user_id)
        
        # Удаляем thread_id
        r.delete(_key(user_id))
        
        logger.info(f"Reset complete for user {user_id}: thread and files cleared")
    except Exception as e:
        logger.error(f"Error in reset_thread: {e}")

# Оставляем синхронную версию для совместимости
def reset_thread_sync(user_id: int):
    """Синхронная версия сброса (только thread_id, без файлов)"""
    try:
        r.delete(_key(user_id))
    except Exception as e:
        logger.error(f"Redis error in reset_thread_sync: {e}")
