import logging
import os

LOG_FILE = os.path.join(os.path.dirname(__file__), "bot.log")

# Настраиваем глобальный логгер
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# По желанию: можно вернуть логгер, если хочешь единообразия
logger = logging.getLogger("bot")
