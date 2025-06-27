#!/bin/bash

# Telegram GPT Bot - Start Script
# Запуск бота через systemd сервис

set -e  # Остановка при ошибке

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="telegram-gpt-bot.service"
BOT_DIR="$SCRIPT_DIR"
VENV_DIR="$BOT_DIR/venv"
MAIN_FILE="$BOT_DIR/main.py"

echo "🚀 Запуск Telegram GPT Bot..."

# Основные проверки
echo "🔧 Проверка конфигурации..."

# Проверка наличия main.py
if [ ! -f "$MAIN_FILE" ]; then
    echo "❌ Файл main.py не найден в $BOT_DIR"
    exit 1
fi

# Проверка .env файла
if [ ! -f "$BOT_DIR/.env" ]; then
    echo "⚠️  Файл .env не найден. Убедитесь, что все переменные окружения настроены."
fi

# Проверка виртуального окружения
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Виртуальное окружение не найдено в $VENV_DIR"
    echo "📦 Создание виртуального окружения..."
    python3 -m venv "$VENV_DIR"
    echo "✅ Виртуальное окружение создано"
fi

# Проверяем, запущен ли systemd сервис
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "⚠️  Сервис уже запущен!"
    echo "🔍 Статус: $(systemctl is-active $SERVICE_NAME)"
    echo "📊 Для проверки деталей: ./status.sh"
    echo "🔄 Для перезапуска: ./restart.sh"
    exit 1
    
elif systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "🔍 Найден systemd сервис: $SERVICE_NAME"
    
    # Установка/обновление зависимостей
    if [ -f "$BOT_DIR/requirements.txt" ]; then
        echo "📦 Обновление зависимостей..."
        source "$VENV_DIR/bin/activate"
        pip install -r "$BOT_DIR/requirements.txt" --quiet
        deactivate
    fi
    
    # Запуск через systemd
    echo "▶️  Запуск сервиса..."
    if sudo systemctl start "$SERVICE_NAME"; then
        echo "✅ Сервис запускается..."
        
        # Ждем запуска
        sleep 3
        
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            echo "✅ Бот успешно запущен!"
            echo "🆔 Сервис: $SERVICE_NAME"
            echo "🔍 Статус: $(systemctl is-active $SERVICE_NAME)"
            echo "📊 Подробности: ./status.sh"
            echo "📝 Логи: sudo journalctl -u $SERVICE_NAME -f"
            echo "⏹️  Остановить: ./stop.sh"
        else
            echo "❌ Ошибка запуска сервиса"
            echo "📝 Проверьте логи: sudo journalctl -u $SERVICE_NAME -n 20"
            exit 1
        fi
    else
        echo "❌ Не удалось запустить сервис"
        exit 1
    fi
    
else
    echo "⚠️  Systemd сервис не найден. Запуск напрямую..."
    
    # Fallback: проверяем наличие процессов
    BOT_PIDS=$(pgrep -f "python.*main.py" | while read pid; do
        if pwdx "$pid" 2>/dev/null | grep -q "$SCRIPT_DIR"; then
            echo "$pid"
        fi
    done)
    
    if [ -n "$BOT_PIDS" ]; then
        echo "⚠️  Найдены запущенные процессы бота:"
        for pid in $BOT_PIDS; do
            ps -p "$pid" -o pid,cmd --no-headers
        done
        echo "🛑 Используйте ./stop.sh для остановки"
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
    nohup python "$MAIN_FILE" >> "$BOT_DIR/bot.log" 2>&1 &
    BOT_PID=$!
    
    # Сохранение PID
    echo $BOT_PID > "$BOT_DIR/bot.pid"
    
    # Небольшая пауза для проверки запуска
    sleep 2
    
    # Проверка, что процесс запустился
    if ps -p $BOT_PID > /dev/null 2>&1; then
        echo "✅ Бот успешно запущен!"
        echo "🆔 PID: $BOT_PID"
        echo "📝 Логи: $BOT_DIR/bot.log"
        echo "🔍 Проверить статус: ./status.sh"
        echo "⏹️  Остановить: ./stop.sh"
    else
        echo "❌ Ошибка запуска бота"
        echo "📝 Проверьте логи: tail -f $BOT_DIR/bot.log"
        rm -f "$BOT_DIR/bot.pid"
        exit 1
    fi
fi 