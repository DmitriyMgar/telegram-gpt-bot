# Telegram GPT Bot - Project Technical Documentation

## Project Overview

**Project Name:** Telegram GPT Bot  
**Version:** 1.8.2  
**Language:** Python 3.8+  
**Architecture:** Asynchronous, microservice-style modular design  
**Primary Purpose:** Channel-subscription-gated Telegram bot with OpenAI Assistant integration, DALL-E image generation, document processing, user analytics, comprehensive file handling, and **dual-mode operation** (private chats + group/channel administrator mode)

### Core Functionality
- **Dual-Mode Operation**: Bot operates in two distinct modes:
  - **Direct Mode**: Full AI chat functionality in private conversations
  - **Chat Participant Mode**: Responds to mentions (@botname) and replies in groups/channels
- **AI Chat Interface**: Users interact with OpenAI Assistant via Telegram
- **Document Processing**: Support for PDF, TXT, and DOCX files with AI analysis using OpenAI file_search
- **DALL-E Image Generation**: Text-to-image generation with natural language detection and explicit commands
- **Image Processing**: Support for image uploads with OpenAI Vision API integration
- **Channel-Based Authorization**: Access control through Telegram channel subscription verification
- **Persistent Conversations**: Redis-backed thread management for conversation continuity with per-chat threading
- **Export/History Features**: Chat history retrieval and export capabilities
- **User Analytics System**: Comprehensive token usage tracking and reporting for text, image generation, and document processing
- **Cost Control**: Real-time cost tracking and transparent pricing for all AI operations
- **File Management**: Comprehensive lifecycle management for images and documents with automatic cleanup
- **Caching System**: Intelligent Redis caching for subscription status optimization
- **Smart Message Filtering**: Context-aware response logic for group conversations
- **Network Error Resilience**: Automatic recovery from Telegram API outages with exponential backoff

---

## System Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram      │◄──►│   Bot Core       │◄──►│   OpenAI        │
│   Users         │    │   (main.py)      │    │   Assistant     │
│   (Private +    │    │   + Chat Detect  │    │                 │
│    Groups)      │    │   (chat_detector)│    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Authorization  │    │   DALL-E 3      │
                       │   System         │    │   Images API    │
                       │   (subscription) │    │                 │
                       └──────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  File Processing │    │  Document API   │
                       │ (Images + Docs)  │    │  (file_search)  │
                       │  Dual-Mode Mgmt  │    │                 │
                       └──────────────────┘    └─────────────────┘
                                │
                        ┌───────▼───────┐    ┌─────────────────┐
                        │     Redis     │    │   Analytics     │
                        │   (Cache &    │    │   Database      │
                        │  Sessions +   │    │   (SQLite)      │
                        │  Chat Threads)│    │                 │
                        └───────────────┘    └─────────────────┘
