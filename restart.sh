#!/bin/bash

# Telegram GPT Bot - Restart Script
# Перезапуск бота (остановка + запуск)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔄 Перезапуск Telegram GPT Bot..."

# Проверка наличия скриптов
if [ ! -f "$SCRIPT_DIR/stop.sh" ]; then
    echo "❌ Скрипт stop.sh не найден"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/start.sh" ]; then
    echo "❌ Скрипт start.sh не найден"
    exit 1
fi

# Остановка бота
echo "🛑 Остановка бота..."
if ! bash "$SCRIPT_DIR/stop.sh"; then
    echo "❌ Ошибка при остановке бота"
    exit 1
fi

echo ""
echo "⏳ Пауза перед запуском..."
sleep 2

# Запуск бота
echo "🚀 Запуск бота..."
if ! bash "$SCRIPT_DIR/start.sh"; then
    echo "❌ Ошибка при запуске бота"
    exit 1
fi

echo ""
echo "✅ Бот успешно перезапущен!" 