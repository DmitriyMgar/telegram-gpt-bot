"""
Chat Detection System for Dual-Mode Bot Operation

This module provides functions to detect chat types and determine whether
the bot should respond in group/channel contexts based on mentions and replies.
"""

import re
from enum import Enum
from typing import Optional
from telegram import Update, Message
from logger import logger


class ChatType(Enum):
    """Enumeration of supported chat types"""
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


def get_chat_type(update: Update) -> ChatType:
    """
    Determines the chat type from the update.
    
    Args:
        update: Telegram Update object
        
    Returns:
        ChatType: The type of chat (private, group, supergroup, channel)
    """
    chat_type_str = update.effective_chat.type
    
    try:
        return ChatType(chat_type_str)
    except ValueError:
        logger.warning(f"Unknown chat type received: {chat_type_str}")
        # Default to group for unknown types
        return ChatType.GROUP


def is_private_chat(update: Update) -> bool:
    """
    Checks if the update is from a private chat.
    
    Args:
        update: Telegram Update object
        
    Returns:
        bool: True if private chat, False otherwise
    """
    return get_chat_type(update) == ChatType.PRIVATE


def is_group_chat(update: Update) -> bool:
    """
    Checks if the update is from a group or supergroup chat.
    
    Args:
        update: Telegram Update object
        
    Returns:
        bool: True if group/supergroup chat, False otherwise
    """
    chat_type = get_chat_type(update)
    return chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]


def is_bot_mentioned(update: Update, bot_username: str) -> bool:
    """
    Checks if the bot is mentioned in the message text or caption.
    
    Args:
        update: Telegram Update object
        bot_username: Bot username (without @)
        
    Returns:
        bool: True if bot is mentioned, False otherwise
    """
    if not update.message:
        return False
    
    # Check both text and caption (for photos/documents with captions)
    text_to_check = update.message.text or update.message.caption
    if not text_to_check:
        return False
    
    message_text = text_to_check.lower()
    bot_mention = f"@{bot_username.lower()}"
    
    # Check for @botusername mention
    if bot_mention in message_text:
        return True
    
    # Check for mentions in entities (more reliable)
    # Check both text entities and caption entities
    entities_to_check = []
    if update.message.entities:
        entities_to_check.extend(update.message.entities)
    if update.message.caption_entities:
        entities_to_check.extend(update.message.caption_entities)
    
    for entity in entities_to_check:
        if entity.type == "mention":
            # Extract the mention from the message text
            mention_text = message_text[entity.offset:entity.offset + entity.length]
            if mention_text == bot_mention:
                return True
    
    return False


def is_reply_to_bot(update: Update, bot_id: int) -> bool:
    """
    Checks if the message is a reply to a bot message.
    
    Args:
        update: Telegram Update object
        bot_id: Bot's Telegram ID
        
    Returns:
        bool: True if replying to bot, False otherwise
    """
    if not update.message or not update.message.reply_to_message:
        return False
    
    replied_message = update.message.reply_to_message
    
    # Check if the replied message is from the bot
    return (replied_message.from_user and 
            replied_message.from_user.id == bot_id)


def is_bot_command(update: Update) -> bool:
    """
    Checks if the message is a bot command (in text or caption).
    
    Args:
        update: Telegram Update object
        
    Returns:
        bool: True if message is a command, False otherwise
    """
    if not update.message:
        return False
    
    # Check both text and caption for commands
    text_to_check = update.message.text or update.message.caption
    if not text_to_check:
        return False
    
    # Check if message starts with /
    if text_to_check.startswith('/'):
        return True
    
    # Check for command entities in both text and caption
    entities_to_check = []
    if update.message.entities:
        entities_to_check.extend(update.message.entities)
    if update.message.caption_entities:
        entities_to_check.extend(update.message.caption_entities)
    
    for entity in entities_to_check:
        if entity.type == "bot_command":
            return True
    
    return False


def should_process_message(update: Update) -> bool:
    """
    Determines whether the bot should process a message for context.
    In groups, the bot should process ALL messages to maintain conversation context,
    but only respond when specifically addressed.
    
    Args:
        update: Telegram Update object
        
    Returns:
        bool: True if bot should process the message for context
    """
    chat_type = get_chat_type(update)
    
    # Always process messages in private chats
    if chat_type == ChatType.PRIVATE:
        return True
    
    # In groups, process all user messages (text, photos, documents, etc.)
    if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        # Skip if no message at all
        if not update.message:
            return False
        
        # Skip messages from other bots (unless it's a command to our bot)
        if update.message.from_user and update.message.from_user.is_bot:
            return is_bot_command(update)
        
        # Process text messages, photos, documents, etc.
        # Skip system messages (service messages have no from_user)
        return update.message.from_user is not None
    
    # For channels, only process commands
    if chat_type == ChatType.CHANNEL:
        return is_bot_command(update)
    
    # Default: don't process
    return False


