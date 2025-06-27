import asyncio
from config import OPENAI_API_KEY, ASSISTANT_ID
from session_manager import get_thread_id, set_thread_id
from logger import logger
from openai import AsyncOpenAI
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

    for message in reversed(messages.data):
        if (
            message.role == "assistant" and
            message.created_at >= run.created_at
        ):
            reply = message.content[0].text.value
            logger.info(f"[OpenAI] Reply to {user_id}: {reply}")
            return reply

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
                logger.info(f"[OpenAI] Image analysis reply to {user_id}: {reply[:100]}...")
                
                # Clean up the uploaded file to save storage
                try:
                    await client.files.delete(uploaded_file.id)
                    logger.debug(f"Cleaned up uploaded file: {uploaded_file.id}")
                except Exception as e:
                    logger.warning(f"Failed to delete uploaded file {uploaded_file.id}: {e}")
                
                return reply

        return "Ошибка: не удалось получить ответ на изображение."

    except Exception as e:
        logger.error(f"Error processing image for user {user_id}: {e}")
        return "❌ Произошла ошибка при анализе изображения. Попробуйте еще раз."