#!/bin/bash

# Telegram GPT Bot - Stop Script
# Остановка бота через systemd сервис

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="telegram-gpt-bot.service"

echo "⏹️  Остановка Telegram GPT Bot..."

# Проверяем, запущен ли systemd сервис
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "🔍 Найден активный systemd сервис: $SERVICE_NAME"
    
    # Останавливаем сервис
    echo "🛑 Остановка сервиса..."
    if sudo systemctl stop "$SERVICE_NAME"; then
        echo "✅ Сервис успешно остановлен"
        
        # Проверяем статус
        sleep 2
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            echo "⚠️  Сервис все еще активен, ожидание..."
            sleep 3
            if systemctl is-active --quiet "$SERVICE_NAME"; then
                echo "❌ Не удалось остановить сервис"
                exit 1
            fi
        fi
        
        echo "🔍 Статус сервиса: $(systemctl is-active $SERVICE_NAME)"
        echo "✅ Бот успешно остановлен"
    else
        echo "❌ Ошибка при остановке сервиса"
        exit 1
    fi
    
elif systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "ℹ️  Сервис существует, но не запущен"
    echo "🔍 Статус: $(systemctl is-active $SERVICE_NAME)"
    echo "✅ Бот уже остановлен"
    
else
    echo "⚠️  Systemd сервис не найден. Проверяем процессы..."
    
    # Fallback: ищем процессы нашего бота напрямую
    BOT_PIDS=$(pgrep -f "python.*main.py" | while read pid; do
        if pwdx "$pid" 2>/dev/null | grep -q "$SCRIPT_DIR"; then
            echo "$pid"
        fi
    done)
    
    if [ -n "$BOT_PIDS" ]; then
        echo "🔍 Найдены процессы бота:"
        for pid in $BOT_PIDS; do
            ps -p "$pid" -o pid,cmd --no-headers
        done
        
        echo "🛑 Остановка процессов..."
        for pid in $BOT_PIDS; do
            kill -TERM "$pid" 2>/dev/null
        done
        
        sleep 3
        
        # Проверяем, что процессы остановились
        REMAINING_PIDS=$(pgrep -f "python.*main.py" | while read pid; do
            if pwdx "$pid" 2>/dev/null | grep -q "$SCRIPT_DIR"; then
                echo "$pid"
            fi
        done)
        
        if [ -n "$REMAINING_PIDS" ]; then
            echo "⚠️  Принудительная остановка..."
            for pid in $REMAINING_PIDS; do
                kill -KILL "$pid" 2>/dev/null
            done
        fi
        
        echo "✅ Процессы остановлены"
    else
        echo "ℹ️  Процессы бота не найдены"
        echo "✅ Бот уже остановлен"
    fi
fi

echo ""
echo "📊 Для проверки статуса: ./status.sh"
echo "🚀 Для запуска: ./start.sh" 