import asyncio
from config import OPENAI_API_KEY, ASSISTANT_ID
from session_manager import get_thread_id, set_thread_id
from logger import logger
from openai import AsyncOpenAI
import tempfile

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def create_thread():
    thread = await client.beta.threads.create()
    return thread.id

async def send_message_and_get_response(user_id: int, user_message: str) -> str:
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