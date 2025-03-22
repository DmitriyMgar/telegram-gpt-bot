Вот обновлённый `README.MD` на английском, в стиле оригинала:

---

# 🤖 Telegram GPT Bot using OpenAI Assistants API

This is an asynchronous, modular, production-ready Telegram bot that connects authorized users to an OpenAI Assistant via the Assistants API.  
It uses Redis for persistent thread management, supports async processing, centralized logging, and access control.

---

## 📦 Features

- ✅ Chat with OpenAI Assistant (Assistants API)
- ✅ Fully asynchronous processing (`asyncio`)
- ✅ Redis-based conversation history per user (`thread_id`)
- ✅ `/reset` command to start a new thread
- ✅ Access whitelist (by Telegram user ID)
- ✅ Centralized logging to `bot.log`
- ✅ Runs as a `systemd` service on Linux
- ✅ Modular project structure for easy extension

---

## 🧱 Project Structure

```
mygpt_bot/
├── main.py                # Bot entry point (Telegram handlers)
├── config.py              # Tokens, Redis, whitelist, .env loader
├── logger.py              # Logging setup
├── openai_handler.py      # Assistants API logic (async)
├── session_manager.py     # Redis session management (user <-> thread_id)
├── .env                   # Secret tokens and config
├── bot.log                # Log file
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
```

These are automatically loaded via `config.py`.

---

## 🔒 Access Control

Define allowed users in `config.py`:

```python
ALLOWED_USERS = [
    123456789,  # your Telegram user ID
    987654321,
]
```

Only users in this list can access the bot.

---

## 💬 Available Commands

| Command    | Description                          |
|------------|--------------------------------------|
| `/start`   | Welcome message                      |
| `/reset`   | Clears your conversation thread      |

---

## 🧠 How It Works

- Each user is assigned a persistent `thread_id` via OpenAI's `beta.threads` API.
- Messages are added to the thread and executed via `runs`.
- Replies are filtered by `created_at` to avoid duplicates.
- Redis stores `thread_id` per user for persistence across restarts.
- The entire flow is asynchronous using `openai.AsyncOpenAI` and `asyncio`.

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
