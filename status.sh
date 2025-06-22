#!/bin/bash

# Telegram GPT Bot - Status Script
# Проверка статуса бота, процессов и системных ресурсов

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$SCRIPT_DIR"
PID_FILE="$BOT_DIR/bot.pid"
LOG_FILE="$BOT_DIR/bot.log"
VENV_DIR="$BOT_DIR/venv"

echo "📊 Статус Telegram GPT Bot"
echo "=================================="

# Информация о времени
echo "⏰ Время: $(date)"
echo ""

# Проверка PID файла и процесса
echo "🔍 Статус процесса:"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "   📄 PID файл: $PID_FILE (PID: $PID)"
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "   ✅ Процесс запущен и работает"
        
        # Подробная информация о процессе
        echo "   📋 Детали процесса:"
        ps -p $PID -o pid,ppid,user,%cpu,%mem,etime,cmd --no-headers | while read line; do
            echo "      $line"
        done
        
        # Время запуска процесса
        START_TIME=$(ps -p $PID -o lstart --no-headers 2>/dev/null)
        [ -n "$START_TIME" ] && echo "   🕐 Запущен: $START_TIME"
        
    else
        echo "   ❌ Процесс не найден (PID устарел)"
        echo "   🧹 Требуется очистка PID файла"
    fi
else
    echo "   ⚠️  PID файл не найден"
    
    # Поиск процессов нашего бота (ищем по main.py в нашей директории)
    ALL_MAIN_PIDS=$(pgrep -f "main.py" 2>/dev/null || true)
    OUR_BOT_PIDS=""
    if [ -n "$ALL_MAIN_PIDS" ]; then
        for pid in $ALL_MAIN_PIDS; do
            if ps -p $pid > /dev/null 2>&1; then
                PWD_DIR=$(pwdx $pid 2>/dev/null | cut -d: -f2 | xargs 2>/dev/null || echo "unknown")
                # Проверяем, что процесс работает в нашей директории
                if [[ "$PWD_DIR" == "$BOT_DIR" ]]; then
                    OUR_BOT_PIDS="$OUR_BOT_PIDS $pid"
                fi
            fi
        done
    fi
    
    if [ -n "$OUR_BOT_PIDS" ]; then
        echo "   🔍 Найдены процессы нашего бота:"
        for pid in $OUR_BOT_PIDS; do
            if ps -p $pid > /dev/null 2>&1; then
                CMD=$(ps -p $pid -o cmd --no-headers 2>/dev/null)
                PWD_DIR=$(pwdx $pid 2>/dev/null | cut -d: -f2 | xargs 2>/dev/null || echo "unknown")
                echo "      PID $pid: $CMD"
                echo "      Директория: $PWD_DIR"
            fi
        done
    else
        echo "   ❌ Процессы нашего бота не найдены"
    fi
    
    # Показать все процессы с main.py для информации (без возможности воздействия)
    OTHER_PIDS=""
    if [ -n "$ALL_MAIN_PIDS" ]; then
        for pid in $ALL_MAIN_PIDS; do
            if ps -p $pid > /dev/null 2>&1; then
                PWD_DIR=$(pwdx $pid 2>/dev/null | cut -d: -f2 | xargs 2>/dev/null || echo "unknown")
                # Показываем только если это НЕ наш бот (не в нашей директории)
                if [[ "$PWD_DIR" != "$BOT_DIR" ]]; then
                    OTHER_PIDS="$OTHER_PIDS $pid"
                fi
            fi
        done
    fi
    
    if [ -n "$OTHER_PIDS" ]; then
        echo "   ℹ️  Другие Python процессы с main.py на сервере:"
        for pid in $OTHER_PIDS; do
            if ps -p $pid > /dev/null 2>&1; then
                CMD=$(ps -p $pid -o cmd --no-headers 2>/dev/null)
                PWD_DIR=$(pwdx $pid 2>/dev/null | cut -d: -f2 | xargs 2>/dev/null || echo "unknown")
                echo "      PID $pid: $CMD"
                echo "      Директория: $PWD_DIR"
            fi
        done
    fi
fi

echo ""

# Проверка логов
echo "📝 Статус логов:"
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
    LOG_LINES=$(wc -l < "$LOG_FILE")
    LOG_MODIFIED=$(stat -c %y "$LOG_FILE" 2>/dev/null || date -r "$LOG_FILE" 2>/dev/null)
    
    echo "   📁 Файл: $LOG_FILE"
    echo "   📏 Размер: $LOG_SIZE ($LOG_LINES строк)"
    echo "   🕐 Изменен: $LOG_MODIFIED"
    
    # Последние записи в логе
    echo "   📄 Последние 3 записи:"
    tail -n 3 "$LOG_FILE" 2>/dev/null | sed 's/^/      /'
    
