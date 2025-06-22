import os
from dotenv import load_dotenv

load_dotenv()  # Загружаем .env один раз — сразу при импорте config

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")  # заранее созданный ассистент

# Канал для проверки подписки
CHANNEL_ID = os.getenv("CHANNEL_ID", "@logloss_notes")  # ID канала по умолчанию

# Список разрешённых Telegram ID (резервный механизм)
# ALLOWED_USERS = [792501309, 916387745, 2120274462]  # Закомментировано - теперь используем проверку подписки

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
REDIS_DB = int(os.getenv("REDIS_DB"))

# Настройки для аналитики пользователей
ANALYTICS_DB_PATH = os.getenv("ANALYTICS_DB_PATH", "./data/user_analytics.db")