```

### Component Architecture
1. **Presentation Layer**: Telegram Bot API handlers (`main.py`) with dual-mode routing
2. **Business Logic Layer**: Authorization, session management, message processing, document processing, image processing, image generation, analytics, **chat detection system**
3. **Data Access Layer**: Redis for caching and sessions (user + chat-based), SQLite for analytics, temporary file storage
4. **External API Layer**: OpenAI Assistant API (text, vision, file_search), OpenAI Images API (DALL-E 3), Telegram Bot API, OpenAI File API
5. **Infrastructure Layer**: Logging, configuration, error handling, comprehensive file lifecycle management, cost tracking, **intelligent response filtering**

---

## File Structure & Modules

```
telegram-gpt-bot/
├── main.py                    # Entry point & Telegram handlers (dual-mode)
├── config.py                  # Configuration & environment variables
├── logger.py                  # Centralized logging setup
├── openai_handler.py          # OpenAI Assistant API integration (dual-mode)
├── session_manager.py         # Redis session management (user + chat-based)
├── subscription_checker.py    # Channel subscription verification
├── chat_detector.py           # Chat detection & response filtering (NEW)
├── user_analytics.py          # User analytics and token usage tracking
├── view_analytics.py          # Analytics viewing tool
├── requirements.txt           # Python dependencies
├── README.MD                  # Project documentation
├── .env                       # Environment variables (not tracked)
├── bot.log                    # Application logs
├── data/                      # Data storage directory
│   └── user_analytics.db      # SQLite analytics database
├── docs/                      # Documentation directory
│   ├── project-index.md       # This file
│   ├── progress.md            # Changelog & version history
│   └── working-cache.md       # Implementation planning docs
├── venv/                      # Python virtual environment
└── __pycache__/              # Python bytecode cache
```

---

## Core Modules Documentation

### 1. main.py - Bot Entry Point (Enhanced for Dual-Mode)
**Purpose**: Telegram bot handlers and application lifecycle management with dual-mode operation support

#### Key Functions:
- `init_bot_info()` - **NEW**: Initialize bot username and ID for mention detection
- `is_authorized_async(user_id: int) -> bool`
  - Async authorization check via channel subscription
  - Integrates with subscription_checker module
  - Returns True if user has access

- `start(update, context)` - Welcome handler with authorization and context-aware messaging
- `reset(update, context)` - Clear conversation thread and cleanup files (dual-mode)
- `handle_message(update, context)` - **ENHANCED**: Process user text messages with dual-mode routing
- `handle_photo(update, context)` - **ENHANCED**: Process user image uploads with dual-mode routing
- `handle_document(update, context)` - Process user document uploads (PDF, TXT, DOCX)
- `history(update, context)` - Retrieve conversation history
- `export(update, context)` - Export chat history as file
- `subscribe(update, context)` - Check subscription status

#### Dual-Mode Behavior with Topic Isolation:
| Chat Type                 | Response Logic                                    | Session Management                    |
|---------------------------|---------------------------------------------------|---------------------------------------|
| Private                   | Responds to all messages (unchanged)             | `user:{user_id}`                      |
| Group                     | Responds to mentions, replies, commands only     | `chat:{chat_id}`                      |
| Supergroup (no topics)   | Responds to mentions, replies, commands only     | `chat:{chat_id}`                      |
| Supergroup (with topics) | Responds to mentions, replies, commands only     | `chat:{chat_id}:topic:{thread_id}`    |
| Channel                   | Responds to commands only                        | `chat:{chat_id}`                      |

**🎯 Topic Isolation Enhancement**: Supergroups with forum topics now maintain separate conversation contexts for each topic, preventing context mixing between different discussion threads.

### 2. chat_detector.py - Chat Detection System (NEW)
**Purpose**: Intelligent chat type detection and response filtering for dual-mode operation

#### Key Functions:
- `get_chat_type(update) -> str`
  - Detects chat type: `private`, `group`, `supergroup`, `channel`
  - Returns string identifier for chat classification

- `is_bot_mentioned(text: str, bot_username: str) -> bool`
  - Checks for @botname mentions in message text
  - Handles various mention formats and positioning

- `is_reply_to_bot(update, bot_id: int) -> bool`
  - Detects if message is a reply to bot's previous message
  - Uses message threading for context detection

- `is_bot_command(text: str) -> bool`
  - Identifies bot commands (/, /start, /reset, etc.)
  - Returns True for command-style messages

- `should_respond_in_chat(update, bot_username: str, bot_id: int) -> bool`
  - **MAIN DECISION FUNCTION**: Determines if bot should respond
  - Combines chat type, mentions, replies, and commands
  - Core logic for dual-mode operation

- `should_process_message(update, bot_username: str, bot_id: int) -> bool`
  - **NEW**: Determines if bot should process message for context
  - Processes ALL group messages for conversation awareness
  - Separate from response logic for better context tracking

- `has_topic_thread(update) -> bool` - **NEW**
  - Checks if message is from a supergroup with forum topics enabled
  - Detects presence of `message_thread_id` field

- `get_topic_thread_id(update) -> Optional[int]` - **NEW** 
  - Extracts topic thread ID from supergroup forum messages
  - Returns None for non-topic messages

- `get_chat_identifier(update) -> str` - **ENHANCED**
  - Generates unique session identifiers for Redis storage with topic support
  - Formats: `user:{user_id}` for private, `chat:{chat_id}` for groups, `chat:{chat_id}:topic:{thread_id}` for supergroup topics

- `get_log_context(update) -> str` - **ENHANCED**
  - Creates contextual logging strings for debugging with topic information
  - Includes chat type, user info, message context, and topic ID for supergroups

### 3. openai_handler.py - OpenAI Integration (Enhanced for Dual-Mode)
**Purpose**: Manages OpenAI Assistant API interactions with dual-mode support

#### Key Functions (Existing):
- `create_thread() -> str`
- `send_message_and_get_response(user_id: int, message: str, username: str = None) -> str`
- `detect_image_generation_request(message: str) -> bool`
- `generate_image_dalle(prompt: str, user_id: int, username: str = None, size: str = "1024x1024") -> tuple[str, int]`
- `get_message_history(user_id: int, limit: int = 10) -> str`
- `export_message_history(user_id: int, limit: int = 50) -> str | None`
- `send_image_and_get_response(user_id: int, image_path: str, caption: str = "", username: str = None) -> str`
- `send_document_and_get_response(user_id: int, local_file_path: str, original_filename: str, user_question: str = "", username: str = None) -> str`

#### New Dual-Mode Functions:
- `send_message_and_get_response_for_chat(chat_identifier: str, message: str, user_id: int, username: str = None) -> str`
  - **NEW**: Chat-based message processing
  - Uses chat_identifier for session/thread management
  - Maintains per-chat conversation context
  - Integrates with analytics using original user_id

- `send_image_and_get_response_for_chat(chat_identifier: str, image_path: str, caption: str, user_id: int, username: str = None) -> str`
  - **NEW**: Chat-based image processing
  - Uses chat_identifier for session management
  - Supports dual-mode file tracking and cleanup

- `add_message_to_context(chat_identifier: str, message: str, user_id: int) -> None`
  - **NEW**: Adds messages to conversation context without generating responses
  - Critical for group chat context awareness
  - Allows bot to understand conversation flow without responding

- `add_message_to_context_for_chat(chat_identifier: str, message: str, user_id: int) -> None`
  - **NEW**: Chat-based context addition
  - Dual-mode version of context processing

### 4. session_manager.py - Redis Session Management (Enhanced for Dual-Mode)
**Purpose**: Persistent storage for user conversation threads with dual-mode support and comprehensive file management

#### Legacy Functions (Maintained for Backward Compatibility):
- `get_thread_id(user_id: int) -> str | None`
- `set_thread_id(user_id: int, thread_id: str)`
- `async reset_thread(user_id: int)`

#### New Dual-Mode Functions:
- `get_thread_id_for_chat(chat_identifier: str) -> str | None`
  - **NEW**: Unified thread ID retrieval for any chat type
  - Handles both user-based and chat-based sessions
  - Includes legacy fallback for user sessions

- `set_thread_id_for_chat(chat_identifier: str, thread_id: str)`
  - **NEW**: Unified thread ID storage
  - Supports both user:{user_id} and chat:{chat_id} patterns

- `reset_chat_thread(chat_identifier: str)`
  - **NEW**: Unified reset functionality for dual-mode
  - Cleans up threads, images, and documents for any chat type

#### Dual-Mode File Management:
- `add_chat_image(chat_identifier: str, file_id: str)` - **NEW**: Track images per chat
- `get_chat_images(chat_identifier: str) -> list[str]` - **NEW**: Retrieve chat images
- `clear_chat_images(chat_identifier: str)` - **NEW**: Clear chat image tracking
- `add_chat_document(chat_identifier: str, file_id: str, original_filename: str)` - **NEW**: Track documents per chat
- `get_chat_documents(chat_identifier: str) -> list[dict]` - **NEW**: Retrieve chat documents
- `clear_chat_documents(chat_identifier: str)` - **NEW**: Clear chat document tracking
- `async delete_chat_images_from_openai(chat_identifier: str)` - **NEW**: OpenAI cleanup for chat images
- `async delete_chat_documents_from_openai(chat_identifier: str)` - **NEW**: OpenAI cleanup for chat documents

#### Redis Schema (Enhanced):
- **Thread Storage**
  - **Key Patterns**: 
    - `thread:user:{user_id}` (private chats + legacy)
    - `thread:chat:{chat_id}` (group/supergroup/channel chats)
  - **Value**: OpenAI thread identifier string
  - **TTL**: Persistent (no expiration)

- **File Tracking (Dual-Mode)**
  - **Key Patterns**:
    - `chat_images:{chat_identifier}` (replaces user_images for unified approach)
    - `chat_documents:{chat_identifier}` (replaces user_documents for unified approach)
  - **Values**: Redis sets/hashes of OpenAI file_id strings with metadata
  - **TTL**: Persistent (cleaned on reset)

### 5. subscription_checker.py - Authorization System
**Purpose**: Telegram channel subscription verification with caching

#### Key Functions:
- `check_channel_subscription(bot_token: str, channel_id: str, user_id: int) -> bool`
  - Primary authorization function
  - Checks Redis cache first
  - Makes Telegram API request if cache miss
  - Handles all subscription statuses

- `clear_subscription_cache(user_id: int) -> bool`
  - Manual cache invalidation
  - Useful for testing or admin operations

- `get_subscription_cache_info(user_id: int) -> Optional[dict]`
  - Cache inspection utility
  - Returns subscription status and TTL

#### Authorization Logic:
- **Allowed Statuses**: `creator`, `administrator`, `member`
- **Denied Statuses**: `left`, `kicked`, `restricted`
- **Cache TTL**: 600 seconds (10 minutes)
- **API Endpoint**: `https://api.telegram.org/bot{token}/getChatMember`

