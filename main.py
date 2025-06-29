from logger import logger
import os
import asyncio
import tempfile
from pathlib import Path
import logging
import re

from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN, CHANNEL_ID
from openai_handler import send_message_and_get_response, send_message_and_get_response_for_chat, add_message_to_context, add_message_to_context_for_chat, get_message_history, export_message_history, send_image_and_get_response, send_image_and_get_response_for_chat, detect_image_generation_request, generate_image_dalle, send_document_and_get_response
from session_manager import reset_thread, reset_chat_thread, get_thread_id_for_chat, set_thread_id_for_chat
from telegram.constants import ChatAction
from subscription_checker import check_channel_subscription
from user_analytics import analytics
from chat_detector import (
    should_process_message, should_respond_in_chat, get_chat_identifier, get_log_context, 
    is_private_chat, is_group_chat
)

# Путь до лог-файла
LOG_FILE = os.path.join(os.path.dirname(__file__), "bot.log")

# Bot information for dual-mode operation
bot_info = {"username": None, "id": None}

async def init_bot_info(bot):
    """Initialize bot information for dual-mode operation"""
    try:
        bot_user = await bot.get_me()
        bot_info["username"] = bot_user.username
        bot_info["id"] = bot_user.id
        logger.info(f"Bot initialized: @{bot_info['username']} (ID: {bot_info['id']})")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")

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
    # Check if bot should respond in this chat context
    if not should_respond_in_chat(update, bot_info["username"], bot_info["id"]):
        return  # Ignore start command in group chats without mention/reply
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    log_context = get_log_context(update)
    logger.info(f"[Start] {log_context}")
    
    if not await is_authorized_async(user_id):
        await update.message.reply_text(
            "🔐 <b>Для доступа к боту требуется подписка на канал</b>\n\n"
            "<b>Telegram GPT Bot</b> - умный AI-ассистент с возможностями:\n"
            "• 🤖 Продвинутое общение с искусственным интеллектом\n"
            "• 💾 Сохранение истории всех ваших диалогов\n"
            "• 🧠 Понимание контекста и ведение осмысленных бесед\n"
            "• 🖼️ Анализ и обработка изображений\n"
            "• 📄 Работа с документами (PDF, TXT, DOCX)\n"
            "• 📁 Экспорт переписки в удобном формате\n\n"
            "<b>Для получения доступа:</b>\n"
            "1️⃣ Подпишитесь на канал: https://t.me/logloss_notes\n"
            "2️⃣ Нажмите \"Присоединиться\" в канале\n"
            "3️⃣ Вернитесь сюда и отправьте любое сообщение\n\n"
            "🔒 <b>Конфиденциальность гарантирована:</b>\n"
            "• Ваши диалоги видите только вы\n"
            "• Данные хранятся на серверах OpenAI (уровень безопасности как у ChatGPT)\n"
            "• Полная приватность вашего общения с ботом\n\n"
            "После подписки вам станут доступны все функции бота!\n"
            "<i>Подписка проверяется автоматически</i>",
            parse_mode='HTML'
        )
        return
    
    # Provide context-appropriate welcome message
    if is_private_chat(update):
        await update.message.reply_text(
            "🤖 <b>Добро пожаловать в Telegram GPT Bot!</b>\n\n"
            "Я - ваш персональный AI-ассистент с уникальными возможностями:\n"
            "• 💬 <b>Умные диалоги</b> - понимаю контекст и веду осмысленные беседы\n"
            "• 🧠 <b>Память</b> - помню всю нашу историю общения\n"
            "• 📚 <b>Непрерывность</b> - наш диалог продолжится даже после перерывов\n"
            "• 🖼️ <b>Анализ изображений</b> - могу анализировать и описывать картинки\n"
            "• 📄 <b>Работа с документами</b> - анализирую PDF, TXT, DOCX файлы\n"
            "• 🎨 <b>Генерация изображений</b> - создаю картинки по вашим описаниям\n"
            "• 📁 <b>Сохранение</b> - можете экспортировать любую беседу\n\n"
            "<b>Как пользоваться:</b>\n"
            "• Напишите мне любое текстовое сообщение\n"
            "• Отправьте изображение с подписью или без\n"
            "• Прикрепите документ (PDF, TXT, DOCX) с вопросом или без\n"
            "• <code>/reset</code> - начать новую беседу с чистого листа\n"
            "• <code>/history</code> - посмотреть последние сообщения\n"
            "• <code>/export</code> - скачать всю историю общения\n"
            "• <code>/subscribe</code> - проверить статус доступа\n\n"
            "🔒 <b>Конфиденциальность:</b>\n"
            "• Ваш диалог с ботом видите только <b>вы</b>\n"
            "• История сохраняется на серверах OpenAI (как у ChatGPT)\n"
            "• Ваши сообщения защищены наравне с миллиардами диалогов других пользователей\n"
            "• Никто другой не имеет доступа к вашей переписке\n\n"
            "Готов помочь с любыми вопросами! Начните просто написав мне сообщение или отправив изображение 🚀",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "🤖 <b>Привет! Я Telegram GPT Bot</b>\n\n"
            "Теперь я работаю в этом чате! Мои возможности:\n"
            "• 💬 <b>Умные диалоги</b> - отвечаю на упоминания и в ответах\n"
            "• 🧠 <b>Память чата</b> - помню контекст беседы в этом чате\n"
            "• 🖼️ <b>Анализ изображений</b> - могу анализировать картинки\n"
            "• 📄 <b>Работа с документами</b> - анализирую PDF, TXT, DOCX файлы\n"
            "• 🎨 <b>Генерация изображений</b> - создаю картинки по описаниям\n\n"
            "<b>Как со мной общаться в группе:</b>\n"
            f"• Упомяните меня: <code>@{bot_info['username']} ваш вопрос</code>\n"
            "• Ответьте на мое сообщение\n"
            "• Используйте команды: <code>/reset</code>, <code>/start</code>\n\n"
            "🔒 <b>Приватность:</b>\n"
            "• История чата сохраняется отдельно для каждой группы\n"
            "• Данные защищены как у ChatGPT\n"
            "• Доступ к боту только у подписчиков @logloss_notes\n\n"
            f"Готов помочь! Упомяните меня <code>@{bot_info['username']}</code> с вашим вопросом 🚀",
            parse_mode='HTML'
        )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if bot should respond in this chat context
    if not should_respond_in_chat(update, bot_info["username"], bot_info["id"]):
        return  # Ignore reset command in group chats without mention/reply
    
    user_id = update.effective_user.id
    if not await is_authorized_async(user_id):
        await update.message.reply_text(
            "🚫 Доступ к боту ограничен!\n\n"
            "Для использования бота необходимо подписаться на канал:\n"
            "👉 https://t.me/logloss_notes\n\n"
            "После подписки попробуйте снова."
        )
        return
    
    chat_identifier = get_chat_identifier(update)
    log_context = get_log_context(update)
    
    # Use dual-mode reset
    await reset_chat_thread(chat_identifier)
    
    # Provide appropriate response based on chat type
    if is_private_chat(update):
        await update.message.reply_text("🔄 История и файлы сброшены. Новая беседа начата!")
    else:
        await update.message.reply_text("🔄 История беседы в этом чате сброшена. Новая беседа начата!")
    
    logger.info(f"{log_context} - Reset completed")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # First check if we should process this message at all
    if not should_process_message(update):
        return  # Ignore system messages, other bots, etc.
    
    user_id = update.effective_user.id
    # Handle both text messages and captions (for context tracking)
    user_message = update.message.text or update.message.caption
    
    # Skip if no text content to process
    if not user_message:
        return
    
    username = get_username(update)
    chat_identifier = get_chat_identifier(update)
    log_context = get_log_context(update)
    
    # Check authorization - required for both processing and responding
    if not await is_authorized_async(user_id):
        # Only show authorization message if bot should respond
        if should_respond_in_chat(update, bot_info["username"], bot_info["id"]):
            await update.message.reply_text(
                "🚫 Доступ к боту ограничен!\n\n"
                "Для использования бота необходимо подписаться на канал:\n"
                "👉 https://t.me/logloss_notes\n\n"
                "После подписки попробуйте снова."
            )
        return
    
    # Check if we should respond to this message
    should_respond = should_respond_in_chat(update, bot_info["username"], bot_info["id"])
    
    logger.info(f"{log_context}: {user_message} {'[RESPOND]' if should_respond else '[CONTEXT]'}")
    
    # If we shouldn't respond, just add to context and return
    if not should_respond:
        try:
            if is_private_chat(update):
                # This shouldn't happen in private chats, but handle it anyway
                await add_message_to_context(user_id, user_message, username)
            else:
                # Add group message to context without responding
                await add_message_to_context_for_chat(chat_identifier, user_message, username, user_id)
        except Exception as context_error:
            logger.error(f"Error adding message to context {log_context}: {context_error}")
        return
    
    # From here on, we're responding to the message
    await update.message.chat.send_action(action="typing")

    # NEW: Image generation detection
    if await detect_image_generation_request(user_message):
        await handle_image_generation_request(update, context, user_message)
        return

    # Отправляем сообщение о том, что запрос обрабатывается
    processing_message = await update.message.reply_text(
        "🤖 Ваш запрос передан в <b>ChatGPT</b> и обрабатывается...",
        parse_mode='HTML'
    )

    try:
        # Use dual-mode session management
        if is_private_chat(update):
            # For private chats, use legacy user_id based system
            reply = await send_message_and_get_response(user_id, user_message, username)
        else:
            # For group chats, use chat-based system
            reply = await send_message_and_get_response_for_chat(chat_identifier, user_message, username, user_id)
        
        # Конвертируем Markdown в HTML для красивого отображения
        formatted_reply = markdown_to_html(reply)
        
        # Заменяем сообщение о обработке на ответ
        try:
            await processing_message.edit_text(formatted_reply, parse_mode='HTML')
        except Exception as message_edit_error:
            # If editing failed (e.g., message too long), send new message with reply
            logger.warning(f"Failed to edit processing message: {message_edit_error}")
            await update.message.reply_text(formatted_reply, parse_mode='HTML')
            
    except Exception as message_processing_error:
        logger.error(f"Error processing message {log_context}: {message_processing_error}")
        # Replace processing message with error message
        try:
            await processing_message.edit_text("❌ Произошла ошибка при обработке запроса. Попробуйте еще раз.")
        except:
            await update.message.reply_text("❌ Произошла ошибка при обработке запроса. Попробуйте еще раз.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages with optional caption"""
    # First check if we should process this message at all
    if not should_process_message(update):
        return  # Ignore system messages, other bots, etc.
    
    user_id = update.effective_user.id
    username = get_username(update)
    caption = update.message.caption or ""
    chat_identifier = get_chat_identifier(update)
    log_context = get_log_context(update)
    
    # Check authorization - required for both processing and responding
    if not await is_authorized_async(user_id):
        # Only show authorization message if bot should respond
        if should_respond_in_chat(update, bot_info["username"], bot_info["id"]):
            await update.message.reply_text(
                "🚫 Доступ к боту ограничен!\n\n"
                "Для использования бота необходимо подписаться на канал:\n"
                "👉 https://t.me/logloss_notes\n\n"
                "После подписки попробуйте снова."
            )
        return
    
    # Check if we should respond to this message
    should_respond = should_respond_in_chat(update, bot_info["username"], bot_info["id"])
    
    logger.info(f"{log_context} - Photo with caption: {caption} {'[RESPOND]' if should_respond else '[CONTEXT]'}")
    
    # Photos require response processing, so if we shouldn't respond, skip
    # (Unlike text messages, we don't add photos to context without processing them)
    if not should_respond:
        return
    
    # From here on, we're responding to the photo
    await update.message.chat.send_action(action="typing")
    
    try:
        # Get the largest photo size
        photo = update.message.photo[-1]
        
        # Check file size (max 20MB as per Telegram limit)
        if photo.file_size > 20 * 1024 * 1024:
            await update.message.reply_text(
                "🚫 Файл слишком большой. Максимальный размер изображения: 20MB"
            )
            return
        
        # Get file info
        file = await context.bot.get_file(photo.file_id)
        
        # Create temporary file
        temp_dir = Path(tempfile.gettempdir()) / "telegram_bot_images"
        temp_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.file_path).suffix.lower()
        if file_extension not in ['.jpg', '.jpeg', '.png', '.webp']:
            await update.message.reply_text(
                "🚫 Поддерживаются только форматы: JPEG, PNG, WebP"
            )
            return
        
        temp_file_path = temp_dir / f"image_{user_id}_{photo.file_unique_id}{file_extension}"
        
        # Download image using Telegram Bot API
        await file.download_to_drive(temp_file_path)
        
        # Отправляем сообщение о том, что изображение обрабатывается
        processing_message = await update.message.reply_text(
            "🖼️ Ваше изображение передано в <b>ChatGPT</b> для анализа...",
            parse_mode='HTML'
        )
        
        # Process image with OpenAI using dual-mode
        if is_private_chat(update):
            # For private chats, use legacy user_id based system
            reply = await send_image_and_get_response(user_id, str(temp_file_path), caption, username)
        else:
            # For group chats, use chat-based system
            reply = await send_image_and_get_response_for_chat(chat_identifier, str(temp_file_path), caption, username, user_id)
        
        # Конвертируем Markdown в HTML для красивого отображения
        formatted_reply = markdown_to_html(reply)
        
        # Заменяем сообщение о обработке на ответ
        try:
            await processing_message.edit_text(formatted_reply, parse_mode='HTML')
        except Exception as e:
            # Если не удалось отредактировать (например, сообщение слишком длинное),
            # отправляем новое сообщение с ответом
            logger.warning(f"Failed to edit processing message for image: {e}")
            await update.message.reply_text(formatted_reply, parse_mode='HTML')
        
    except Exception as image_processing_error:
        logger.error(f"Error processing photo from user {user_id}: {image_processing_error}")
        # Try to edit processing message if it exists
        if 'processing_message' in locals():
            try:
                await processing_message.edit_text("❌ Произошла ошибка при обработке изображения")
            except:
                await update.message.reply_text("❌ Произошла ошибка при обработке изображения")
        else:
            await update.message.reply_text("❌ Произошла ошибка при обработке изображения")
    finally:
        # Cleanup temporary file
        try:
            if 'temp_file_path' in locals() and temp_file_path.exists():
                temp_file_path.unlink()
        except Exception as cleanup_error:
            logger.error(f"Error cleaning up temp file: {cleanup_error}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document messages (TXT, PDF, DOCX)"""
    user_id = update.effective_user.id
    if not await is_authorized_async(user_id):
        await update.message.reply_text(
            "🚫 Доступ к боту ограничен!\n\n"
            "Для использования бота необходимо подписаться на канал:\n"
            "👉 https://t.me/logloss_notes\n\n"
            "После подписки попробуйте снова."
        )
        return
    
    username = get_username(update)
    document = update.message.document
    caption = update.message.caption or ""
    
    # Define allowed document types
    ALLOWED_DOCUMENT_TYPES = {
        "application/pdf": ".pdf",
        "text/plain": ".txt", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx"
    }
    
    # Check file type
    if document.mime_type not in ALLOWED_DOCUMENT_TYPES:
        await update.message.reply_text(
            "❌ <b>Неподдерживаемый тип файла</b>\n\n"
            "Поддерживаемые форматы:\n"
            "• 📄 <b>PDF</b> - документы PDF\n"
            "• 📝 <b>TXT</b> - текстовые файлы\n"
            "• 📄 <b>DOCX</b> - документы Word\n\n"
            "Пожалуйста, отправьте файл одного из поддерживаемых форматов.",
            parse_mode='HTML'
        )
        return
    
    # Check file extension as additional validation
    file_extension = Path(document.file_name).suffix.lower() if document.file_name else ""
    expected_extension = ALLOWED_DOCUMENT_TYPES[document.mime_type]
    if file_extension != expected_extension:
        await update.message.reply_text(
            f"❌ <b>Несоответствие расширения файла</b>\n\n"
            f"Ожидается: <code>{expected_extension}</code>\n"
            f"Получено: <code>{file_extension}</code>\n\n"
            "Убедитесь, что файл имеет правильное расширение.",
            parse_mode='HTML'
        )
        return
    
    # Check file size (15MB limit)
    max_size = 15 * 1024 * 1024  # 15MB
    if document.file_size > max_size:
        await update.message.reply_text(
            f"❌ <b>Файл слишком большой</b>\n\n"
            f"Размер файла: <b>{document.file_size / (1024*1024):.1f} MB</b>\n"
            f"Максимальный размер: <b>15 MB</b>\n\n"
            "Пожалуйста, уменьшите размер файла или разделите его на части.",
            parse_mode='HTML'
        )
        return
    
    await update.message.chat.send_action(action="typing")
    logger.info(f"Document message from {user_id} (@{username}): {document.file_name} ({document.mime_type}) with caption: {caption}")
    
    # Processing message
    processing_message = await update.message.reply_text(
        f"📄 Обрабатываю документ <b>{document.file_name}</b>...\n"
        f"<i>Это может занять некоторое время в зависимости от размера документа</i>",
        parse_mode='HTML'
    )
    
    temp_file_path = None
    try:
        # Get file info
        file = await context.bot.get_file(document.file_id)
        
        # Create temporary file
        temp_dir = Path(tempfile.gettempdir()) / "telegram_bot_documents"
        temp_dir.mkdir(exist_ok=True)
        
        # Use original filename with proper extension
        original_filename = document.file_name or f"document{expected_extension}"
        temp_file_path = temp_dir / f"{user_id}_{document.file_id}_{original_filename}"
        
        # Download file
        await file.download_to_drive(temp_file_path)
        logger.debug(f"Downloaded document to: {temp_file_path}")
        
        # Process document with OpenAI
        reply = await send_document_and_get_response(
            user_id=user_id,
            local_file_path=str(temp_file_path),
            user_message=caption,
            original_filename=original_filename,
            username=username
        )
        
        # Format reply
        formatted_reply = markdown_to_html(reply)
        
        # Edit processing message with result
        await processing_message.edit_text(formatted_reply, parse_mode='HTML')
        
        logger.info(f"Document processed successfully for user {user_id}")
        
    except Exception as document_processing_error:
        logger.error(f"Error processing document from user {user_id}: {document_processing_error}")
        # Edit processing message with error
        try:
            await processing_message.edit_text(
                "❌ <b>Ошибка при обработке документа</b>\n\n"
                "Попробуйте еще раз или обратитесь к администратору, если проблема повторяется.",
                parse_mode='HTML'
            )
        except:
            await update.message.reply_text(
                "❌ <b>Ошибка при обработке документа</b>\n\n"
                "Попробуйте еще раз или обратитесь к администратору, если проблема повторяется.",
                parse_mode='HTML'
            )
    finally:
        # Cleanup temporary file
        try:
            if temp_file_path and temp_file_path.exists():
                temp_file_path.unlink()
                logger.debug(f"Cleaned up temp file: {temp_file_path}")
        except Exception as cleanup_error:
            logger.error(f"Error cleaning up temp document file: {cleanup_error}")

async def handle_image_generation_request(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str):
    """Processes image generation requests"""
    user_id = update.effective_user.id
    username = get_username(update)
    
    # Processing notification
    processing_message = await update.message.reply_text(
        "🎨 Generating image with <b>DALL-E 3</b>...\n"
        "<i>This may take 10-30 seconds</i>",
        parse_mode='HTML'
    )
    
    try:
        # Generate image
        image_url, tokens_used = await generate_image_dalle(prompt, user_id, username)
        
        # Send result
        await update.message.reply_photo(
            photo=image_url,
            caption=f"🎨 <b>Generated by DALL-E 3</b>\n\n"
                   f"<i>Prompt:</i> {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n\n"
                   f"<i>Used ~{tokens_used} tokens (≈$0.04)</i>",
            parse_mode='HTML'
        )
        
        # Remove processing message
        await processing_message.delete()
        
        logger.info(f"Generated image for user {user_id}: {prompt[:50]}...")
        
    except Exception as image_generation_error:
        error_message = str(image_generation_error) if str(image_generation_error) else "Image generation failed"
        await processing_message.edit_text(f"❌ {error_message}")
        logger.error(f"Image generation failed for user {user_id}: {image_generation_error}")

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
    formatted_reply = markdown_to_html(reply)
    await update.message.reply_text(formatted_reply, parse_mode='HTML')

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
            "✅ <b>Отлично! У вас есть полный доступ к боту</b>\n\n"
            "<b>Telegram GPT Bot готов к работе!</b>\n\n"
            "<b>Ваши возможности:</b>\n"
            "• 🤖 Неограниченное общение с AI-ассистентом\n"
            "• 🧠 Бот помнит контекст всей беседы\n"
            "• 💾 История диалогов сохраняется автоматически\n"
            "• 📁 Экспорт переписки в любой момент\n"
            "• 🖼️ Анализ изображений\n"
            "• 📄 Работа с документами (PDF, TXT, DOCX)\n"
            "• 🎨 Генерация изображений с помощью DALL-E 3\n\n"
            "<b>Команды для управления:</b>\n"
            "• <code>/reset</code> - начать новую беседу с чистого листа\n"
            "• <code>/history</code> - посмотреть последние 10 сообщений\n"
            "• <code>/export</code> - скачать всю историю общения\n"
            "• <code>/subscribe</code> - проверить статус (эта команда)\n\n"
            "Просто напишите любое сообщение для начала диалога! 🚀",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "📢 <b>Для доступа к боту требуется подписка на канал</b>\n\n"
            "<b>Что вы получите после подписки:</b>\n"
            "• 🤖 Умный AI-ассистент для любых задач\n"
            "• 💬 Естественные диалоги с пониманием контекста\n"
            "• 📚 Непрерывные беседы - бот помнит всю историю\n"
            "• 📁 Возможность экспорта переписки\n"
            "• 🖼️ Анализ изображений\n"
            "• 📄 Работа с документами (PDF, TXT, DOCX)\n"
            "• 🎨 Генерация изображений с помощью DALL-E 3\n"
            "• 🔄 Сессии работают даже после перезапуска\n\n"
            "<b>Простые шаги для активации:</b>\n"
            "1️⃣ Перейдите по ссылке: https://t.me/logloss_notes\n"
            "2️⃣ Нажмите \"Присоединиться к каналу\"\n"
            "3️⃣ Вернитесь сюда и отправьте любое сообщение\n\n"
            "<b>Подписка проверяется автоматически!</b>\n"
            "Доступ откроется сразу после подписки ✨",
            parse_mode='HTML'
        )

