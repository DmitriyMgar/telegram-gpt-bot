from logger import logger
import os
import asyncio

from telegram import Update, BotCommand
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
            "🔐 **Для доступа к боту требуется подписка на канал**\n\n"
            "**Telegram GPT Bot** - умный AI-ассистент с возможностями:\n"
            "• 🤖 Продвинутое общение с искусственным интеллектом\n"
            "• 💾 Сохранение истории всех ваших диалогов\n"
            "• 🧠 Понимание контекста и ведение осмысленных бесед\n"
            "• 📁 Экспорт переписки в удобном формате\n\n"
            "**Для получения доступа:**\n"
            "1️⃣ Подпишитесь на канал: https://t.me/logloss_notes\n"
            "2️⃣ Нажмите \"Присоединиться\" в канале\n"
            "3️⃣ Вернитесь сюда и отправьте любое сообщение\n\n"
            "После подписки вам станут доступны все функции бота!\n"
            "*Подписка проверяется автоматически*"
        )
        return
    
    await update.message.reply_text(
        "🤖 **Добро пожаловать в Telegram GPT Bot!**\n\n"
        "Я - ваш персональный AI-ассистент с уникальными возможностями:\n"
        "• 💬 **Умные диалоги** - понимаю контекст и веду осмысленные беседы\n"
        "• 🧠 **Память** - помню всю нашу историю общения\n"
        "• 📚 **Непрерывность** - наш диалог продолжится даже после перерывов\n"
        "• 📁 **Сохранение** - можете экспортировать любую беседу\n\n"
        "**Как пользоваться:**\n"
        "• Просто напишите мне любое сообщение\n"
        "• `/reset` - начать новую беседу с чистого листа\n"
        "• `/history` - посмотреть последние сообщения\n"
        "• `/export` - скачать всю историю общения\n"
        "• `/subscribe` - проверить статус доступа\n\n"
        "Готов помочь с любыми вопросами! Начните просто написав мне сообщение 🚀"
    )

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
            "✅ **Отлично! У вас есть полный доступ к боту**\n\n"
            "**Telegram GPT Bot готов к работе!**\n\n"
            "**Ваши возможности:**\n"
            "• 🤖 Неограниченное общение с AI-ассистентом\n"
            "• 🧠 Бот помнит контекст всей беседы\n"
            "• 💾 История диалогов сохраняется автоматически\n"
            "• 📁 Экспорт переписки в любой момент\n\n"
            "**Команды для управления:**\n"
            "• `/reset` - начать новую беседу с чистого листа\n"
            "• `/history` - посмотреть последние 10 сообщений\n"
            "• `/export` - скачать всю историю общения\n"
            "• `/subscribe` - проверить статус (эта команда)\n\n"
            "Просто напишите любое сообщение для начала диалога! 🚀"
        )
    else:
        await update.message.reply_text(
            "📢 **Для доступа к боту требуется подписка на канал**\n\n"
            "**Что вы получите после подписки:**\n"
            "• 🤖 Умный AI-ассистент для любых задач\n"
            "• 💬 Естественные диалоги с пониманием контекста\n"
            "• 📚 Непрерывные беседы - бот помнит всю историю\n"
            "• 📁 Возможность экспорта переписки\n"
            "• 🔄 Сессии работают даже после перезапуска\n\n"
            "**Простые шаги для активации:**\n"
            "1️⃣ Перейдите по ссылке: https://t.me/logloss_notes\n"
            "2️⃣ Нажмите \"Присоединиться к каналу\"\n"
            "3️⃣ Вернитесь сюда и отправьте любое сообщение\n\n"
            "**Подписка проверяется автоматически!**\n"
            "Доступ откроется сразу после подписки ✨"
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

async def setup_bot_commands(bot):
    """Устанавливает меню команд для бота."""
    commands = [
        BotCommand("start", "🚀 Начать работу с ботом"),
        BotCommand("reset", "🔄 Начать новую беседу"),
        BotCommand("history", "📝 Показать историю сообщений"),
        BotCommand("export", "📁 Экспортировать историю чата"),
        BotCommand("subscribe", "📢 Проверить статус подписки")
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Bot commands menu set successfully")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

def main():
    # Инициализируем аналитику
    init_analytics_sync()
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Устанавливаем меню команд
    app.job_queue.run_once(lambda context: asyncio.create_task(setup_bot_commands(context.bot)), when=1)

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