#### Redis Caching Schema:
- **Key Pattern**: `subscription:{user_id}`
- **Value**: `"true"` or `"false"`
- **TTL**: 600 seconds

### 6. config.py - Configuration Management
**Purpose**: Environment variable loading and application configuration

#### Configuration Variables:
```python
TELEGRAM_BOT_TOKEN    # Telegram bot API token
OPENAI_API_KEY        # OpenAI API key
ASSISTANT_ID          # Pre-configured OpenAI Assistant ID
CHANNEL_ID            # Target channel for subscription (@logloss_notes)
REDIS_HOST            # Redis server hostname
REDIS_PORT            # Redis server port
REDIS_DB              # Redis database number
ANALYTICS_DB_PATH     # SQLite analytics database path
```

### 7. logger.py - Logging Infrastructure
**Purpose**: Centralized logging configuration

#### Configuration:
- **Log Level**: INFO
- **Format**: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- **Outputs**: File (`bot.log`) + Console (stdout)
- **Encoding**: UTF-8

### 8. user_analytics.py - User Analytics System
**Purpose**: Comprehensive user analytics and token usage tracking for text and image generation

#### DALL-E Pricing Constants:
```python
DALLE_PRICING = {
    "1024x1024": 0.040,      # Standard DALL-E 3
    "1792x1024": 0.080,      # HD landscape
    "1024x1792": 0.080,      # HD portrait
}

DALLE_TOKEN_EQUIVALENT = {
    "1024x1024": 400,        # $0.04 = 400 "tokens"
    "1792x1024": 800,        # $0.08 = 800 "tokens"  
    "1024x1792": 800,        # $0.08 = 800 "tokens"
}
```

