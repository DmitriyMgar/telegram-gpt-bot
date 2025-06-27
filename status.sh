#!/bin/bash

# Telegram GPT Bot - Status Script
# Проверка статуса бота

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="telegram-gpt-bot.service"

echo "📊 Статус Telegram GPT Bot"
echo "=========================="

# Проверка systemd сервиса
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "🔍 Systemd сервис: НАЙДЕН"
    echo "📋 Название сервиса: $SERVICE_NAME"
    
    # Статус сервиса
    STATUS=$(systemctl is-active "$SERVICE_NAME")
    case "$STATUS" in
        "active")
            echo "✅ Статус: ЗАПУЩЕН (active)"
            ;;
        "inactive")
            echo "⏹️  Статус: ОСТАНОВЛЕН (inactive)"
            ;;
        "failed")
            echo "❌ Статус: ОШИБКА (failed)"
            ;;
        *)
            echo "⚠️  Статус: $STATUS"
            ;;
    esac
    
    # Дополнительная информация
    if [ "$STATUS" = "active" ]; then
        echo ""
        echo "📋 Подробная информация:"
        systemctl status "$SERVICE_NAME" --no-pager -l
        
        echo ""
        echo "📊 Использование ресурсов:"
        systemctl show "$SERVICE_NAME" --property=MainPID,CPUAccounting,MemoryAccounting 2>/dev/null
        
        # Находим PID процесса
        MAIN_PID=$(systemctl show "$SERVICE_NAME" --property=MainPID --value 2>/dev/null)
        if [ -n "$MAIN_PID" ] && [ "$MAIN_PID" != "0" ]; then
            echo "🆔 Основной PID: $MAIN_PID"
            echo "💾 Память: $(ps -p $MAIN_PID -o rss= 2>/dev/null | awk '{print int($1/1024)" MB"}' || echo "неизвестно")"
            echo "⏱️  CPU: $(ps -p $MAIN_PID -o %cpu= 2>/dev/null | awk '{print $1"%"}' || echo "неизвестно")"
        fi
    fi
    
    echo ""
    echo "🔧 Управление сервисом:"
    echo "   Запуск:      sudo systemctl start $SERVICE_NAME"
    echo "   Остановка:   sudo systemctl stop $SERVICE_NAME"
    echo "   Перезапуск:  sudo systemctl restart $SERVICE_NAME"
    echo "   Логи:        sudo journalctl -u $SERVICE_NAME -f"
    
else
    echo "⚠️  Systemd сервис: НЕ НАЙДЕН"
    echo ""
    echo "🔍 Поиск процессов вручную..."
    
    # Поиск процессов нашего бота
    BOT_PIDS=$(pgrep -f "python.*main.py" | while read pid; do
        if pwdx "$pid" 2>/dev/null | grep -q "$SCRIPT_DIR"; then
            echo "$pid"
        fi
    done)
    
    if [ -n "$BOT_PIDS" ]; then
        echo "✅ Найдены процессы бота:"
        for pid in $BOT_PIDS; do
            echo "   🆔 PID: $pid"
            echo "   📂 Команда: $(ps -p $pid -o cmd --no-headers 2>/dev/null)"
            echo "   📍 Директория: $(pwdx $pid 2>/dev/null | cut -d: -f2 | xargs)"
            echo "   💾 Память: $(ps -p $pid -o rss= 2>/dev/null | awk '{print int($1/1024)" MB"}' || echo "неизвестно")"
            echo "   ⏱️  CPU: $(ps -p $pid -o %cpu= 2>/dev/null | awk '{print $1"%"}' || echo "неизвестно")"
            echo "   ⏰ Время запуска: $(ps -p $pid -o lstart= 2>/dev/null || echo "неизвестно")"
            echo "   ---"
        done
        
        # Проверяем PID файл
        if [ -f "$SCRIPT_DIR/bot.pid" ]; then
            PID_FROM_FILE=$(cat "$SCRIPT_DIR/bot.pid")
            echo "📄 PID из файла: $PID_FROM_FILE"
            if echo "$BOT_PIDS" | grep -q "$PID_FROM_FILE"; then
                echo "✅ PID файл соответствует запущенному процессу"
            else
                echo "⚠️  PID файл не соответствует процессам (устарел?)"
            fi
        else
            echo "📄 PID файл: НЕ НАЙДЕН"
        fi
        
    else
        echo "❌ Процессы бота НЕ НАЙДЕНЫ"
        
        # Проверяем остатки PID файла
        if [ -f "$SCRIPT_DIR/bot.pid" ]; then
            echo "📄 Найден устаревший PID файл"
            echo "🧹 Рекомендуется удалить: rm $SCRIPT_DIR/bot.pid"
        fi
    fi
    
    echo ""
    echo "🔧 Управление без systemd:"
    echo "   Запуск:      ./start.sh"
    echo "   Остановка:   ./stop.sh"
    echo "   Перезапуск:  ./restart.sh"
    echo "   Логи:        tail -f $SCRIPT_DIR/bot.log"
fi

echo ""
echo "📁 Файлы проекта:"
echo "   Главный файл: $([ -f "$SCRIPT_DIR/main.py" ] && echo "✅ НАЙДЕН" || echo "❌ НЕ НАЙДЕН")"
echo "   Конфигурация: $([ -f "$SCRIPT_DIR/.env" ] && echo "✅ НАЙДЕН" || echo "❌ НЕ НАЙДЕН")"
echo "   Виртуальное окружение: $([ -d "$SCRIPT_DIR/venv" ] && echo "✅ НАЙДЕНО" || echo "❌ НЕ НАЙДЕНО")"
echo "   Зависимости: $([ -f "$SCRIPT_DIR/requirements.txt" ] && echo "✅ НАЙДЕНЫ" || echo "❌ НЕ НАЙДЕНЫ")"
echo "   Лог файл: $([ -f "$SCRIPT_DIR/bot.log" ] && echo "✅ НАЙДЕН ($(stat -c%s "$SCRIPT_DIR/bot.log" 2>/dev/null | awk '{print int($1/1024)" KB"}' || echo "неизвестно"))" || echo "❌ НЕ НАЙДЕН")"

echo ""
echo "🔄 Быстрые действия:"
echo "   Проверить этот статус: ./status.sh"
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "   Перезапустить бота:    ./restart.sh (или sudo systemctl restart $SERVICE_NAME)"
    echo "   Просмотр логов:        sudo journalctl -u $SERVICE_NAME -f"
else
    echo "   Перезапустить бота:    ./restart.sh"
    echo "   Просмотр логов:        tail -f $SCRIPT_DIR/bot.log" 