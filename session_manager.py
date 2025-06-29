import redis # type: ignore
from config import REDIS_HOST, REDIS_PORT, REDIS_DB
from logger import logger

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

SESSION_PREFIX = "thread_id:"
IMAGES_PREFIX = "user_images:"  # Prefix for user images
DOCUMENTS_PREFIX = "user_documents:"  # Prefix for user documents

def _key(user_id: int) -> str:
    return f"{SESSION_PREFIX}{user_id}"

def _images_key(user_id: int) -> str:
    return f"{IMAGES_PREFIX}{user_id}"

def _documents_key(user_id: int) -> str:
    return f"{DOCUMENTS_PREFIX}{user_id}"

def get_thread_id(user_id: int) -> str | None:
    try:
        return r.get(_key(user_id))
    except Exception as e:
        logger.error(f"Redis error in get_thread_id: {e}")
        return None

def set_thread_id(user_id: int, thread_id: str):
    try:
        r.set(_key(user_id), thread_id)
    except Exception as e:
        logger.error(f"Redis error in set_thread_id: {e}")

# === IMAGE MANAGEMENT FUNCTIONS ===
def add_user_image(user_id: int, file_id: str):
    """Adds image file_id to user's image list"""
    try:
        r.sadd(_images_key(user_id), file_id)
        logger.debug(f"Added image {file_id} for user {user_id}")
    except Exception as e:
        logger.error(f"Redis error in add_user_image: {e}")

def get_user_images(user_id: int) -> list[str]:
    """Gets all image file_ids for user"""
    try:
        images = r.smembers(_images_key(user_id))
        return list(images) if images else []
    except Exception as e:
        logger.error(f"Redis error in get_user_images: {e}")
        return []

def clear_user_images(user_id: int):
    """Clears user's image list"""
    try:
        r.delete(_images_key(user_id))
        logger.debug(f"Cleared images list for user {user_id}")
    except Exception as e:
        logger.error(f"Redis error in clear_user_images: {e}")

# === DOCUMENT MANAGEMENT FUNCTIONS ===
def add_user_document(user_id: int, file_id: str, original_filename: str = ""):
    """Adds document file_id to user's document list with metadata"""
    try:
        # Store both file_id and filename as a hash
        document_data = {"file_id": file_id, "filename": original_filename}
        r.hset(f"{_documents_key(user_id)}:{file_id}", mapping=document_data)
        logger.debug(f"Added document {file_id} ({original_filename}) for user {user_id}")
    except Exception as e:
        logger.error(f"Redis error in add_user_document: {e}")

def get_user_documents(user_id: int) -> list[dict]:
    """Gets all user documents with their metadata"""
    try:
        keys = r.keys(f"{_documents_key(user_id)}:*")
        documents = []
        for key in keys:
            doc_data = r.hgetall(key)
            if doc_data:
                documents.append({
                    "file_id": doc_data.get("file_id", ""),
                    "filename": doc_data.get("filename", "")
                })
        return documents
    except Exception as e:
        logger.error(f"Redis error in get_user_documents: {e}")
        return []

def clear_user_documents(user_id: int):
    """Clears user's document list"""
    try:
        keys = r.keys(f"{_documents_key(user_id)}:*")
        if keys:
            r.delete(*keys)
        logger.debug(f"Cleared documents list for user {user_id}")
    except Exception as e:
        logger.error(f"Redis error in clear_user_documents: {e}")

async def delete_user_documents_from_openai(user_id: int):
    """Deletes all user documents from OpenAI storage"""
    from openai import AsyncOpenAI
    from config import OPENAI_API_KEY
    
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    documents_to_delete = get_user_documents(user_id)
    
    if not documents_to_delete:
        logger.debug(f"No documents to delete for user {user_id}")
        return
    
    deleted_count = 0
    for doc in documents_to_delete:
        file_id = doc.get("file_id")
        original_filename = doc.get("filename", "unknown")
        if file_id:
            try:
                await client.files.delete(file_id)
                deleted_count += 1
                logger.debug(f"Deleted document {file_id} ({original_filename}) for user {user_id}")
            except Exception as doc_delete_error:
                logger.warning(f"Failed to delete document {file_id} ({original_filename}) for user {user_id}: {doc_delete_error}")
    
    # Clear list after deletion
    clear_user_documents(user_id)
    logger.info(f"Deleted {deleted_count} documents for user {user_id} on reset")

async def delete_user_images_from_openai(user_id: int):
    """Deletes all user images from OpenAI storage"""
    from openai import AsyncOpenAI
    from config import OPENAI_API_KEY
    
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    images_to_delete = get_user_images(user_id)
    
    if not images_to_delete:
        logger.debug(f"No images to delete for user {user_id}")
        return
    
    deleted_count = 0
    for file_id in images_to_delete:
        try:
            await client.files.delete(file_id)
            deleted_count += 1
            logger.debug(f"Deleted image {file_id} for user {user_id}")
        except Exception as image_delete_error:
            logger.warning(f"Failed to delete image {file_id} for user {user_id}: {image_delete_error}")
    
    # Clear list after deletion
    clear_user_images(user_id)
    logger.info(f"Deleted {deleted_count} images for user {user_id} on reset")

async def reset_thread(user_id: int):
    """Resets thread and deletes all user images and documents"""
    try:
        # Delete images from OpenAI
        await delete_user_images_from_openai(user_id)
        
        # Delete documents from OpenAI
        await delete_user_documents_from_openai(user_id)
        
        # Delete thread_id
        r.delete(_key(user_id))
        
        logger.info(f"Reset complete for user {user_id}: thread, images, and documents cleared")
    except Exception as reset_error:
        logger.error(f"Error in reset_thread: {reset_error}")

# Keep synchronous version for compatibility
def reset_thread_sync(user_id: int):
    """Synchronous version of reset (thread_id only, no files)"""
    try:
        r.delete(_key(user_id))
    except Exception as sync_reset_error:
        logger.error(f"Redis error in reset_thread_sync: {sync_reset_error}")
