#!/bin/bash

# Telegram GPT Bot - Logs Script
# Просмотр логов с различными опциями

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$SCRIPT_DIR"
LOG_FILE="$BOT_DIR/bot.log"

# Функция помощи
show_help() {
    echo "📝 Просмотр логов Telegram GPT Bot"
    echo ""
    echo "Использование:"
    echo "  ./logs.sh [опция]"
    echo ""
    echo "Опции:"
    echo "  -f, --follow     Следить за логами в реальном времени (по умолчанию)"
    echo "  -t, --tail N     Показать последние N строк (по умолчанию 50)"
    echo "  -e, --errors     Показать только ошибки"
    echo "  -w, --warnings   Показать предупреждения и ошибки"
    echo "  -s, --search     Поиск по логам"
    echo "  -c, --clear      Очистить логи"
    echo "  -h, --help       Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  ./logs.sh                # Следить за логами"
    echo "  ./logs.sh -t 100         # Последние 100 строк"
    echo "  ./logs.sh -e             # Только ошибки"
    echo "  ./logs.sh -s \"user_id\"   # Поиск по тексту"
}

# Проверка наличия лог файла
check_log_file() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "❌ Лог файл не найден: $LOG_FILE"
        echo "💡 Возможно, бот еще не запускался или лог файл был удален"
        exit 1
    fi
}

# Функция очистки логов
clear_logs() {
    echo "🗑️  Очистка логов..."
    read -p "❓ Вы уверены, что хотите очистить лог файл? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Создаем бэкап перед очисткой
        BACKUP_FILE="$BOT_DIR/bot.log.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$LOG_FILE" "$BACKUP_FILE"
        echo "💾 Создан бэкап: $BACKUP_FILE"
        
        # Очистка файла
        > "$LOG_FILE"
        echo "✅ Логи очищены"
    else
        echo "❌ Отменено"
    fi
}

# Основная логика
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -c|--clear)
        check_log_file
        clear_logs
        exit 0
        ;;
    -e|--errors)
        check_log_file
        echo "❌ Показ только ошибок из $LOG_FILE"
        echo "=================================="
        grep -i "ERROR\|CRITICAL" "$LOG_FILE" || echo "✅ Ошибок не найдено"
        ;;
    -w|--warnings)
        check_log_file
        echo "⚠️  Показ предупреждений и ошибок из $LOG_FILE"
        echo "=================================="
        grep -i "WARNING\|ERROR\|CRITICAL" "$LOG_FILE" || echo "✅ Предупреждений и ошибок не найдено"
        ;;
    -s|--search)
        check_log_file
        if [ -z "$2" ]; then
            read -p "🔍 Введите текст для поиска: " SEARCH_TEXT
        else
            SEARCH_TEXT="$2"
        fi
        echo "🔍 Поиск '$SEARCH_TEXT' в $LOG_FILE"
        echo "=================================="
        grep -i --color=always "$SEARCH_TEXT" "$LOG_FILE" || echo "❌ Ничего не найдено"
        ;;
    -t|--tail)
        check_log_file
        LINES="${2:-50}"
        echo "📄 Последние $LINES строк из $LOG_FILE"
        echo "=================================="
        tail -n "$LINES" "$LOG_FILE"
        ;;
    -f|--follow|"")
        check_log_file
        echo "📝 Просмотр логов в реальном времени"
        echo "💡 Нажмите Ctrl+C для выхода"
        echo "=================================="
        tail -f "$LOG_FILE"
        ;;
    *)
        echo "❌ Неизвестная опция: $1"
        echo "💡 Используйте ./logs.sh --help для справки"
        exit 1
        ;;
esac 