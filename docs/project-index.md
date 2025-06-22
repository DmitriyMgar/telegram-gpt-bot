# Telegram GPT Bot - Project Technical Documentation

## Project Overview

**Project Name:** Telegram GPT Bot  
**Version:** 1.1.0  
**Language:** Python 3.8+  
**Architecture:** Asynchronous, microservice-style modular design  
**Primary Purpose:** Channel-subscription-gated Telegram bot with OpenAI Assistant integration

### Core Functionality
- **AI Chat Interface**: Users interact with OpenAI Assistant via Telegram
- **Channel-Based Authorization**: Access control through Telegram channel subscription verification
- **Persistent Conversations**: Redis-backed thread management for conversation continuity
- **Export/History Features**: Chat history retrieval and export capabilities
- **Caching System**: Intelligent Redis caching for subscription status optimization

---

## System Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram      │◄──►│   Bot Core       │◄──►│   OpenAI        │
│   Users         │    │   (main.py)      │    │   Assistant     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Authorization  │
                       │   System         │
                       │   (subscription) │
                       └──────────────────┘
                                │
                        ┌───────▼───────┐
                        │     Redis     │
                        │   (Cache &    │
                        │   Sessions)   │
                        └───────────────┘
```

### Component Architecture
1. **Presentation Layer**: Telegram Bot API handlers (`main.py`)
2. **Business Logic Layer**: Authorization, session management, message processing
3. **Data Access Layer**: Redis for caching and session storage
4. **External API Layer**: OpenAI Assistant API, Telegram Bot API
5. **Infrastructure Layer**: Logging, configuration, error handling

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
├── requirements.txt           # Python dependencies
├── README.MD                  # Project documentation
├── .env                       # Environment variables (not tracked)
├── bot.log                    # Application logs
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
- `reset(update, context)` - Clear conversation thread
- `handle_message(update, context)` - Process user messages
- `history(update, context)` - Retrieve conversation history
- `export(update, context)` - Export chat history as file
- `subscribe(update, context)` - Check subscription status

#### Bot Commands:
| Command      | Description                              | Authorization Required |
|--------------|------------------------------------------|------------------------|
| `/start`     | Welcome message & instructions           | Yes                    |
| `/reset`     | Clear conversation thread                | Yes                    |
| `/history`   | Show recent conversation history         | Yes                    |
| `/export`    | Export conversation as text file         | Yes                    |
| `/subscribe` | Check subscription status & instructions | No                     |

### 2. openai_handler.py - OpenAI Integration
**Purpose**: Manages OpenAI Assistant API interactions

#### Key Functions:
- `create_thread() -> str`
  - Creates new OpenAI conversation thread
  - Returns thread_id for session tracking

- `send_message_and_get_response(user_id: int, message: str) -> str`
  - Core message processing function
  - Manages thread creation/retrieval
  - Handles assistant run execution
  - Returns AI response

- `get_message_history(user_id: int, limit: int = 10) -> str`
  - Retrieves formatted conversation history
  - Returns emoji-formatted message list

- `export_message_history(user_id: int, limit: int = 50) -> str | None`
  - Creates temporary file with conversation export
  - Returns file path for download

#### OpenAI API Flow:
1. Get/Create thread for user
2. Add user message to thread
3. Create and execute run
4. Poll for completion
5. Retrieve and filter assistant responses
6. Return formatted response

### 3. session_manager.py - Redis Session Management
**Purpose**: Persistent storage for user conversation threads

#### Key Functions:
- `get_thread_id(user_id: int) -> str | None`
  - Retrieves stored thread_id for user
  - Returns None if no thread exists

- `set_thread_id(user_id: int, thread_id: str)`
  - Stores thread_id for user persistence
  - Enables conversation continuity across restarts

- `reset_thread(user_id: int)`
  - Deletes stored thread_id
  - Forces new conversation thread creation

#### Redis Schema:
- **Key Pattern**: `thread_id:{user_id}`
- **Value**: OpenAI thread identifier string
- **TTL**: Persistent (no expiration)

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
```

### 6. logger.py - Logging Infrastructure
**Purpose**: Centralized logging configuration

#### Configuration:
- **Log Level**: INFO
- **Format**: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- **Outputs**: File (`bot.log`) + Console (stdout)
- **Encoding**: UTF-8

---

## Dependencies & External Services

### Python Dependencies
```
python-telegram-bot==21.11.1    # Telegram Bot API wrapper
openai==1.64.0                  # OpenAI API client (async)
redis==5.2.1                    # Redis client
python-dotenv==1.0.1            # Environment variable loader
aiohttp==3.10.11                # Async HTTP client
```

### External Services
1. **Telegram Bot API**
   - Bot messaging and command handling
   - Channel membership verification
   - File upload/download capabilities

2. **OpenAI Assistants API**
   - AI conversation management
   - Thread-based conversation persistence
   - Message history and retrieval

3. **Redis Database**
   - Session storage (thread_id mapping)
   - Subscription status caching
   - Performance optimization

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

---

## API Integrations

### Telegram Bot API Endpoints Used
- `POST /bot{token}/sendMessage` - Send messages
- `POST /bot{token}/sendDocument` - Send files
- `POST /bot{token}/sendChatAction` - Typing indicators
- `GET /bot{token}/getChatMember` - Check channel membership

### OpenAI Assistants API Endpoints Used
- `POST /v1/threads` - Create conversation threads
- `POST /v1/threads/{thread_id}/messages` - Add messages
- `POST /v1/threads/{thread_id}/runs` - Execute assistant runs
- `GET /v1/threads/{thread_id}/runs/{run_id}` - Check run status
- `GET /v1/threads/{thread_id}/messages` - Retrieve messages

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

### Log Analysis
- Monitor `bot.log` for error patterns
- Track subscription verification failures
- Monitor Redis connection health
- Watch for OpenAI API rate limiting

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

### Extension Points
- **Multiple Channels**: Extend subscription_checker for multi-channel support
- **Role-based Access**: Different permissions based on channel role
- **Custom Commands**: Add new command handlers in main.py
- **Advanced Analytics**: Enhanced logging and metrics collection

---

**Last Updated**: June 22, 2025, 11:51 UTC  
**Document Version**: 1.0  
**Project Version**: 1.1.0 