async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /generate for explicit image generation"""
    user_id = update.effective_user.id
    
    if not await is_authorized_async(user_id):
        await update.message.reply_text("🚫 Bot access restricted!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "🎨 <b>Image Generation</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/generate image description</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/generate beautiful sunset over ocean</code>\n"
            "• <code>/generate cat in astronaut suit</code>\n"
            "• <code>/generate futuristic city</code>\n\n"
            "<i>Cost: ~$0.04 per image</i>",
            parse_mode='HTML'
        )
        return
    
    prompt = " ".join(context.args)
    await handle_image_generation_request(update, context, prompt)

def init_analytics_sync():
    """Синхронная обертка для инициализации аналитики."""
    try:
        # Создаем новый event loop для инициализации
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(analytics.init_database())
        logger.info("Analytics database initialized successfully")
        # НЕ закрываем loop, оставляем для telegram-bot
    except Exception as analytics_init_error:
        logger.error(f"Failed to initialize analytics database: {analytics_init_error}")

async def setup_bot_commands(bot):
    """Устанавливает меню команд для бота."""
    commands = [
        BotCommand("start", "🚀 Начать работу с ботом"),
        BotCommand("reset", "🔄 Начать новую беседу"),
        BotCommand("generate", "🎨 Генерировать изображение"),
        BotCommand("history", "📝 Показать историю сообщений"),
        BotCommand("export", "📁 Экспортировать историю чата"),
        BotCommand("subscribe", "📢 Проверить статус подписки")
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Bot commands menu set successfully")
    except Exception as commands_setup_error:
        logger.error(f"Failed to set bot commands: {commands_setup_error}")

def markdown_to_html(text):
    """Конвертирует основные элементы Markdown в HTML для Telegram"""
    # Экранируем HTML символы (кроме тех, что мы сами добавим)
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Блоки кода (```code```) - обрабатываем до одиночных `
    text = re.sub(r'```(.+?)```', r'<pre>\1</pre>', text, flags=re.DOTALL)
    
    # Заголовки - делаем их жирными с дополнительным отступом
    text = re.sub(r'^### (.+)$', r'\n<b>\1</b>\n', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'\n<b>\1</b>\n', text, flags=re.MULTILINE) 
    text = re.sub(r'^# (.+)$', r'\n<b>\1</b>\n', text, flags=re.MULTILINE)
    
    # Жирный текст
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    
    # Курсив (только одиночные *, избегаем конфликта с жирным)
    text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_([^_]+?)_(?!_)', r'<i>\1</i>', text)
    
    # Одиночный код (после блоков кода)
    text = re.sub(r'`([^`]+?)`', r'<code>\1</code>', text)
    
    # Списки - улучшенная обработка
    text = re.sub(r'^[\s]*[-\*\+] (.+)$', r'• \1', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\. (.+)$', r'• \1', text, flags=re.MULTILINE)
    
    # Убираем лишние переносы строк
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def main():
    # Инициализируем аналитику
    init_analytics_sync()
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Инициализируем информацию о боте для dual-mode operation
    app.job_queue.run_once(lambda context: asyncio.create_task(init_bot_info(context.bot)), when=0.5)
    
    # Устанавливаем меню команд
    app.job_queue.run_once(lambda context: asyncio.create_task(setup_bot_commands(context.bot)), when=1)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("export", export))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("generate", generate_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.PDF | filters.Document.TXT | filters.Document.Category("application/vnd.openxmlformats-officedocument.wordprocessingml.document"), handle_document))
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
        except Exception as analytics_close_error:
            logger.error(f"Error closing analytics: {analytics_close_error}")

if __name__ == "__main__":
    main()
