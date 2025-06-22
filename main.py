from logger import logger
import os
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN, CHANNEL_ID
from openai_handler import send_message_and_get_response, get_message_history, export_message_history
from session_manager import reset_thread
from telegram.constants import ChatAction
from subscription_checker import check_channel_subscription
from user_analytics import analytics

# Путь до лог-файла
LOG_FILE = os.path.join(os.path.dirname(__file__), "bot.log")

def get_username(update: Update) -> str:
    """
    Получает имя пользователя для записи в аналитику.
    
    Args:
        update: Telegram Update объект
        
    Returns:
        str: Имя пользователя или fallback значение
    """
    user = update.effective_user
    return user.username or user.first_name or f"user_{user.id}"

async def is_authorized_async(user_id: int) -> bool:
    """
    Проверяет авторизацию пользователя через подписку на канал.
    
    Args:
        user_id: ID пользователя Telegram
        
    Returns:
        bool: True если пользователь авторизован (подписан на канал)
    """
    try:
        return await check_channel_subscription(TELEGRAM_BOT_TOKEN, CHANNEL_ID, user_id)
    except Exception as e:
        logger.error(f"[Authorization] Error checking subscription for user {user_id}: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    logger.info(f"[Start] User {user_id} (@{username}) started the bot")
    
    if not await is_authorized_async(user_id):
        await update.message.reply_text(
            "🚫 Доступ к боту ограничен!\n\n"
            "Для использования бота необходимо подписаться на канал:\n"
            "👉 https://t.me/logloss_notes\n\n"
            "После подписки попробуйте снова."
        )
        return
    
    await update.message.reply_text("Привет! Напиши мне что-нибудь. Используй /reset, чтобы очистить историю.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized_async(user_id):
        await update.message.reply_text(
            "🚫 Доступ к боту ограничен!\n\n"
            "Для использования бота необходимо подписаться на канал:\n"
            "👉 https://t.me/logloss_notes\n\n"
            "После подписки попробуйте снова."
        )
        return
    
    reset_thread(user_id)
    await update.message.reply_text("История сброшена.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized_async(user_id):
        await update.message.reply_text(
            "🚫 Доступ к боту ограничен!\n\n"
            "Для использования бота необходимо подписаться на канал:\n"
            "👉 https://t.me/logloss_notes\n\n"
            "После подписки попробуйте снова."
        )
        return
    
    user_message = update.message.text
    username = get_username(update)
    await update.message.chat.send_action(action="typing")
    logger.info(f"Message from {user_id} (@{username}): {user_message}")

    reply = await send_message_and_get_response(user_id, user_message, username)
    await update.message.reply_text(reply)

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized_async(user_id):
        await update.message.reply_text(
            "🚫 Доступ к боту ограничен!\n\n"
            "Для использования бота необходимо подписаться на канал:\n"
            "👉 https://t.me/logloss_notes\n\n"
            "После подписки попробуйте снова."
        )
        return

    await update.message.chat.send_action(action="typing")
    reply = await get_message_history(user_id)
    await update.message.reply_text(reply)

async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_authorized_async(user_id):
        await update.message.reply_text(
            "🚫 Доступ к боту ограничен!\n\n"
            "Для использования бота необходимо подписаться на канал:\n"
            "👉 https://t.me/logloss_notes\n\n"
            "После подписки попробуйте снова."
        )
        return

    await update.message.chat.send_action(action=ChatAction.UPLOAD_DOCUMENT)
    file_path = await export_message_history(user_id)

    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            await update.message.reply_document(f, filename="chat_history.txt")
        os.remove(file_path)
    else:
        await update.message.reply_text("История пуста или произошла ошибка при экспорте.")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда с инструкцией о подписке на канал"""
    user_id = update.effective_user.id
    
    # Проверяем текущий статус подписки
    is_subscribed = await is_authorized_async(user_id)
    
    if is_subscribed:
        await update.message.reply_text(
            "✅ Отлично! Вы уже подписаны на канал и можете пользоваться ботом.\n\n"
            "Просто напишите мне сообщение или используйте команды:\n"
            "• /reset - сбросить историю диалога\n"
            "• /history - показать историю сообщений\n"
            "• /export - экспортировать историю"
        )
    else:
        await update.message.reply_text(
            "📢 Для доступа к боту необходимо подписаться на канал:\n\n"
            "👉 https://t.me/logloss_notes\n\n"
            "После подписки вы сможете:\n"
            "• Общаться с AI-ассистентом\n"
            "• Сохранять историю диалогов\n"
            "• Экспортировать беседы\n\n"
            "После подписки просто отправьте любое сообщение боту!"
        )

def init_analytics_sync():
    """Синхронная обертка для инициализации аналитики."""
    try:
        # Создаем новый event loop для инициализации
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(analytics.init_database())
        logger.info("Analytics database initialized successfully")
        # НЕ закрываем loop, оставляем для telegram-bot
    except Exception as e:
        logger.error(f"Failed to initialize analytics database: {e}")

def main():
    # Инициализируем аналитику
    init_analytics_sync()
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("export", export))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    try:
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        # Graceful shutdown
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(analytics.close())
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error closing analytics: {e}")

if __name__ == "__main__":
    main()
