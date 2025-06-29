import redis # type: ignore
from config import REDIS_HOST, REDIS_PORT, REDIS_DB
from logger import logger

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

# Legacy prefixes for backward compatibility
SESSION_PREFIX = "thread_id:"
IMAGES_PREFIX = "user_images:"  
DOCUMENTS_PREFIX = "user_documents:"

# New prefixes for dual-mode operation
THREAD_PREFIX = "thread:"  # New unified prefix for both user and chat threads
CHAT_IMAGES_PREFIX = "chat_images:"
CHAT_DOCUMENTS_PREFIX = "chat_documents:"

def _key(user_id: int) -> str:
    """Legacy key format for backward compatibility"""
    return f"{SESSION_PREFIX}{user_id}"

def _images_key(user_id: int) -> str:
    """Legacy images key format for backward compatibility"""
    return f"{IMAGES_PREFIX}{user_id}"

def _documents_key(user_id: int) -> str:
    """Legacy documents key format for backward compatibility"""
    return f"{DOCUMENTS_PREFIX}{user_id}"

def _thread_key(identifier: str) -> str:
    """New unified thread key format for dual-mode operation"""
    return f"{THREAD_PREFIX}{identifier}"

def _chat_images_key(identifier: str) -> str:
    """Images key for chat-based sessions"""
    return f"{CHAT_IMAGES_PREFIX}{identifier}"

def _chat_documents_key(identifier: str) -> str:
    """Documents key for chat-based sessions"""
    return f"{CHAT_DOCUMENTS_PREFIX}{identifier}"

# === DUAL-MODE SESSION MANAGEMENT ===

def get_thread_id_for_chat(chat_identifier: str) -> str | None:
    """
    Gets thread ID for any chat context (user or group).
    
    Args:
        chat_identifier: Either "user:USER_ID" or "chat:CHAT_ID"
        
    Returns:
        str | None: Thread ID if exists, None otherwise
    """
    try:
        # Try new format first
        thread_id = r.get(_thread_key(chat_identifier))
        if thread_id:
            return thread_id
        
        # Fallback to legacy format for user sessions
        if chat_identifier.startswith("user:"):
            user_id = int(chat_identifier.split(":")[1])
            return r.get(_key(user_id))
        
        return None
    except Exception as e:
        logger.error(f"Redis error in get_thread_id_for_chat: {e}")
        return None

def set_thread_id_for_chat(chat_identifier: str, thread_id: str):
    """
    Sets thread ID for any chat context (user or group).
    
    Args:
        chat_identifier: Either "user:USER_ID" or "chat:CHAT_ID"
        thread_id: OpenAI thread ID
    """
    try:
        r.set(_thread_key(chat_identifier), thread_id)
        
        # Also set in legacy format for user sessions (backward compatibility)
        if chat_identifier.startswith("user:"):
            user_id = int(chat_identifier.split(":")[1])
            r.set(_key(user_id), thread_id)
            
        logger.debug(f"Set thread_id {thread_id} for {chat_identifier}")
    except Exception as e:
        logger.error(f"Redis error in set_thread_id_for_chat: {e}")

# === LEGACY FUNCTIONS (for backward compatibility) ===

def get_thread_id(user_id: int) -> str | None:
    """Legacy function - maintained for backward compatibility"""
    return get_thread_id_for_chat(f"user:{user_id}")

def set_thread_id(user_id: int, thread_id: str):
    """Legacy function - maintained for backward compatibility"""
    set_thread_id_for_chat(f"user:{user_id}", thread_id)

# === DUAL-MODE FILE MANAGEMENT ===

def add_chat_image(chat_identifier: str, file_id: str):
    """Adds image file_id to chat's image list"""
    try:
        r.sadd(_chat_images_key(chat_identifier), file_id)
        
        # Also add to legacy format for user sessions
        if chat_identifier.startswith("user:"):
            user_id = int(chat_identifier.split(":")[1])
            r.sadd(_images_key(user_id), file_id)
            
        logger.debug(f"Added image {file_id} for {chat_identifier}")
    except Exception as e:
        logger.error(f"Redis error in add_chat_image: {e}")