def should_respond_in_chat(update: Update, bot_username: str, bot_id: int) -> bool:
    """
    Determines whether the bot should respond to a message based on chat type
    and message context. This is separate from processing - the bot can process
    messages for context without responding.
    
    Args:
        update: Telegram Update object
        bot_username: Bot username (without @)
        bot_id: Bot's Telegram ID
        
    Returns:
        bool: True if bot should respond, False otherwise
    """
    chat_type = get_chat_type(update)
    
    # Always respond in private chats
    if chat_type == ChatType.PRIVATE:
        return True
    
    # In group chats, respond only to:
    # 1. Messages that mention the bot
    # 2. Replies to bot messages
    # 3. Bot commands
    if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return (is_bot_mentioned(update, bot_username) or 
                is_reply_to_bot(update, bot_id) or 
                is_bot_command(update))
    
    # For channels, only respond to commands for now
    if chat_type == ChatType.CHANNEL:
        return is_bot_command(update)
    
    # Default: don't respond
    return False


def has_topic_thread(update: Update) -> bool:
    """
    Checks if the message is from a supergroup with forum topics enabled.
    
    Args:
        update: Telegram Update object
        
    Returns:
        bool: True if message has topic thread_id, False otherwise
    """
    if not update.message:
        return False
    
    # Check if message has message_thread_id (indicates supergroup topic)
    return hasattr(update.message, 'message_thread_id') and update.message.message_thread_id is not None


def get_topic_thread_id(update: Update) -> Optional[int]:
    """
    Gets the topic thread ID from the message if available.
    
    Args:
        update: Telegram Update object
        
    Returns:
        Optional[int]: Topic thread ID if available, None otherwise
    """
    if not update.message:
        return None
    
    return getattr(update.message, 'message_thread_id', None)


def get_chat_identifier(update: Update) -> str:
    """
    Gets a unique identifier for the chat context.
    Used for session management in dual-mode operation.
    Enhanced to support topic-based isolation in supergroups.
    
    Args:
        update: Telegram Update object
        
    Returns:
        str: Unique chat identifier for session management
        
    Examples:
        - Private chat: "user:123456789"
        - Regular group: "chat:-123456789"
        - Supergroup without topics: "chat:-123456789"
        - Supergroup with topics: "chat:-123456789:topic:5"
    """
    chat_type = get_chat_type(update)
    
    if chat_type == ChatType.PRIVATE:
        # For private chats, use user_id for backward compatibility
        return f"user:{update.effective_user.id}"
    else:
        # For group chats, use chat_id
        base_identifier = f"chat:{update.effective_chat.id}"
        
        # Check if this is a supergroup with topics
        if chat_type == ChatType.SUPERGROUP and has_topic_thread(update):
            topic_id = get_topic_thread_id(update)
            return f"{base_identifier}:topic:{topic_id}"
        
        return base_identifier


def get_log_context(update: Update) -> str:
    """
    Creates a contextual string for logging purposes.
    Enhanced to include topic information for supergroups.
    
    Args:
        update: Telegram Update object
        
    Returns:
        str: Formatted string for logging
        
    Examples:
        - Private: "[Private] user_123(@john)"
        - Group: "[Group] user_123(@john) in chat_-456(My Group)"
        - Supergroup: "[Supergroup] user_123(@john) in chat_-456(My Supergroup)"
        - Supergroup with topic: "[Supergroup] user_123(@john) in chat_-456(My Supergroup) | Topic: 5"
    """
    chat_type = get_chat_type(update)
    user = update.effective_user
    chat = update.effective_chat
    
    user_info = f"user_{user.id}"
    if user.username:
        user_info += f"(@{user.username})"
    
    if chat_type == ChatType.PRIVATE:
        return f"[Private] {user_info}"
    else:
        chat_info = f"chat_{chat.id}"
        if chat.title:
            chat_info += f"({chat.title})"
        
        base_context = f"[{chat_type.value.title()}] {user_info} in {chat_info}"
        
        # Add topic information for supergroups with topics
        if chat_type == ChatType.SUPERGROUP and has_topic_thread(update):
            topic_id = get_topic_thread_id(update)
            base_context += f" | Topic: {topic_id}"
        
        return base_context 