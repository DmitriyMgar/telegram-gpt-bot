# Telegram GPT Bot - Project Technical Documentation

## Project Overview

**Project Name:** Telegram GPT Bot  
**Version:** 1.7.0  
**Language:** Python 3.8+  
**Architecture:** Asynchronous, microservice-style modular design  
**Primary Purpose:** Channel-subscription-gated Telegram bot with OpenAI Assistant integration, DALL-E image generation, document processing, user analytics, and comprehensive file handling

### Core Functionality
- **AI Chat Interface**: Users interact with OpenAI Assistant via Telegram
- **Document Processing**: Support for PDF, TXT, and DOCX files with AI analysis using OpenAI file_search
- **DALL-E Image Generation**: Text-to-image generation with natural language detection and explicit commands
- **Image Processing**: Support for image uploads with OpenAI Vision API integration
- **Channel-Based Authorization**: Access control through Telegram channel subscription verification
- **Persistent Conversations**: Redis-backed thread management for conversation continuity
- **Export/History Features**: Chat history retrieval and export capabilities
- **User Analytics System**: Comprehensive token usage tracking and reporting for text, image generation, and document processing
- **Cost Control**: Real-time cost tracking and transparent pricing for all AI operations
- **File Management**: Comprehensive lifecycle management for images and documents with automatic cleanup
- **Caching System**: Intelligent Redis caching for subscription status optimization

---

## System Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram      │◄──►│   Bot Core       │◄──►│   OpenAI        │
│   Users         │    │   (main.py)      │    │   Assistant     │
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
                       └──────────────────┘    └─────────────────┘
                                │
                        ┌───────▼───────┐    ┌─────────────────┐
                        │     Redis     │    │   Analytics     │
                        │   (Cache &    │    │   Database      │
                        │   Sessions)   │    │   (SQLite)      │
                        └───────────────┘    └─────────────────┘
```

### Component Architecture
1. **Presentation Layer**: Telegram Bot API handlers (`main.py`)
2. **Business Logic Layer**: Authorization, session management, message processing, document processing, image processing, image generation, analytics
3. **Data Access Layer**: Redis for caching and sessions, SQLite for analytics, temporary file storage
4. **External API Layer**: OpenAI Assistant API (text, vision, file_search), OpenAI Images API (DALL-E 3), Telegram Bot API, OpenAI File API
5. **Infrastructure Layer**: Logging, configuration, error handling, comprehensive file lifecycle management, cost tracking

---

## File Structure & Modules

```
telegram-gpt-bot/
├── main.py                    # Entry point & Telegram handlers
├── config.py                  # Configuration & environment variables
├── logger.py                  # Centralized logging setup
├── openai_handler.py          # OpenAI Assistant API integration
├── session_manager.py         # Redis session management
├── subscription_checker.py    # Channel subscription verification
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

### 1. main.py - Bot Entry Point
**Purpose**: Telegram bot handlers and application lifecycle management

#### Key Functions:
- `is_authorized_async(user_id: int) -> bool`
  - Async authorization check via channel subscription
  - Integrates with subscription_checker module
  - Returns True if user has access

- `start(update, context)` - Welcome handler with authorization
- `reset(update, context)` - Clear conversation thread and cleanup files
- `handle_message(update, context)` - Process user text messages
- `handle_photo(update, context)` - Process user image uploads
- `handle_document(update, context)` - Process user document uploads (PDF, TXT, DOCX)
- `history(update, context)` - Retrieve conversation history
- `export(update, context)` - Export chat history as file
- `subscribe(update, context)` - Check subscription status

#### Bot Commands:
| Command      | Description                              | Authorization Required |
|--------------|------------------------------------------|------------------------|
| `/start`     | Welcome message & instructions           | Yes                    |
| `/reset`     | Clear conversation thread                | Yes                    |
| `/generate`  | Generate image with DALL-E 3            | Yes                    |
| `/history`   | Show recent conversation history         | Yes                    |
| `/export`    | Export conversation as text file         | Yes                    |
| `/subscribe` | Check subscription status & instructions | No                     |

#### Message Handling:
| Input Type   | Description                              | Supported Formats      |
|--------------|------------------------------------------|------------------------|
| Text         | Regular chat messages + image generation | All text formats       |
| Images       | Image analysis with optional captions    | JPEG, PNG, WebP (≤20MB)|
| Documents    | Document analysis with optional questions| PDF, TXT, DOCX (≤15MB) |
| Generation   | Natural language image generation        | "нарисуй", "draw", etc.|

### 2. openai_handler.py - OpenAI Integration
**Purpose**: Manages OpenAI Assistant API interactions and DALL-E image generation

#### Key Functions:
- `create_thread() -> str`
  - Creates new OpenAI conversation thread
  - Returns thread_id for session tracking

- `send_message_and_get_response(user_id: int, message: str, username: str = None) -> str`
  - Core message processing function
  - Manages thread creation/retrieval
  - Handles assistant run execution
  - Tracks token usage for analytics
  - Returns AI response

- `detect_image_generation_request(message: str) -> bool`
  - Detects image generation requests using multilingual regex patterns
  - Supports Russian ("нарисуй", "создай картинку") and English ("draw", "generate image")
  - Returns True if message is requesting image generation