#### Key Functions:
- `UserAnalytics.__init__(db_path: str = None)`
  - Initialize analytics with SQLite database path
  - Auto-creates database directory if needed

- `async init_database() -> None`
  - Creates analytics table and performance indexes
  - Called automatically during bot startup

- `async record_usage(user_id: int, username: str, tokens_used: int) -> None`
  - Records token consumption for user and date
  - Validates input data and handles errors gracefully
  - Called automatically after each OpenAI API request

- `async record_image_generation(user_id: int, username: str, size: str = "1024x1024", model: str = "dall-e-3") -> None`
  - Records image generation usage in analytics
  - Converts DALL-E pricing to token equivalents
  - Integrates with existing analytics infrastructure
  - Provides detailed logging for cost tracking

- `async get_user_daily_usage(user_id: int, date: str) -> int`
  - Returns total tokens used by user on specific date

- `async get_user_total_usage(user_id: int) -> int`
  - Returns total tokens used by user across all time

- `async get_all_users_usage_by_date(date: str) -> List[Dict]`
  - Returns usage statistics for all users on specific date

- `async get_user_usage_stats(user_id: int, days: int = 7) -> Dict`
  - Returns detailed usage statistics for user over specified period

#### Database Schema:
```sql
CREATE TABLE user_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    request_date DATE NOT NULL,
    tokens_used INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Cost Control Features:
- **Unified Token System**: Text and images tracked in consistent token equivalents
- **Real-time Cost Calculation**: Immediate cost feedback to users
- **Foundation for Limits**: Infrastructure ready for usage restrictions
- **Transparent Pricing**: Clear cost display in all operations

### 9. view_analytics.py - Analytics Viewing Tool
**Purpose**: Command-line tool for viewing and analyzing user data

#### Usage Modes:
- `python view_analytics.py` - Show all analytics data
- `python view_analytics.py users` - User statistics only
- `python view_analytics.py daily` - Daily statistics only
- `python view_analytics.py info` - Database information only
- `python view_analytics.py help` - Command help

#### Features:
- **Formatted Output**: Clean table layouts with proper alignment
- **Multiple Views**: Raw data, user summaries, daily aggregations
- **Database Info**: File size, record counts, date ranges
- **Error Handling**: Graceful handling of database issues
- **Direct SQL Access**: Alternative to Python interface

---

## Dependencies & External Services

### Python Dependencies
```
python-telegram-bot==21.11.1    # Telegram Bot API wrapper
openai==1.64.0                  # OpenAI API client (async)
redis==5.2.1                    # Redis client
python-dotenv==1.0.1            # Environment variable loader
aiohttp==3.10.11                # Async HTTP client
aiosqlite==0.20.0               # Async SQLite driver for analytics
```

### External Services
1. **Telegram Bot API**
   - Bot messaging and command handling
   - Channel membership verification
   - File upload/download capabilities
   - Image file processing and temporary storage

2. **OpenAI Assistants API**
   - AI conversation management
   - Thread-based conversation persistence
   - Message history and retrieval
   - Token usage reporting
   - Vision API integration for image analysis
   - File storage and management with automatic cleanup

3. **Redis Database**
   - Session storage (thread_id mapping)
   - Subscription status caching
   - Performance optimization

4. **SQLite Database**
   - User analytics and token usage tracking
   - Daily usage aggregation
   - Historical data storage

---

## Database Schemas

### Redis Data Structure

#### Session Storage
```
Key: thread_id:{user_id}
Value: {openai_thread_id}
TTL: Persistent
Example: thread_id:123456789 → "thread_abc123"
```

#### Subscription Cache
```
Key: subscription:{user_id}
Value: "true" | "false"
TTL: 600 seconds
Example: subscription:123456789 → "true"
```

#### Image File Tracking
```
Key: user_images:{user_id}
Value: Redis Set of OpenAI file_id strings
TTL: Persistent (cleaned on reset)
Example: user_images:123456789 → {"file-abc123", "file-xyz789"}
```

#### Document File Tracking
```
Key: user_documents:{user_id}
Value: Redis Hash {file_id: original_filename}
TTL: Persistent (cleaned on reset)
Example: user_documents:123456789 → {"file-doc123": "report.pdf", "file-doc456": "notes.docx"}
```

### SQLite Analytics Database

#### User Analytics Table
```sql
CREATE TABLE user_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    request_date DATE NOT NULL,
    tokens_used INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_user_analytics_user_id ON user_analytics(user_id);
