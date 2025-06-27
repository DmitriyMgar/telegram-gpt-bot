#!/bin/bash

# Telegram GPT Bot - Restart Script
# Перезапуск бота через systemd сервис

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="telegram-gpt-bot.service"

echo "🔄 Перезапуск Telegram GPT Bot..."

# Проверяем наличие systemd сервиса
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "🔍 Найден systemd сервис: $SERVICE_NAME"
    
    # Показываем текущий статус
    CURRENT_STATUS=$(systemctl is-active "$SERVICE_NAME")
    echo "🔍 Текущий статус: $CURRENT_STATUS"
    
    # Перезапускаем сервис
    echo "🔄 Перезапуск сервиса..."
    if sudo systemctl restart "$SERVICE_NAME"; then
        echo "✅ Команда перезапуска выполнена"
        
        # Ждем запуска
        echo "⏳ Ожидание запуска сервиса..."
        sleep 5
        
        # Проверяем результат
        NEW_STATUS=$(systemctl is-active "$SERVICE_NAME")
        echo "🔍 Новый статус: $NEW_STATUS"
        
        if [ "$NEW_STATUS" = "active" ]; then
            echo "✅ Бот успешно перезапущен!"
            echo "🆔 Сервис: $SERVICE_NAME"
            echo "📊 Подробности: ./status.sh"
            echo "📝 Логи: sudo journalctl -u $SERVICE_NAME -f"
        else
            echo "❌ Ошибка при перезапуске сервиса"
            echo "🔍 Статус: $NEW_STATUS"
            echo "📝 Проверьте логи: sudo journalctl -u $SERVICE_NAME -n 20"
            exit 1
        fi
    else
        echo "❌ Ошибка выполнения команды перезапуска"
        exit 1
    fi
    
else
    echo "⚠️  Systemd сервис не найден. Используем скрипты..."
    
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
    sleep 3
    
    # Запуск бота
    echo "🚀 Запуск бота..."
    if ! bash "$SCRIPT_DIR/start.sh"; then
        echo "❌ Ошибка при запуске бота"
        exit 1
    fi
    
    echo ""
    echo "✅ Бот успешно перезапущен!" 
fi

echo ""
echo "📊 Для проверки статуса: ./status.sh"
echo "📝 Для просмотра логов: sudo journalctl -u $SERVICE_NAME -f" 