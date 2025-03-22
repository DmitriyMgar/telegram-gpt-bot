from logger import logger
import os

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN, ALLOWED_USERS
from openai_handler import send_message_and_get_response, get_message_history, export_message_history
from session_manager import reset_thread
from telegram.constants import ChatAction

# Путь до лог-файла
LOG_FILE = os.path.join(os.path.dirname(__file__), "bot.log")

def is_authorized(user_id: int) -> bool:
    return user_id in ALLOWED_USERS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("Извините, у вас нет доступа к этому боту.")
        return
    
    await update.message.reply_text("Привет! Напиши мне что-нибудь. Используй /reset, чтобы очистить историю.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return
    
    reset_thread(user_id)
    await update.message.reply_text("История сброшена.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return
    
    user_message = update.message.text
    await update.message.chat.send_action(action="typing")
    logger.info(f"Message from {user_id}: {user_message}")

    reply = await send_message_and_get_response(user_id, user_message)
    await update.message.reply_text(reply)

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return

    await update.message.chat.send_action(action="typing")
    reply = await get_message_history(user_id)
    await update.message.reply_text(reply)

async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return

    await update.message.chat.send_action(action=ChatAction.UPLOAD_DOCUMENT)
    file_path = await export_message_history(user_id)

    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            await update.message.reply_document(f, filename="chat_history.txt")
        os.remove(file_path)
    else:
        await update.message.reply_text("История пуста или произошла ошибка при экспорте.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("export", export))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