CREATE INDEX idx_user_analytics_date ON user_analytics(request_date);
CREATE INDEX idx_user_analytics_user_date ON user_analytics(user_id, request_date);
```

#### Data Examples
```
id | user_id   | username  | request_date | tokens_used | created_at
1  | 123456789 | john_doe  | 2025-06-22  | 150         | 2025-06-22 16:03:27
2  | 987654321 | jane_doe  | 2025-06-22  | 89          | 2025-06-22 16:05:12
3  | 123456789 | john_doe  | 2025-06-22  | 203         | 2025-06-22 16:12:45
```

---

## API Integrations

### Telegram Bot API Endpoints Used
- `POST /bot{token}/sendMessage` - Send messages with document processing results
- `POST /bot{token}/sendDocument` - Send exported files
- `POST /bot{token}/sendChatAction` - Typing indicators during processing
- `GET /bot{token}/getChatMember` - Check channel membership
- `GET /bot{token}/getFile` - Get file info for downloads (images and documents)
- File download via HTTPS - Download user-uploaded images and documents

### OpenAI Assistants API Endpoints Used
- `POST /v1/threads` - Create conversation threads
- `POST /v1/threads/{thread_id}/messages` - Add messages (text, images, and documents)
- `POST /v1/threads/{thread_id}/runs` - Execute assistant runs with file_search tool
- `GET /v1/threads/{thread_id}/runs/{run_id}` - Check run status
- `GET /v1/threads/{thread_id}/messages` - Retrieve messages
- `POST /v1/files` - Upload files with `purpose="vision"` (images) or `purpose="assistants"` (documents)
- `DELETE /v1/files/{file_id}` - Clean up uploaded files during reset operations

---

## Error Handling & Resilience

### Error Handling Strategies
1. **Network Timeouts**: 10-second HTTP timeouts with aiohttp
2. **API Rate Limits**: Graceful degradation and retry logic
3. **Redis Failures**: Fallback to uncached operations
4. **OpenAI API Errors**: User-friendly error messages
5. **Telegram API Errors**: Comprehensive status code handling

### Logging Strategy
- **Info Level**: User actions, API responses, cache hits/misses
- **Warning Level**: Recoverable errors, cache failures
- **Error Level**: Critical failures, API errors, exceptions

---

## Security Considerations

### Access Control
- Channel-based authorization prevents unauthorized access
- No hardcoded user IDs in production code
- Bot token and API keys stored in environment variables

### Data Privacy
- No permanent storage of user messages
- Temporary files deleted after export
- Redis data can be configured with TTL for compliance

### API Security
- Timeout protection against hanging requests
- Input validation for user messages
- Secure environment variable handling

---

## Performance Optimization

### Caching Strategy
- **Subscription Status**: 10-minute Redis cache reduces API calls
- **Session Persistence**: Thread IDs cached indefinitely
- **Cache Hit Optimization**: Prefer cached data over API calls

### Async Architecture
- **Non-blocking Operations**: All I/O operations are async
- **Concurrent Processing**: Multiple users can interact simultaneously
- **Resource Efficiency**: Event loop manages connection pooling

---

## Deployment Configuration

### Environment Variables Required
```bash
TELEGRAM_BOT_TOKEN=bot123456789:ABC...
OPENAI_API_KEY=sk-...
OPENAI_ASSISTANT_ID=asst_...
CHANNEL_ID=@logloss_notes
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
ANALYTICS_DB_PATH=./data/user_analytics.db
```

### System Requirements
- **Python**: 3.8+
- **Redis**: 5.0+
- **Memory**: 256MB minimum
- **Storage**: 100MB for logs and cache
- **Network**: Outbound HTTPS (443) for APIs

### Systemd Service Configuration
```ini
[Unit]
Description=Telegram GPT Bot using OpenAI Assistants API
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/path/to/telegram-gpt-bot
ExecStart=/path/to/venv/bin/python main.py
EnvironmentFile=/path/to/.env
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## Testing & Monitoring

