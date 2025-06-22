import asyncio
import aiohttp
import json
from typing import Optional
from logger import logger
import redis
from config import REDIS_HOST, REDIS_PORT, REDIS_DB

# Создаем подключение к Redis для кеширования
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

# Статусы, которые разрешают доступ к боту
ALLOWED_STATUSES = {"creator", "administrator", "member"}

# Время жизни кеша в секундах (10 минут)
CACHE_TTL = 600

async def check_channel_subscription(bot_token: str, channel_id: str, user_id: int) -> bool:
    """
    Проверяет подписку пользователя на канал через Telegram Bot API.
    
    Args:
        bot_token: Токен Telegram бота
        channel_id: ID канала (например, @logloss_notes)
        user_id: ID пользователя Telegram
        
    Returns:
        bool: True если пользователь подписан на канал, False иначе
    """
    # Проверяем кеш
    cache_key = f"subscription:{user_id}"
    try:
        cached_result = redis_client.get(cache_key)
        if cached_result is not None:
            logger.info(f"[Subscription] Cache hit for user {user_id}: {cached_result}")
            return cached_result.lower() == "true"
    except Exception as e:
        logger.warning(f"[Subscription] Redis cache error for user {user_id}: {e}")
    
    # Выполняем запрос к API
    url = f"https://api.telegram.org/bot{bot_token}/getChatMember"
    params = {
        "chat_id": channel_id,
        "user_id": user_id
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # Таймаут 10 секунд
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        member_status = data.get("result", {}).get("status")
                        is_subscribed = member_status in ALLOWED_STATUSES
                        
                        logger.info(f"[Subscription] User {user_id} status in channel: {member_status}, allowed: {is_subscribed}")
                        
                        # Кешируем результат
                        try:
                            redis_client.setex(cache_key, CACHE_TTL, "true" if is_subscribed else "false")
                        except Exception as e:
                            logger.warning(f"[Subscription] Failed to cache result for user {user_id}: {e}")
                        
                        return is_subscribed
                    else:
                        error_description = data.get("description", "Unknown error")
                        logger.warning(f"[Subscription] API error for user {user_id}: {error_description}")
                        
                        # Если пользователь не найден в канале, считаем что не подписан
                        if "user not found" in error_description.lower() or "bad request" in error_description.lower():
                            try:
                                redis_client.setex(cache_key, CACHE_TTL, "false")
                            except Exception as e:
                                logger.warning(f"[Subscription] Failed to cache negative result for user {user_id}: {e}")
                            return False
                        
                        # Для других ошибок не кешируем и возвращаем False
                        return False
                else:
                    logger.error(f"[Subscription] HTTP error {response.status} for user {user_id}")
                    return False
                    
    except asyncio.TimeoutError:
        logger.error(f"[Subscription] Timeout checking subscription for user {user_id}")
        return False
    except aiohttp.ClientError as e:
        logger.error(f"[Subscription] Network error checking subscription for user {user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"[Subscription] Unexpected error checking subscription for user {user_id}: {e}")
        return False

async def clear_subscription_cache(user_id: int) -> bool:
    """
    Очищает кеш подписки для конкретного пользователя.
    
    Args:
        user_id: ID пользователя Telegram
        
    Returns:
        bool: True если кеш был успешно очищен
    """
    cache_key = f"subscription:{user_id}"
    try:
        result = redis_client.delete(cache_key)
        logger.info(f"[Subscription] Cache cleared for user {user_id}")
        return bool(result)
    except Exception as e:
        logger.error(f"[Subscription] Failed to clear cache for user {user_id}: {e}")
        return False

def get_subscription_cache_info(user_id: int) -> Optional[dict]:
    """
    Получает информацию о кешированном статусе подписки.
    
    Args:
        user_id: ID пользователя Telegram
        
    Returns:
        dict: Информация о кеше или None если кеш пуст
    """
    cache_key = f"subscription:{user_id}"
    try:
        value = redis_client.get(cache_key)
        ttl = redis_client.ttl(cache_key)
        
        if value is not None:
            return {
                "user_id": user_id,
                "subscribed": value.lower() == "true",
                "ttl_seconds": ttl if ttl > 0 else 0
            }
        return None
    except Exception as e:
        logger.error(f"[Subscription] Failed to get cache info for user {user_id}: {e}")
        return None 