- `generate_image_dalle(prompt: str, user_id: int, username: str = None, size: str = "1024x1024") -> tuple[str, int]`
  - Core DALL-E 3 image generation function
  - Integrates with OpenAI Images API
  - Returns image URL and equivalent token cost
  - Records usage in analytics system
  - Handles all API errors with user-friendly messages

- `get_message_history(user_id: int, limit: int = 10) -> str`
  - Retrieves formatted conversation history
  - Returns emoji-formatted message list

- `export_message_history(user_id: int, limit: int = 50) -> str | None`
  - Creates temporary file with conversation export
  - Returns file path for download

- `send_image_and_get_response(user_id: int, image_path: str, caption: str = "", username: str = None) -> str`
  - Process images with OpenAI Vision API through Assistants
  - Uploads image to OpenAI storage with `purpose="vision"`
  - Uses proper `image_file` content type with `file_id` reference
  - Includes automatic file cleanup to prevent quota issues
  - Supports optional text captions alongside images
  - Integrates with token usage analytics

- `send_document_and_get_response(user_id: int, local_file_path: str, original_filename: str, user_question: str = "", username: str = None) -> str`
  - Process documents with OpenAI Assistants API using file_search tool
  - Uploads document to OpenAI storage with `purpose="assistants"`
  - Supports PDF, TXT, and DOCX file formats with comprehensive analysis
  - Handles specific user questions or provides default comprehensive analysis
  - Integrates with session management and analytics tracking
  - Returns detailed AI analysis of document content and structure

#### OpenAI API Flow:
1. Get/Create thread for user
2. Add user message to thread (text, image+text, document+question, or generation request)
3. For images: Upload to OpenAI storage with `purpose="vision"` and reference by file_id
4. For documents: Upload to OpenAI storage with `purpose="assistants"` and attach with file_search tool
5. For generation: Call DALL-E 3 Images API
6. Create and execute run (for text/image/document analysis)
7. Poll for completion
8. Retrieve and filter responses
9. Clean up uploaded files (images only - documents managed by session lifecycle)
10. Record usage in analytics
11. Return formatted response or generated image

#### DALL-E 3 Integration:
- **Model**: dall-e-3
- **Standard Size**: 1024x1024 ($0.04)
- **Quality**: Standard
- **Style**: Vivid
- **Error Handling**: Comprehensive API error mapping
- **Cost Tracking**: Automatic analytics recording

### 3. session_manager.py - Redis Session Management & File Lifecycle
**Purpose**: Persistent storage for user conversation threads and comprehensive file management

#### Key Functions:
- `get_thread_id(user_id: int) -> str | None`
  - Retrieves stored thread_id for user
  - Returns None if no thread exists

- `set_thread_id(user_id: int, thread_id: str)`
  - Stores thread_id for user persistence
  - Enables conversation continuity across restarts

- `async reset_thread(user_id: int)`
  - Deletes stored thread_id and cleans up all associated files
  - Forces new conversation thread creation
  - Removes images and documents from OpenAI storage

#### Image Management Functions:
- `add_user_image(user_id: int, file_id: str)` - Track uploaded images in Redis
- `get_user_images(user_id: int) -> list[str]` - Retrieve user's image file IDs
- `clear_user_images(user_id: int)` - Clear image tracking data
- `async delete_user_images_from_openai(user_id: int)` - Delete images from OpenAI storage

#### Document Management Functions:
- `add_user_document(user_id: int, file_id: str, original_filename: str)` - Track uploaded documents
- `get_user_documents(user_id: int) -> list[dict]` - Retrieve document metadata
- `clear_user_documents(user_id: int)` - Clear document tracking data
- `async delete_user_documents_from_openai(user_id: int)` - Delete documents from OpenAI storage

#### Redis Schema:
- **Thread Storage**
  - **Key Pattern**: `thread_id:{user_id}`
  - **Value**: OpenAI thread identifier string
  - **TTL**: Persistent (no expiration)

- **Image File Tracking**
  - **Key Pattern**: `user_images:{user_id}`
  - **Value**: Redis set of OpenAI file_id strings
  - **TTL**: Persistent (cleaned on reset)

- **Document File Tracking**
  - **Key Pattern**: `user_documents:{user_id}`
  - **Value**: Redis hash with file_id → original_filename mapping
  - **TTL**: Persistent (cleaned on reset)

### 4. subscription_checker.py - Authorization System
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

### 5. config.py - Configuration Management
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

### 6. logger.py - Logging Infrastructure
**Purpose**: Centralized logging configuration

#### Configuration:
- **Log Level**: INFO
- **Format**: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- **Outputs**: File (`bot.log`) + Console (stdout)
- **Encoding**: UTF-8

### 7. user_analytics.py - User Analytics System
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

### 8. view_analytics.py - Analytics Viewing Tool
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
TTL: 600 seconds (10 minutes)
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

### Log Analysis
- Monitor `bot.log` for error patterns
- Track subscription verification failures
- Monitor Redis connection health
- Watch for OpenAI API rate limiting
- Track DALL-E generation success rates
- Monitor cost trends and usage spikes

---

## Development Guidelines

### Code Style
- **Async/Await**: All I/O operations must be async
- **Type Hints**: Function signatures include type annotations
- **Error Handling**: Comprehensive try/catch blocks
- **Logging**: Structured logging with context

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

---

**Last Updated**: June 29, 2025, 17:50 MSK  
**Document Version**: 1.4  
**Project Version**: 1.7.0 