### Key Metrics to Monitor
- **Bot Response Time**: Average message processing duration
- **Cache Hit Ratio**: Redis cache effectiveness
- **API Error Rates**: OpenAI and Telegram API failures
- **User Activity**: Command usage and conversation volume
- **Authorization Success**: Channel subscription verification rates
- **Token Usage**: Daily and total OpenAI API token consumption
- **Image Generation**: DALL-E usage, success rates, and cost tracking
- **Analytics Database**: Record counts, growth rate, storage size
- **User Engagement**: Active users per day, usage patterns
- **Image Processing**: Upload success rates, file sizes, format distribution
- **File Storage**: OpenAI storage usage, cleanup success rates
- **Cost Control**: Daily/monthly spending trends, user cost distribution
- **Dual-Mode Performance**: Response filtering accuracy, context processing efficiency
- **Chat Detection**: Mention detection accuracy, response appropriateness
- **Session Management**: Thread creation success across chat types

### Log Analysis
- Monitor `bot.log` for error patterns
- Track subscription verification failures
- Monitor Redis connection health
- Watch for OpenAI API rate limiting
- Track DALL-E generation success rates
- Monitor cost trends and usage spikes
- **NEW**: Monitor dual-mode operation patterns
- **NEW**: Track chat detection accuracy and response filtering
- **NEW**: Watch for context processing performance in groups

