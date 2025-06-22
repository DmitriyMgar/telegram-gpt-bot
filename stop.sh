#!/bin/bash

# Telegram GPT Bot - Stop Script
# Остановка бота с корректным завершением процесса

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$SCRIPT_DIR"
PID_FILE="$BOT_DIR/bot.pid"

echo "⏹️  Остановка Telegram GPT Bot..."

# Проверка наличия PID файла
if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  PID файл не найден. Бот не запущен или запущен вручную."
    
    # Попытка найти процесс нашего бота по рабочей директории
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
        echo "🔍 Найдены процессы нашего бота:"
        for pid in $OUR_BOT_PIDS; do
            if ps -p $pid > /dev/null 2>&1; then
                CMD=$(ps -p $pid -o cmd --no-headers 2>/dev/null)
                PWD_DIR=$(pwdx $pid 2>/dev/null | cut -d: -f2 | xargs 2>/dev/null || echo "unknown")
                echo "   PID $pid: $CMD"
                echo "   Директория: $PWD_DIR"
            fi
        done
        echo ""
        read -p "❓ Остановить эти процессы нашего бота? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            for pid in $OUR_BOT_PIDS; do
                kill -TERM $pid 2>/dev/null || true
            done
            echo "✅ Процессы нашего бота остановлены"
        else
            echo "❌ Отменено пользователем"
        fi
    else
        echo "✅ Процессы нашего бота не найдены"
    fi
    exit 0
fi

# Чтение PID из файла
PID=$(cat "$PID_FILE")

# Проверка, что процесс существует
if ! ps -p $PID > /dev/null 2>&1; then
    echo "⚠️  Процесс с PID $PID не найден"
    echo "🧹 Удаление устаревшего PID файла..."
    rm -f "$PID_FILE"
    echo "✅ Бот уже остановлен"
    exit 0
fi

echo "🔍 Найден процесс бота (PID: $PID)"

# Мягкая остановка (SIGTERM)
echo "📤 Отправка сигнала SIGTERM..."
kill -TERM $PID

# Ожидание завершения процесса
TIMEOUT=10
COUNT=0
while ps -p $PID > /dev/null 2>&1 && [ $COUNT -lt $TIMEOUT ]; do
    echo "⏳ Ожидание завершения процесса... ($((COUNT+1))/$TIMEOUT)"
    sleep 1
    COUNT=$((COUNT+1))
done

# Проверка, завершился ли процесс
if ps -p $PID > /dev/null 2>&1; then
    echo "⚠️  Процесс не завершился за $TIMEOUT секунд"
    echo "💥 Принудительная остановка (SIGKILL)..."
    kill -KILL $PID
    sleep 1
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "❌ Не удалось остановить процесс"
        exit 1
    else
        echo "✅ Процесс принудительно остановлен"
    fi
else
    echo "✅ Процесс корректно завершен"
fi

# Удаление PID файла
rm -f "$PID_FILE"
echo "🧹 PID файл удален"
echo "✅ Бот успешно остановлен" 