#!/bin/bash

# Telegram GPT Bot - Start Script
# Запуск бота с проверками и логированием

set -e  # Остановка при ошибке

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$SCRIPT_DIR"
VENV_DIR="$BOT_DIR/venv"
MAIN_FILE="$BOT_DIR/main.py"
PID_FILE="$BOT_DIR/bot.pid"
LOG_FILE="$BOT_DIR/bot.log"

echo "🚀 Запуск Telegram GPT Bot..."

# Проверка наличия виртуального окружения
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Виртуальное окружение не найдено в $VENV_DIR"
    echo "📦 Создание виртуального окружения..."
    python3 -m venv "$VENV_DIR"
    echo "✅ Виртуальное окружение создано"
fi

# Проверка наличия main.py
if [ ! -f "$MAIN_FILE" ]; then
    echo "❌ Файл main.py не найден в $BOT_DIR"
    exit 1
fi

# Проверка .env файла
if [ ! -f "$BOT_DIR/.env" ]; then
    echo "⚠️  Файл .env не найден. Убедитесь, что все переменные окружения настроены."
fi

# Проверка, не запущен ли уже наш бот
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        # Дополнительная проверка, что это действительно наш процесс
        CMD=$(ps -p $PID -o cmd --no-headers 2>/dev/null)
        if [[ "$CMD" == *"$MAIN_FILE"* ]]; then
            echo "⚠️  Наш бот уже запущен (PID: $PID)"
            echo "🔍 Для проверки статуса: ./status.sh"
            echo "🔄 Для перезапуска: ./restart.sh"
            exit 1
        else
            echo "🧹 PID файл указывает на другой процесс, удаляем..."
            rm -f "$PID_FILE"
        fi
    else
        echo "🧹 Удаление устаревшего PID файла..."
        rm -f "$PID_FILE"
    fi
fi

# Дополнительная проверка на процессы нашего бота без PID файла
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
    echo "⚠️  Найдены процессы нашего бота без PID файла:"
    for pid in $OUR_BOT_PIDS; do
        if ps -p $pid > /dev/null 2>&1; then
            CMD=$(ps -p $pid -o cmd --no-headers 2>/dev/null)
            PWD_DIR=$(pwdx $pid 2>/dev/null | cut -d: -f2 | xargs 2>/dev/null || echo "unknown")
            echo "   PID $pid: $CMD"
            echo "   Директория: $PWD_DIR"
        fi
    done
    echo "🛑 Используйте ./stop.sh для корректной остановки"
    exit 1
fi

# Активация виртуального окружения
echo "🔧 Активация виртуального окружения..."
source "$VENV_DIR/bin/activate"

# Установка/обновление зависимостей
if [ -f "$BOT_DIR/requirements.txt" ]; then
    echo "📦 Проверка зависимостей..."
    pip install -r "$BOT_DIR/requirements.txt" --quiet
fi

# Запуск бота в фоновом режиме
echo "▶️  Запуск бота..."
cd "$BOT_DIR"

# Запуск с перенаправлением вывода в лог
nohup python "$MAIN_FILE" >> "$LOG_FILE" 2>&1 &
BOT_PID=$!

# Сохранение PID
echo $BOT_PID > "$PID_FILE"

# Небольшая пауза для проверки запуска
sleep 2

# Проверка, что процесс запустился
if ps -p $BOT_PID > /dev/null 2>&1; then
    echo "✅ Бот успешно запущен!"
    echo "🆔 PID: $BOT_PID"
    echo "📝 Логи: $LOG_FILE"
    echo "🔍 Проверить статус: ./status.sh"
    echo "⏹️  Остановить: ./stop.sh"
else
    echo "❌ Ошибка запуска бота"
    echo "📝 Проверьте логи: tail -f $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi 