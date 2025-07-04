import asyncio
import re
from config import OPENAI_API_KEY, ASSISTANT_ID
from session_manager import get_thread_id, set_thread_id, add_user_image, add_user_document, get_thread_id_for_chat, set_thread_id_for_chat, add_chat_image, add_chat_document
from logger import logger
from openai import AsyncOpenAI
from openai.types import Image, ImageModel, ImagesResponse
import openai
import tempfile
from user_analytics import analytics

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def create_thread():
    thread = await client.beta.threads.create()
    return thread.id

async def send_message_and_get_response(user_id: int, user_message: str, username: str = None) -> str:
    thread_id = get_thread_id(user_id)
    if not thread_id:
        thread_id = await create_thread()
        set_thread_id(user_id, thread_id)

    # Добавляем сообщение пользователя
    await client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    # Запускаем выполнение
    run = await client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID,
    )

    # Ожидаем завершения
    while True:
        run_status = await client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        if run_status.status in ["completed", "failed", "cancelled"]:
            break
        await asyncio.sleep(1)

    # Проверка статуса выполнения
    if run_status.status == "failed":
        logger.error(f"[OpenAI] Assistant run failed for user {user_id}: {run_status.last_error}")
        return "❌ Ошибка при обработке запроса. Попробуйте еще раз."
    
    if run_status.status == "cancelled":
        logger.error(f"[OpenAI] Assistant run cancelled for user {user_id}")
        return "❌ Запрос был отменен. Попробуйте еще раз."
    
    if run_status.status == "requires_action":
        logger.warning(f"[OpenAI] Assistant requires action for user {user_id} - this is not supported")
        return "❌ Запрос требует дополнительных действий, которые не поддерживаются."

    # Записываем использование токенов в аналитику
    tokens_used = 0
    if run_status.usage and run_status.usage.total_tokens:
        tokens_used = run_status.usage.total_tokens
        logger.debug(f"[OpenAI] Tokens used: {tokens_used} (prompt: {run_status.usage.prompt_tokens}, completion: {run_status.usage.completion_tokens})")
    
    # Записываем в аналитику
    if tokens_used > 0:
        try:
            await analytics.record_usage(user_id, username, tokens_used)
        except Exception as e:
            logger.error(f"Failed to record usage analytics: {e}")

    # Получаем только новые сообщения
    messages = await client.beta.threads.messages.list(thread_id=thread_id)
    
    # Логирование для диагностики (БЕЗ содержимого сообщений!)
    logger.debug(f"[OpenAI] Retrieved {len(messages.data)} messages for user {user_id}")
    logger.debug(f"[OpenAI] Run created at: {run.created_at}, status: {run_status.status}")
    
    assistant_messages_count = 0
    for message in reversed(messages.data):
        if message.role == "assistant":
            assistant_messages_count += 1
        
        if (
            message.role == "assistant" and
            message.created_at >= run.created_at
        ):
            reply = message.content[0].text.value
            logger.info(f"[OpenAI] Response sent to user {user_id}")
            return reply
    
    # Логирование деталей если не найден подходящий ответ (БЕЗ содержимого!)
    logger.warning(f"[OpenAI] No suitable response found for user {user_id}")
    logger.warning(f"[OpenAI] Run status: {run_status.status}")
    logger.warning(f"[OpenAI] Assistant messages found: {assistant_messages_count}")
    logger.warning(f"[OpenAI] Run created_at: {run.created_at}")

    return "Ошибка: не удалось получить ответ."


async def add_message_to_context(user_id: int, user_message: str, username: str = None):
    """
    Adds a message to the conversation context without generating a response.
    Used for maintaining context in group chats where bot shouldn't respond
    but needs to track the conversation.
    
    Args:
        user_id: User ID for session management
        user_message: Message text to add to context
        username: Username for logging
    """
    thread_id = get_thread_id(user_id)
    if not thread_id:
        thread_id = await create_thread()
        set_thread_id(user_id, thread_id)

    try:
        # Add message to thread without running the assistant
        await client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )
        logger.debug(f"Added context message for user {user_id}")
    except Exception as e:
        logger.error(f"Error adding message to context for user {user_id}: {e}")


async def add_message_to_context_for_chat(chat_identifier: str, user_message: str, username: str = None, user_id: int = None):
    """
    Dual-mode version: Adds a message to the conversation context without generating a response.
    Used for maintaining context in group chats where bot shouldn't respond
    but needs to track the conversation.
    
    Args:
        chat_identifier: Either "user:USER_ID" or "chat:CHAT_ID"
        user_message: Message text to add to context
        username: Username for logging
        user_id: User ID for analytics (required for group chats)
    """
    thread_id = get_thread_id_for_chat(chat_identifier)
    if not thread_id:
        thread_id = await create_thread()
        set_thread_id_for_chat(chat_identifier, thread_id)

    try:
        # Add message to thread without running the assistant
        await client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )
        logger.debug(f"Added context message for {chat_identifier}")
    except Exception as e:
        logger.error(f"Error adding message to context for {chat_identifier}: {e}")


async def add_image_to_context(user_id: int, image_path: str, caption: str = "", username: str = None):
    """
    Adds an image to the conversation context without generating a response.
    Used for maintaining context in group chats where bot shouldn't respond
    but needs to track the conversation.
    
    Args:
        user_id: User ID for session management
        image_path: Path to the image file
        caption: Optional caption text
        username: Username for logging
    """
    thread_id = get_thread_id(user_id)
    if not thread_id:
        thread_id = await create_thread()
        set_thread_id(user_id, thread_id)

    try:
        # Upload image file to OpenAI with purpose="vision"
        with open(image_path, "rb") as image_file:
            uploaded_file = await client.files.create(
                file=image_file,
                purpose="vision"
            )
        
        # Save file_id in Redis for tracking
        add_user_image(user_id, uploaded_file.id)
        
        # Create message content with uploaded file
        message_content = [
            {
                "type": "image_file",
                "image_file": {
                    "file_id": uploaded_file.id,
                    "detail": "high"
                }
            }
        ]
        
        # Add text if caption provided
        if caption.strip():
            message_content.insert(0, {
                "type": "text",
                "text": caption
            })
        
        # Add message to thread without running the assistant
        await client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_content
        )
        
        logger.debug(f"Added image to context for user {user_id} (file_id: {uploaded_file.id})")
        
    except Exception as e:
        logger.error(f"Error adding image to context for user {user_id}: {e}")


async def add_image_to_context_for_chat(chat_identifier: str, image_path: str, caption: str = "", username: str = None, user_id: int = None):
    """
    Dual-mode version: Adds an image to the conversation context without generating a response.
    Used for maintaining context in group chats where bot shouldn't respond
    but needs to track the conversation.
    
    Args:
        chat_identifier: Either "user:USER_ID" or "chat:CHAT_ID"
        image_path: Path to the image file
        caption: Optional caption text
        username: Username for logging
        user_id: User ID for analytics (required for group chats)
    """
    thread_id = get_thread_id_for_chat(chat_identifier)
    if not thread_id:
        thread_id = await create_thread()
        set_thread_id_for_chat(chat_identifier, thread_id)

    try:
        # Upload image file to OpenAI with purpose="vision"
        with open(image_path, "rb") as image_file:
            uploaded_file = await client.files.create(
                file=image_file,
                purpose="vision"
            )
        
        # Save file_id in Redis for tracking
        add_chat_image(chat_identifier, uploaded_file.id)
        
        # Create message content with uploaded file
        message_content = [
            {
                "type": "image_file",
                "image_file": {
                    "file_id": uploaded_file.id,
                    "detail": "high"
                }
            }
        ]
        
        # Add text if caption provided
        if caption.strip():
            message_content.insert(0, {
                "type": "text",
                "text": caption
            })
        
        # Add message to thread without running the assistant
        await client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_content
        )
        
        logger.debug(f"Added image to context for {chat_identifier} (file_id: {uploaded_file.id})")
        
    except Exception as e:
        logger.error(f"Error adding image to context for {chat_identifier}: {e}")


async def send_message_and_get_response_for_chat(chat_identifier: str, user_message: str, username: str = None, user_id: int = None) -> str:
    """
    Dual-mode version of send_message_and_get_response that works with chat identifiers.
    
    Args:
        chat_identifier: Either "user:USER_ID" or "chat:CHAT_ID"
        user_message: Message text from user
        username: Username for analytics
        user_id: User ID for analytics (required for group chats)
    
    Returns:
        str: Assistant response
    """
    thread_id = get_thread_id_for_chat(chat_identifier)
    if not thread_id:
        thread_id = await create_thread()
        set_thread_id_for_chat(chat_identifier, thread_id)

    # Добавляем сообщение пользователя
    await client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    # Запускаем выполнение
    run = await client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID,
    )

    # Ожидаем завершения
    while True:
        run_status = await client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        if run_status.status in ["completed", "failed", "cancelled"]:
            break
        await asyncio.sleep(1)

    # Проверка статуса выполнения
    if run_status.status == "failed":
        logger.error(f"[OpenAI] Assistant run failed for {chat_identifier}: {run_status.last_error}")
        return "❌ Ошибка при обработке запроса. Попробуйте еще раз."
    
    if run_status.status == "cancelled":
        logger.error(f"[OpenAI] Assistant run cancelled for {chat_identifier}")
        return "❌ Запрос был отменен. Попробуйте еще раз."
    
    if run_status.status == "requires_action":
        logger.warning(f"[OpenAI] Assistant requires action for {chat_identifier} - this is not supported")
        return "❌ Запрос требует дополнительных действий, которые не поддерживаются."

    # Записываем использование токенов в аналитику
    tokens_used = 0
    if run_status.usage and run_status.usage.total_tokens:
        tokens_used = run_status.usage.total_tokens
        logger.debug(f"[OpenAI] Tokens used for {chat_identifier}: {tokens_used} (prompt: {run_status.usage.prompt_tokens}, completion: {run_status.usage.completion_tokens})")
    
    # Записываем в аналитику (используем user_id если доступен, иначе извлекаем из chat_identifier)
    if tokens_used > 0:
        try:
            analytics_user_id = user_id
            if not analytics_user_id and chat_identifier.startswith("user:"):
                analytics_user_id = int(chat_identifier.split(":")[1])
            
            if analytics_user_id:
                await analytics.record_usage(analytics_user_id, username, tokens_used)
        except Exception as e:
            logger.error(f"Failed to record usage analytics for {chat_identifier}: {e}")

    # Получаем только новые сообщения
    messages = await client.beta.threads.messages.list(thread_id=thread_id)
    
    # Логирование для диагностики (БЕЗ содержимого сообщений!)
    logger.debug(f"[OpenAI] Retrieved {len(messages.data)} messages for {chat_identifier}")
    logger.debug(f"[OpenAI] Run created at: {run.created_at}, status: {run_status.status}")
    
    assistant_messages_count = 0
    for message in reversed(messages.data):
        if message.role == "assistant":
            assistant_messages_count += 1
        
        if (
            message.role == "assistant" and
            message.created_at >= run.created_at
        ):
            reply = message.content[0].text.value
            logger.info(f"[OpenAI] Response sent for {chat_identifier}")
            return reply
    
    # Логирование деталей если не найден подходящий ответ (БЕЗ содержимого!)
    logger.warning(f"[OpenAI] No suitable response found for {chat_identifier}")
    logger.warning(f"[OpenAI] Run status: {run_status.status}")
    logger.warning(f"[OpenAI] Assistant messages found: {assistant_messages_count}")
    logger.warning(f"[OpenAI] Run created_at: {run.created_at}")

    return "Ошибка: не удалось получить ответ."


async def get_message_history(user_id: int, limit: int = 10) -> str:
    thread_id = get_thread_id(user_id)
    if not thread_id:
        return "История пуста. Вы ещё не начинали диалог."

    try:
        messages = await client.beta.threads.messages.list(thread_id=thread_id, limit=limit)
        history = []
        for message in reversed(messages.data):  # от старых к новым
            role = "🤖" if message.role == "assistant" else "🧑"
            content = message.content[0].text.value.strip()
            history.append(f"{role}: {content}")
        return "\n\n".join(history) if history else "История пуста."
    except Exception as e:
        logger.error(f"Ошибка при получении истории сообщений: {e}")
        return "Ошибка при получении истории."

async def export_message_history(user_id: int, limit: int = 50) -> str | None:
    thread_id = get_thread_id(user_id)
    if not thread_id:
        return None

    try:
        messages = await client.beta.threads.messages.list(thread_id=thread_id, limit=limit)
        history = []
        for message in reversed(messages.data):
            role = "Assistant" if message.role == "assistant" else "User"
            content = message.content[0].text.value.strip()
            history.append(f"{role}: {content}")

        if not history:
            return None

        with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", suffix=".txt") as f:
            f.write("\n\n".join(history))
            return f.name

    except Exception as e:
        logger.error(f"Ошибка при экспорте истории: {e}")
        return None

async def send_image_and_get_response(user_id: int, image_path: str, caption: str = "", username: str = None) -> str:
    """Process image with optional text caption using OpenAI Assistant"""
    thread_id = get_thread_id(user_id)
    if not thread_id:
        thread_id = await create_thread()
        set_thread_id(user_id, thread_id)

    try:
        # Upload image file to OpenAI with purpose="vision"
        with open(image_path, "rb") as image_file:
            uploaded_file = await client.files.create(
                file=image_file,
                purpose="vision"
            )
        
        # Save file_id in Redis for tracking
        add_user_image(user_id, uploaded_file.id)
        
        # Create message content with uploaded file
        message_content = [
            {
                "type": "image_file",
                "image_file": {
                    "file_id": uploaded_file.id,
                    "detail": "high"
                }
            }
        ]
        
        # Add text if caption provided
        if caption.strip():
            message_content.insert(0, {
                "type": "text",
                "text": caption
            })
        else:
            # Default prompt for image analysis  
            message_content.insert(0, {
                "type": "text", 
                "text": "Проанализируй это изображение и опиши что на нем изображено."
            })

        # Add message to thread
        await client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_content
        )

        # Run assistant
        run = await client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
        )

        # Wait for completion
        while True:
            run_status = await client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            if run_status.status in ["completed", "failed", "cancelled"]:
                break
            await asyncio.sleep(1)

        # Check for errors
        if run_status.status == "failed":
            logger.error(f"Assistant run failed: {run_status.last_error}")
            return "❌ Ошибка при анализе изображения. Попробуйте еще раз."
        
        if run_status.status == "cancelled":
            logger.error(f"[OpenAI] Assistant run cancelled for user {user_id}")
            return "❌ Запрос был отменен. Попробуйте еще раз."
        
        if run_status.status == "requires_action":
            logger.warning(f"[OpenAI] Assistant requires action for user {user_id} - this is not supported")
            return "❌ Запрос требует дополнительных действий, которые не поддерживаются."

        # Record token usage
        tokens_used = 0
        if run_status.usage and run_status.usage.total_tokens:
            tokens_used = run_status.usage.total_tokens
            logger.debug(f"[OpenAI] Image processing tokens used: {tokens_used}")
        
        # Record analytics
        if tokens_used > 0:
            try:
                await analytics.record_usage(user_id, username, tokens_used)
            except Exception as e:
                logger.error(f"Failed to record usage analytics: {e}")

        # Get response
        messages = await client.beta.threads.messages.list(thread_id=thread_id)

        for message in reversed(messages.data):
            if (
                message.role == "assistant" and
                message.created_at >= run.created_at
            ):
                reply = message.content[0].text.value
                logger.info(f"[OpenAI] Image analysis completed for user {user_id}")
                
                # Файл НЕ удаляется сразу - будет удален при команде /reset
                logger.debug(f"File {uploaded_file.id} stored for user {user_id}, will be cleaned on /reset")
                
                return reply

        return "Ошибка: не удалось получить ответ на изображение."

    except Exception as e:
        logger.error(f"Error processing image for user {user_id}: {e}")
        return "❌ Произошла ошибка при анализе изображения. Попробуйте еще раз."


async def send_image_and_get_response_for_chat(chat_identifier: str, image_path: str, caption: str = "", username: str = None, user_id: int = None) -> str:
    """
    Dual-mode version of send_image_and_get_response that works with chat identifiers.
    
    Args:
        chat_identifier: Either "user:USER_ID" or "chat:CHAT_ID"
        image_path: Path to the image file
        caption: Optional caption text
        username: Username for analytics
        user_id: User ID for analytics (required for group chats)
    
    Returns:
        str: Assistant response
    """
    thread_id = get_thread_id_for_chat(chat_identifier)
    if not thread_id:
        thread_id = await create_thread()
        set_thread_id_for_chat(chat_identifier, thread_id)

    try:
        # Upload image file to OpenAI with purpose="vision"
        with open(image_path, "rb") as image_file:
            uploaded_file = await client.files.create(
                file=image_file,
                purpose="vision"
            )
        
        # Save file_id in Redis for tracking
        add_chat_image(chat_identifier, uploaded_file.id)
        
        # Create message content with uploaded file
        message_content = [
            {
                "type": "image_file",
                "image_file": {
                    "file_id": uploaded_file.id,
                    "detail": "high"
                }
            }
        ]
        
        # Add text if caption provided
        if caption.strip():
            message_content.insert(0, {
                "type": "text",
                "text": caption
            })
        else:
            # Default prompt for image analysis  
            message_content.insert(0, {
                "type": "text", 
                "text": "Проанализируй это изображение и опиши что на нем изображено."
            })

        # Add message to thread
        await client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_content
        )

        # Run assistant
        run = await client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
        )

        # Wait for completion
        while True:
            run_status = await client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            if run_status.status in ["completed", "failed", "cancelled"]:
                break
            await asyncio.sleep(1)

        # Check for errors
        if run_status.status == "failed":
            logger.error(f"Assistant run failed: {run_status.last_error}")
            return "❌ Ошибка при анализе изображения. Попробуйте еще раз."
        
        if run_status.status == "cancelled":
            logger.error(f"[OpenAI] Assistant run cancelled for {chat_identifier}")
            return "❌ Запрос был отменен. Попробуйте еще раз."
        
        if run_status.status == "requires_action":
            logger.warning(f"[OpenAI] Assistant requires action for {chat_identifier} - this is not supported")
            return "❌ Запрос требует дополнительных действий, которые не поддерживаются."

        # Record token usage
        tokens_used = 0
        if run_status.usage and run_status.usage.total_tokens:
            tokens_used = run_status.usage.total_tokens
            logger.debug(f"[OpenAI] Image processing tokens used for {chat_identifier}: {tokens_used}")
        
        # Record analytics (using user_id if available)
        if tokens_used > 0:
            try:
                analytics_user_id = user_id
                if not analytics_user_id and chat_identifier.startswith("user:"):
                    analytics_user_id = int(chat_identifier.split(":")[1])
                
                if analytics_user_id:
                    await analytics.record_usage(analytics_user_id, username, tokens_used)
            except Exception as e:
                logger.error(f"Failed to record usage analytics for {chat_identifier}: {e}")

        # Get response
        messages = await client.beta.threads.messages.list(thread_id=thread_id)

        for message in reversed(messages.data):
            if (
                message.role == "assistant" and
                message.created_at >= run.created_at
            ):
                reply = message.content[0].text.value
                logger.info(f"[OpenAI] Image analysis completed for {chat_identifier}")
                
                # File НЕ удаляется сразу - will be cleaned on /reset
                logger.debug(f"File {uploaded_file.id} stored for {chat_identifier}, will be cleaned on /reset")
                
                return reply

        return "Ошибка: не удалось получить ответ на изображение."

    except Exception as e:
        logger.error(f"Error processing image for {chat_identifier}: {e}")
        return "❌ Произошла ошибка при анализе изображения. Попробуйте еще раз."


async def send_document_and_get_response(user_id: int, local_file_path: str, user_message: str = "", original_filename: str = "", username: str = None) -> str:
    """Process document with optional text message using OpenAI Assistant"""
    thread_id = get_thread_id(user_id)
    if not thread_id:
        thread_id = await create_thread()
        set_thread_id(user_id, thread_id)

    try:
        # Upload document file to OpenAI with purpose="assistants"
        with open(local_file_path, "rb") as document_file:
            uploaded_file = await client.files.create(
                file=document_file,
                purpose="assistants"
            )
        
        # Track file for cleanup - use separate function for documents
        add_user_document(user_id, uploaded_file.id, original_filename)
        
        # Create message content
        if user_message.strip():
            # User provided a specific question/instruction
            message_text = f"Analyze the attached document '{original_filename}' and answer the following question: {user_message}"
        else:
            # Default analysis prompt
            message_text = f"Please analyze the attached document '{original_filename}' and provide a comprehensive summary of its content, key points, and main topics."

        # Add message to thread
        await client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_text,
            attachments=[
                {
                    "file_id": uploaded_file.id,
                    "tools": [{"type": "file_search"}]
                }
            ]
        )

        # Run assistant
        run = await client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
        )

        # Wait for completion
        while True:
            run_status = await client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            if run_status.status in ["completed", "failed", "cancelled"]:
                break
            await asyncio.sleep(1)

        # Check for errors
        if run_status.status == "failed":
            logger.error(f"Assistant run failed: {run_status.last_error}")
            return "❌ Ошибка при анализе документа. Попробуйте еще раз."
        
        if run_status.status == "cancelled":
            logger.error(f"[OpenAI] Assistant run cancelled for user {user_id}")
            return "❌ Запрос был отменен. Попробуйте еще раз."
        
        if run_status.status == "requires_action":
            logger.warning(f"[OpenAI] Assistant requires action for user {user_id} - this is not supported")
            return "❌ Запрос требует дополнительных действий, которые не поддерживаются."

        # Record token usage
        tokens_used = 0
        if run_status.usage and run_status.usage.total_tokens:
            tokens_used = run_status.usage.total_tokens
            logger.debug(f"[OpenAI] Document processing tokens used: {tokens_used}")
        
        # Record analytics
        if tokens_used > 0:
            try:
                await analytics.record_usage(user_id, username, tokens_used)
            except Exception as e:
                logger.error(f"Failed to record usage analytics: {e}")

        # Get response
        messages = await client.beta.threads.messages.list(thread_id=thread_id)

        for message in reversed(messages.data):
            if (
                message.role == "assistant" and
                message.created_at >= run.created_at
            ):
                reply = message.content[0].text.value
                logger.info(f"[OpenAI] Document analysis completed for user {user_id}")
                
                # File will be cleaned up during /reset
                logger.debug(f"Document file {uploaded_file.id} stored for user {user_id}, will be cleaned on /reset")
                
                return reply

        return "Ошибка: не удалось получить ответ при анализе документа."

    except Exception as document_processing_error:
        logger.error(f"Error processing document for user {user_id}: {document_processing_error}")
        return "❌ Ошибка при анализе документа. Попробуйте еще раз."


# ===== IMAGE GENERATION FUNCTIONS =====

# Error mapping for DALL-E API
ERROR_MESSAGES = {
    400: "❌ Invalid request. Please check your image description",
    401: "❌ API authentication failed",
    403: "❌ Access denied",
    422: "❌ Request violates OpenAI content policy",
    429: "❌ Rate limit exceeded. Please try again later",
    500: "❌ OpenAI server error. Please try again"
}

async def handle_api_error(error: openai.APIStatusError) -> str:
    """Maps API errors to user-friendly messages"""
    return ERROR_MESSAGES.get(error.status_code, f"❌ API error: {error.status_code}")

async def detect_image_generation_request(message: str) -> bool:
    """Detects image generation requests using regex patterns"""
    generation_patterns = [
        r'\b(нарисуй|создай картинку|сгенерируй изображение)\b',
        r'\b(draw|generate image|create picture)\b',
        r'\b(рисунок|картинка|фото)\s+.{3,}',  # At least 3 characters after the word
        r'^(изображение|картинка)\s',
    ]
    
    return any(re.search(pattern, message.lower()) for pattern in generation_patterns)

async def generate_image_dalle(prompt: str, user_id: int, username: str = None, 
                              size: str = "1024x1024") -> tuple[str, int]:
    """
    Generates image using DALL-E 3 API
    Returns: (image_url, equivalent_tokens)
    """
    try:
        logger.info(f"[DALL-E] Starting image generation for user {user_id}")
        
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size=size,
            quality="standard",
            style="vivid"
        )
        
        image_url = response.data[0].url
        
        # Get equivalent tokens from analytics module
        from user_analytics import DALLE_TOKEN_EQUIVALENT
        equivalent_tokens = DALLE_TOKEN_EQUIVALENT.get(size, 400)
        
        logger.info(f"[DALL-E] Successfully generated image for user {user_id}")
        logger.debug(f"[DALL-E] Image URL: {image_url}")
        
        # Record analytics using enhanced method
        if username:
            try:
                await analytics.record_image_generation(user_id, username, size)
                logger.debug(f"[DALL-E] Recorded analytics: {equivalent_tokens} tokens for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to record image generation analytics: {e}")
        
        return image_url, equivalent_tokens
        
    except openai.APIConnectionError as e:
        logger.error(f"[DALL-E] Connection error for user {user_id}: {e}")
        raise Exception("Connection to OpenAI failed")
    except openai.RateLimitError as e:
        logger.error(f"[DALL-E] Rate limit error for user {user_id}: {e}")
        raise Exception("Rate limit exceeded. Please try again in a few minutes")
    except openai.APIStatusError as e:
        logger.error(f"[DALL-E] API status error for user {user_id}: {e.status_code} - {e}")
        if e.status_code == 400:
            raise Exception("Invalid image description")
        elif e.status_code == 422:
            raise Exception("Request violates OpenAI safety policies")
        else:
            raise Exception(f"API error: {e.status_code}")
    except Exception as e:
        logger.error(f"[DALL-E] Unexpected error for user {user_id}: {e}")
        raise Exception(f"Unexpected error during image generation: {str(e)}")