def get_chat_images(chat_identifier: str) -> list[str]:
    """Gets all image file_ids for chat"""
    try:
        # Try new format first
        images = r.smembers(_chat_images_key(chat_identifier))
        if images:
            return list(images)
        
        # Fallback to legacy format for user sessions
        if chat_identifier.startswith("user:"):
            user_id = int(chat_identifier.split(":")[1])
            legacy_images = r.smembers(_images_key(user_id))
            return list(legacy_images) if legacy_images else []
        
        return []
    except Exception as e:
        logger.error(f"Redis error in get_chat_images: {e}")
        return []

def clear_chat_images(chat_identifier: str):
    """Clears chat's image list"""
    try:
        r.delete(_chat_images_key(chat_identifier))
        
        # Also clear legacy format for user sessions
        if chat_identifier.startswith("user:"):
            user_id = int(chat_identifier.split(":")[1])
            r.delete(_images_key(user_id))
            
        logger.debug(f"Cleared images list for {chat_identifier}")
    except Exception as e:
        logger.error(f"Redis error in clear_chat_images: {e}")

def add_chat_document(chat_identifier: str, file_id: str, original_filename: str = ""):
    """Adds document file_id to chat's document list with metadata"""
    try:
        # Store both file_id and filename as a hash
        document_data = {"file_id": file_id, "filename": original_filename}
        r.hset(f"{_chat_documents_key(chat_identifier)}:{file_id}", mapping=document_data)
        
        # Also add to legacy format for user sessions
        if chat_identifier.startswith("user:"):
            user_id = int(chat_identifier.split(":")[1])
            r.hset(f"{_documents_key(user_id)}:{file_id}", mapping=document_data)
        
        logger.debug(f"Added document {file_id} ({original_filename}) for {chat_identifier}")
    except Exception as e:
        logger.error(f"Redis error in add_chat_document: {e}")

def get_chat_documents(chat_identifier: str) -> list[dict]:
    """Gets all chat documents with their metadata"""
    try:
        # Try new format first
        keys = r.keys(f"{_chat_documents_key(chat_identifier)}:*")
        if keys:
            documents = []
            for key in keys:
                doc_data = r.hgetall(key)
                if doc_data:
                    documents.append({
                        "file_id": doc_data.get("file_id", ""),
                        "filename": doc_data.get("filename", "")
                    })
            return documents
        
        # Fallback to legacy format for user sessions
        if chat_identifier.startswith("user:"):
            user_id = int(chat_identifier.split(":")[1])
            legacy_keys = r.keys(f"{_documents_key(user_id)}:*")
            documents = []
            for key in legacy_keys:
                doc_data = r.hgetall(key)
                if doc_data:
                    documents.append({
                        "file_id": doc_data.get("file_id", ""),
                        "filename": doc_data.get("filename", "")
                    })
            return documents
        
        return []
    except Exception as e:
        logger.error(f"Redis error in get_chat_documents: {e}")
        return []

def clear_chat_documents(chat_identifier: str):
    """Clears chat's document list"""
    try:
        # Clear new format
        keys = r.keys(f"{_chat_documents_key(chat_identifier)}:*")
        if keys:
            r.delete(*keys)
        
        # Also clear legacy format for user sessions
        if chat_identifier.startswith("user:"):
            user_id = int(chat_identifier.split(":")[1])
            legacy_keys = r.keys(f"{_documents_key(user_id)}:*")
            if legacy_keys:
                r.delete(*legacy_keys)
                
        logger.debug(f"Cleared documents list for {chat_identifier}")
    except Exception as e:
        logger.error(f"Redis error in clear_chat_documents: {e}")