---

## Development Guidelines

### Code Style
- **Async/Await**: All I/O operations must be async
- **Type Hints**: Function signatures include type annotations
- **Error Handling**: Comprehensive try/catch blocks
- **Logging**: Structured logging with context
- **Dual-Mode Considerations**: All new features must support both private and group contexts

### Testing Scenarios
1. **Subscribed Users**: All functions should work normally
2. **Non-subscribed Users**: Should receive subscription prompts
3. **Network Failures**: Graceful degradation and error messages
4. **Redis Downtime**: Bot continues with reduced functionality
5. **OpenAI API Issues**: User-friendly error responses
6. **Image Processing**: Various formats, sizes, upload failures
7. **Document Processing**: PDF, TXT, DOCX files, size limits, format validation, analysis accuracy
8. **Image Generation**: DALL-E requests, content policy violations, cost tracking
9. **File Storage**: OpenAI storage limits, cleanup verification, lifecycle management
10. **Cost Tracking**: Analytics accuracy, usage limit scenarios
11. **File Management**: Separate tracking of images vs documents, reset functionality
12. **Multilingual Support**: Russian and English generation requests
13. **NEW - Private Chat Mode**: All existing functionality works unchanged
14. **NEW - Group Chat Mode**: Responds only to mentions, replies, and commands
15. **NEW - Chat Detection**: Accurate identification of chat types and response triggers
16. **NEW - Session Isolation**: Private and group conversations remain separate
17. **NEW - Context Processing**: Bot understands group conversations without inappropriate responses

### Extension Points
- **Multiple Channels**: Extend subscription_checker for multi-channel support
- **Role-based Access**: Different permissions based on channel role
- **Custom Commands**: Add new command handlers in main.py
- **Advanced Analytics**: Enhanced logging and metrics collection
- **Cost Limits**: Daily/monthly usage restrictions per user
- **Image Variations**: Multiple image sizes and quality options
- **Advanced Generation**: Style presets, image editing, variations
- **Document Types**: Support for additional formats (PPTX, XLSX, etc.)
- **Document Features**: OCR for scanned documents, table extraction, chart analysis
- **Batch Processing**: Multiple document uploads and analysis
- **Document Storage**: Vector store integration for document search and retrieval
- **NEW - Advanced Chat Modes**: Support for different response behaviors per group
- **NEW - Group-Specific Features**: Per-group settings, custom commands, role management
- **NEW - Enhanced Context**: Conversation summarization, topic tracking, user mention history

---

**Last Updated**: June 29, 2025, 19:50 MSK  
**Document Version**: 1.5  
**Project Version**: 1.8.0 