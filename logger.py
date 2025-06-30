import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging with daily rotation and httpx filtering
def setup_logging():
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Create daily rotating file handler
    log_filename = os.path.join(LOGS_DIR, "bot.log")
    file_handler = TimedRotatingFileHandler(
        log_filename,
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding='utf-8',
        utc=False
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Add our handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Disable httpx logging (used by python-telegram-bot)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Disable other noisy loggers
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    return logging.getLogger("bot")

# Initialize logging
logger = setup_logging()