else
    echo "   ❌ Лог файл не найден: $LOG_FILE"
fi

echo ""

# Проверка виртуального окружения
echo "🐍 Виртуальное окружение:"
if [ -d "$VENV_DIR" ]; then
    echo "   ✅ Найдено: $VENV_DIR"
    
    if [ -f "$VENV_DIR/bin/python" ]; then
        PYTHON_VERSION=$("$VENV_DIR/bin/python" --version 2>&1)
        echo "   🐍 Версия Python: $PYTHON_VERSION"
        
        # Проверка ключевых пакетов
        if [ -f "$VENV_DIR/bin/pip" ]; then
            echo "   📦 Ключевые пакеты:"
            "$VENV_DIR/bin/pip" list 2>/dev/null | grep -E "(telegram|openai|redis)" | sed 's/^/      /' || echo "      ⚠️  Не удалось получить список пакетов"
        fi
    fi
else
    echo "   ❌ Виртуальное окружение не найдено"
fi

echo ""

# Проверка конфигурации
echo "⚙️  Конфигурация:"
if [ -f "$BOT_DIR/.env" ]; then
    echo "   ✅ .env файл найден"
    
    # Проверка ключевых переменных (без вывода значений)
    echo "   🔑 Переменные окружения:"
    for var in TELEGRAM_BOT_TOKEN OPENAI_API_KEY ASSISTANT_ID CHANNEL_ID REDIS_HOST; do
        if grep -q "^$var=" "$BOT_DIR/.env" 2>/dev/null; then
            echo "      ✅ $var"
        else
            echo "      ❌ $var (не найдена)"
        fi
    done
else
    echo "   ❌ .env файл не найден"
fi

echo ""

# Проверка подключения к внешним сервисам
echo "🌐 Сетевые подключения:"
echo "   🔗 Интернет:"
if ping -c 1 google.com &> /dev/null; then
    echo "      ✅ Подключение к интернету работает"
else
    echo "      ❌ Нет подключения к интернету"
fi

echo "   🔗 Telegram API:"
if curl -s --connect-timeout 5 https://api.telegram.org > /dev/null; then
    echo "      ✅ Telegram API доступен"
else
    echo "      ❌ Telegram API недоступен"
fi

echo "   🔗 OpenAI API:"
if curl -s --connect-timeout 5 https://api.openai.com > /dev/null; then
    echo "      ✅ OpenAI API доступен"
else
    echo "      ❌ OpenAI API недоступен"
fi

echo ""

# Системные ресурсы
echo "💻 Системные ресурсы:"
echo "   🧠 Использование CPU:"
top -bn1 | grep "Cpu(s)" | sed 's/^/      /'

echo "   💾 Использование памяти:"
free -h | head -2 | sed 's/^/      /'

echo "   💿 Использование диска:"
df -h "$BOT_DIR" | tail -1 | sed 's/^/      /'

echo ""

# Git статус
echo "📋 Git статус:"
if [ -d "$BOT_DIR/.git" ]; then
    BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    
    echo "   🌿 Ветка: $BRANCH"
    echo "   📝 Commit: $COMMIT"
    
    # Проверка изменений
    if git diff --quiet 2>/dev/null; then
        echo "   ✅ Нет локальных изменений"
    else
        echo "   ⚠️  Есть локальные изменения"
    fi
    
    # Проверка удаленных изменений
    git fetch origin &>/dev/null
    LOCAL_COMMIT=$(git rev-parse HEAD 2>/dev/null)
    REMOTE_COMMIT=$(git rev-parse origin/$BRANCH 2>/dev/null || echo "")
    
    if [ -n "$REMOTE_COMMIT" ] && [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
        echo "   📥 Доступны обновления"
    else
        echo "   ✅ Код актуален"
    fi
else
    echo "   ❌ Не git репозиторий"
fi

echo ""
echo "=================================="

# Рекомендации
echo "💡 Управление:"
echo "   ▶️  Запуск:      ./start.sh"
echo "   ⏹️  Остановка:   ./stop.sh"
echo "   🔄 Перезапуск:  ./restart.sh"
echo "   🔄 Обновление:  ./update.sh"
echo "   📝 Логи:        tail -f $LOG_FILE" 