async def delete_chat_documents_from_openai(chat_identifier: str):
    """Deletes all chat documents from OpenAI storage"""
    from openai import AsyncOpenAI
    from config import OPENAI_API_KEY
    
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    documents_to_delete = get_chat_documents(chat_identifier)
    
    if not documents_to_delete:
        logger.debug(f"No documents to delete for {chat_identifier}")
        return
    
    deleted_count = 0
    for doc in documents_to_delete:
        file_id = doc.get("file_id")
        original_filename = doc.get("filename", "unknown")
        if file_id:
            try:
                await client.files.delete(file_id)
                deleted_count += 1
                logger.debug(f"Deleted document {file_id} ({original_filename}) for {chat_identifier}")
            except Exception as doc_delete_error:
                logger.warning(f"Failed to delete document {file_id} ({original_filename}) for {chat_identifier}: {doc_delete_error}")
    
    # Clear list after deletion
    clear_chat_documents(chat_identifier)
    logger.info(f"Deleted {deleted_count} documents for {chat_identifier} on reset")

async def delete_chat_images_from_openai(chat_identifier: str):
    """Deletes all chat images from OpenAI storage"""
    from openai import AsyncOpenAI
    from config import OPENAI_API_KEY
    
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    images_to_delete = get_chat_images(chat_identifier)
    
    if not images_to_delete:
        logger.debug(f"No images to delete for {chat_identifier}")
        return
    
    deleted_count = 0
    for file_id in images_to_delete:
        try:
            await client.files.delete(file_id)
            deleted_count += 1
            logger.debug(f"Deleted image {file_id} for {chat_identifier}")
        except Exception as image_delete_error:
            logger.warning(f"Failed to delete image {file_id} for {chat_identifier}: {image_delete_error}")
    
    # Clear list after deletion
    clear_chat_images(chat_identifier)
    logger.info(f"Deleted {deleted_count} images for {chat_identifier} on reset")

async def reset_chat_thread(chat_identifier: str):
    """Resets thread and deletes all chat images and documents"""
    try:
        # Delete images from OpenAI
        await delete_chat_images_from_openai(chat_identifier)
        
        # Delete documents from OpenAI
        await delete_chat_documents_from_openai(chat_identifier)
        
        # Delete thread_id (both new and legacy formats)
        r.delete(_thread_key(chat_identifier))
        if chat_identifier.startswith("user:"):
            user_id = int(chat_identifier.split(":")[1])
            r.delete(_key(user_id))
        
        logger.info(f"Reset complete for {chat_identifier}: thread, images, and documents cleared")
    except Exception as reset_error:
        logger.error(f"Error in reset_chat_thread: {reset_error}")

# === LEGACY FUNCTIONS (maintained for backward compatibility) ===

def add_user_image(user_id: int, file_id: str):
    """Legacy function - maintained for backward compatibility"""
    add_chat_image(f"user:{user_id}", file_id)

def get_user_images(user_id: int) -> list[str]:
    """Legacy function - maintained for backward compatibility"""
    return get_chat_images(f"user:{user_id}")

def clear_user_images(user_id: int):
    """Legacy function - maintained for backward compatibility"""
    clear_chat_images(f"user:{user_id}")

def add_user_document(user_id: int, file_id: str, original_filename: str = ""):
    """Legacy function - maintained for backward compatibility"""
    add_chat_document(f"user:{user_id}", file_id, original_filename)

def get_user_documents(user_id: int) -> list[dict]:
    """Legacy function - maintained for backward compatibility"""
    return get_chat_documents(f"user:{user_id}")

def clear_user_documents(user_id: int):
    """Legacy function - maintained for backward compatibility"""
    clear_chat_documents(f"user:{user_id}")

async def delete_user_documents_from_openai(user_id: int):
    """Legacy function - maintained for backward compatibility"""
    await delete_chat_documents_from_openai(f"user:{user_id}")

async def delete_user_images_from_openai(user_id: int):
    """Legacy function - maintained for backward compatibility"""
    await delete_chat_images_from_openai(f"user:{user_id}")

async def reset_thread(user_id: int):
    """Legacy function - maintained for backward compatibility"""
    await reset_chat_thread(f"user:{user_id}")

# Keep synchronous version for compatibility
def reset_thread_sync(user_id: int):
    """Synchronous version of reset (thread_id only, no files)"""
    try:
        r.delete(_key(user_id))
        r.delete(_thread_key(f"user:{user_id}"))
    except Exception as sync_reset_error:
        logger.error(f"Redis error in reset_thread_sync: {sync_reset_error}")
