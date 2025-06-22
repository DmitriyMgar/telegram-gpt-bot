#!/bin/bash

# Telegram GPT Bot - Update Script
# Обновление кода из git и зависимостей с перезапуском

set -e  # Остановка при ошибке

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$SCRIPT_DIR"
VENV_DIR="$BOT_DIR/venv"

echo "🔄 Обновление Telegram GPT Bot..."

# Проверка git репозитория
if [ ! -d "$BOT_DIR/.git" ]; then
    echo "❌ Директория не является git репозиторием"
    echo "💡 Инициализируйте git или клонируйте проект заново"
    exit 1
fi

# Проверка подключения к интернету
if ! ping -c 1 google.com &> /dev/null; then
    echo "❌ Нет подключения к интернету"
    exit 1
fi

# Сохранение текущего статуса бота
BOT_WAS_RUNNING=false
if [ -f "$BOT_DIR/bot.pid" ]; then
    PID=$(cat "$BOT_DIR/bot.pid")
    if ps -p $PID > /dev/null 2>&1; then
        BOT_WAS_RUNNING=true
        echo "🔍 Бот запущен, будет перезапущен после обновления"
    fi
fi

# Остановка бота если он запущен
if [ "$BOT_WAS_RUNNING" = true ]; then
    echo "🛑 Остановка бота для обновления..."
    if [ -f "$SCRIPT_DIR/stop.sh" ]; then
        bash "$SCRIPT_DIR/stop.sh"
    else
        echo "⚠️  stop.sh не найден, пропускаем остановку"
    fi
fi

# Проверка наличия изменений
echo "🔍 Проверка обновлений..."
git fetch origin

LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null)

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "✅ Код уже актуален (commit: ${LOCAL_COMMIT:0:8})"
    UPDATE_CODE=false
else
    echo "📥 Найдены новые изменения"
    echo "   Локальный:  ${LOCAL_COMMIT:0:8}"
    echo "   Удаленный:  ${REMOTE_COMMIT:0:8}"
    UPDATE_CODE=true
fi

# Создание бэкапа важных файлов
BACKUP_DIR="$BOT_DIR/backup_$(date +%Y%m%d_%H%M%S)"
echo "💾 Создание бэкапа конфигурации в $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Бэкап конфигурационных файлов
[ -f "$BOT_DIR/.env" ] && cp "$BOT_DIR/.env" "$BACKUP_DIR/"
[ -f "$BOT_DIR/bot.log" ] && cp "$BOT_DIR/bot.log" "$BACKUP_DIR/"

# Обновление кода
if [ "$UPDATE_CODE" = true ]; then
    echo "📥 Обновление кода..."
    
    # Сохранение локальных изменений
    if ! git diff --quiet; then
        echo "💾 Сохранение локальных изменений..."
        git stash push -m "Auto-stash before update $(date)"
    fi
    
    # Получение обновлений
    BRANCH=$(git branch --show-current)
    git pull origin "$BRANCH"
    
    echo "✅ Код обновлен до commit: $(git rev-parse --short HEAD)"
else
    echo "⏭️  Пропускаем обновление кода"
fi

# Активация виртуального окружения
if [ -d "$VENV_DIR" ]; then
    echo "🔧 Активация виртуального окружения..."
    source "$VENV_DIR/bin/activate"
else
    echo "❌ Виртуальное окружение не найдено"
    echo "💡 Запустите ./start.sh для создания окружения"
    exit 1
fi

# Обновление зависимостей
if [ -f "$BOT_DIR/requirements.txt" ]; then
    echo "📦 Обновление зависимостей..."
    
    # Сравнение requirements.txt с установленными пакетами
    pip list --format=freeze > "$BACKUP_DIR/pip_freeze_before.txt"
    
    pip install -r "$BOT_DIR/requirements.txt" --upgrade
    
    pip list --format=freeze > "$BACKUP_DIR/pip_freeze_after.txt"
    echo "✅ Зависимости обновлены"
else
    echo "⚠️  requirements.txt не найден, пропускаем обновление зависимостей"
fi

# Запуск бота если он был запущен
if [ "$BOT_WAS_RUNNING" = true ]; then
    echo "🚀 Запуск бота..."
    if [ -f "$SCRIPT_DIR/start.sh" ]; then
        bash "$SCRIPT_DIR/start.sh"
    else
        echo "❌ start.sh не найден"
        exit 1
    fi
elif [ "$UPDATE_CODE" = true ]; then
    echo "💡 Бот не был запущен. Для запуска используйте: ./start.sh"
fi

# Очистка старых бэкапов (оставляем только последние 5)
echo "🧹 Очистка старых бэкапов..."
ls -dt "$BOT_DIR"/backup_* 2>/dev/null | tail -n +6 | xargs rm -rf 2>/dev/null || true

echo ""
echo "✅ Обновление завершено!"
echo "📁 Бэкап сохранен в: $BACKUP_DIR"
echo "📝 Логи: tail -f $BOT_DIR/bot.log"
echo "🔍 Статус: ./status.sh" 