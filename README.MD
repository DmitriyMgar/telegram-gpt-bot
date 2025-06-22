# 🤖 Telegram GPT Bot using OpenAI Assistants API

This is an asynchronous, modular, production-ready Telegram bot that connects authorized users to an OpenAI Assistant via the Assistants API.  
It uses Redis for persistent thread management, supports async processing, centralized logging, and access control.

---

## 📦 Features

- ✅ Chat with OpenAI Assistant (Assistants API)
- ✅ Fully asynchronous processing (`asyncio`)
- ✅ Redis-based conversation history per user (`thread_id`)
- ✅ Channel subscription-based access control
- ✅ **User Analytics System** - Token usage tracking and reporting
- ✅ `/reset` command to start a new thread
- ✅ `/history` and `/export` commands for conversation management
- ✅ Centralized logging to `bot.log`
- ✅ Runs as a `systemd` service on Linux
- ✅ Modular project structure for easy extension

---

## 🧱 Project Structure

```
telegram-gpt-bot/
├── main.py                  # Bot entry point (Telegram handlers)
├── config.py                # Tokens, Redis, channel config, .env loader
├── logger.py                # Logging setup
├── openai_handler.py        # Assistants API logic (async)
├── session_manager.py       # Redis session management (user <-> thread_id)
├── subscription_checker.py  # Channel subscription verification (async)
├── user_analytics.py        # User analytics and token usage tracking
├── view_analytics.py        # Analytics viewing tool
├── data/
│   └── user_analytics.db    # SQLite database for analytics
├── .env                     # Secret tokens and config
├── bot.log                  # Log file
```

---

## 🔐 Environment Variables

Create a `.env` file in the project root:

```
TELEGRAM_BOT_TOKEN=your_telegram_token
OPENAI_API_KEY=your_openai_api_key
OPENAI_ASSISTANT_ID=asst_abc123456789

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Channel for subscription verification (required)
CHANNEL_ID=@logloss_notes

# Analytics database path (optional)
ANALYTICS_DB_PATH=./data/user_analytics.db
```

These are automatically loaded via `config.py`.

---

## 🔒 Access Control

The bot now uses **channel subscription verification** instead of a static user list.

### Channel Setup:
1. The bot must be an **administrator** of the `@logloss_notes` channel
2. Set the `CHANNEL_ID` variable in your `.env` file
3. Only channel subscribers can use the bot

### Access Statuses:
- ✅ `creator` - channel creator
- ✅ `administrator` - channel administrator  
- ✅ `member` - channel member
- ❌ `left` - left the channel
- ❌ `kicked` - banned from channel

### Caching:
Subscription check results are cached in Redis for 10 minutes to optimize performance.

---

## 💬 Available Commands

| Command      | Description                          |
|--------------|--------------------------------------|
| `/start`     | Welcome message                      |
| `/reset`     | Clears your conversation thread      |
| `/history`   | Shows recent conversation history    |
| `/export`    | Exports conversation as text file    |
| `/subscribe` | Check subscription status and help   |

---

## 🧠 How It Works

- Each user is assigned a persistent `thread_id` via OpenAI's `beta.threads` API.
- Messages are added to the thread and executed via `runs`.
- Replies are filtered by `created_at` to avoid duplicates.
- Redis stores `thread_id` per user for persistence across restarts.
- The entire flow is asynchronous using `openai.AsyncOpenAI` and `asyncio`.

---

## 📊 User Analytics System

The bot includes a comprehensive analytics system that tracks OpenAI API token usage per user and date, helping you monitor costs and usage patterns.

### 🎯 What's Tracked

- **User ID**: Telegram user identifier
- **Username**: User's display name or handle
- **Request Date**: Daily aggregation of usage
- **Tokens Used**: OpenAI API token consumption per request
- **No Message Content**: Only metadata is stored for privacy

### 📈 Analytics Features

- **Daily Usage Tracking**: Monitor token consumption by date
- **User Statistics**: Track individual user usage patterns
- **Automatic Collection**: Seamless integration with bot operations
- **SQLite Database**: Lightweight, file-based storage
- **Performance Optimized**: Indexed queries for fast reporting

### 🔍 Viewing Analytics

#### Using the Analytics Tool:
```bash
# Activate virtual environment
source venv/bin/activate

# View all analytics data
python view_analytics.py

# View user statistics only
python view_analytics.py users

# View daily statistics
python view_analytics.py daily

# View database info
python view_analytics.py info

# Show help
python view_analytics.py help
```

#### Direct SQL Access:
```bash
# Access database directly
sqlite3 data/user_analytics.db

# Example queries:
SELECT * FROM user_analytics ORDER BY created_at DESC LIMIT 10;
SELECT user_id, username, SUM(tokens_used) FROM user_analytics GROUP BY user_id;
```

### 🗃️ Database Schema

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

---

## 🪵 Logging

Logs are written to:

```
mygpt_bot/bot.log
```

Configured in `logger.py` with timestamps, log levels, and module names. Also logs to stdout.

---

## 🖥️ Running as a Systemd Service (Linux)

### 1. Create service file

```bash
sudo nano /etc/systemd/system/mygpt_bot.service
```

Paste the following:

```ini
[Unit]
Description=Telegram GPT Bot using OpenAI Assistants API
After=network.target

[Service]
Type=simple
User=botfather
WorkingDirectory=/home/botfather/mygpt_bot
ExecStart=/home/botfather/mygpt_bot/mygptvenv/bin/python main.py
EnvironmentFile=/home/botfather/mygpt_bot/.env
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 2. Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable mygpt_bot
sudo systemctl start mygpt_bot
```

### 3. View logs

```bash
journalctl -u mygpt_bot -f
```

---

## 🚀 Management Scripts

The project includes a comprehensive set of bash scripts for easy bot management and deployment automation.

### 📋 Available Scripts

#### 🚀 start.sh - Bot Startup
```bash
./start.sh
```
**Functions:**
- Creates virtual environment if it doesn't exist
- Checks for all required files
- Installs/updates dependencies
- Starts bot in background mode
- Saves process PID for management

#### ⏹️ stop.sh - Bot Shutdown
```bash
./stop.sh
```
**Functions:**
- Gracefully terminates bot process
- Uses soft shutdown (SIGTERM)
- Forces termination if needed (SIGKILL)
- Cleans up PID file
- Can find manually started processes

#### 🔄 restart.sh - Bot Restart
```bash
./restart.sh
```
**Functions:**
- Stops bot via stop.sh
- Adds pause interval
- Starts bot via start.sh

#### 📥 update.sh - Bot Update
```bash
./update.sh
```
**Functions:**
- Checks git repository for updates
- Creates configuration backup
- Stops bot (if running)
- Updates code from git
- Updates Python dependencies
- Starts bot (if it was running)
- Cleans up old backups

#### 📊 status.sh - Status Check
```bash
./status.sh
```
**Shows:**
- Bot process status
- Log file information
- Virtual environment state
- Configuration (.env file)
- Network connections (internet, APIs)
- System resources (CPU, memory, disk)
- Git status

#### 📝 logs.sh - Log Management
```bash
./logs.sh [options]
```
**Options:**
- `./logs.sh` - follow logs in real-time
- `./logs.sh -t 100` - show last 100 lines
- `./logs.sh -e` - show errors only
- `./logs.sh -w` - show warnings and errors
- `./logs.sh -s "text"` - search in logs
- `./logs.sh -c` - clear logs (with backup)
- `./logs.sh -h` - help

### 🔧 Quick Start

#### First Run
```bash
# Set permissions (if needed)
chmod +x *.sh

# Start bot
./start.sh

# Check status
./status.sh

# View logs
./logs.sh
```

#### Daily Usage
```bash
# Check status
./status.sh

# View logs
./logs.sh -t 50

# Restart if needed
./restart.sh

# Update to new version
./update.sh
```

### 📁 Created Files

- `bot.pid` - PID of running process
- `bot.log` - bot log file
- `backup_YYYYMMDD_HHMMSS/` - backups during updates
- `bot.log.backup.YYYYMMDD_HHMMSS` - log backups

### ⚠️ Important Notes

1. **Virtual Environment**: Created automatically in `venv/` folder
2. **File Permissions**: All scripts must be executable (`chmod +x`)
3. **Configuration**: Ensure `.env` file is properly configured
4. **Git Repository**: update.sh requires initialized git repository
5. **Internet Connection**: Required for updates and bot operation
6. **🔒 Process Safety**: Scripts work only with processes in current directory and do NOT affect other bots on the server

### 🚨 Troubleshooting

#### Bot Won't Start
```bash
# Check status
./status.sh

# View errors in logs
./logs.sh -e

# Check configuration
cat .env
```

#### Process Stuck
```bash
# Try to stop
./stop.sh

# If that doesn't work, find and kill process
ps aux | grep python
kill -9 <PID>
```

#### Update Issues
```bash
# Check git status
git status

# Restore from backup
ls -la backup_*/
cp backup_XXXXXX/.env .
```

### 💡 Tips

- Use `./status.sh` for quick diagnostics
- Regularly check logs with `./logs.sh -e`
- Run `./update.sh` to get updates
- If problems occur, first check `.env` file
- For debugging use `./logs.sh -s "error"`
- **🔒 Multi-Bot Environment**: Scripts safely work on servers with multiple bots, identifying processes by full file path

---

## 🔧 TODO / Ideas for Extension

- 🔄 Log rotation support
- 📎 File/document upload (via OpenAI tool use)
- 📊 Database integration for business intelligence
- 💡 Function calling support
- 🔐 Auth flow with password or OTP

---

## 📄 License

MIT

---

> Created with ❤️ by dimamgar
