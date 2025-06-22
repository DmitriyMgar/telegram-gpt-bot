# Working Cache - Implementation Plans

## User Analytics System Implementation Plan

### Цель
Реализовать систему сбора и хранения данных о пользователях бота для аналитики потребления токенов OpenAI API.

### Требования
- Хранить: user_id, username, дату запроса, количество токенов
- Не хранить сами запросы
- Возможность подсчета токенов по дням и общего потребления по пользователям
- Только сбор данных, без визуализации

---

## Архитектурное решение

### 1. Выбор базы данных
**Решение**: SQLite для простоты развертывания и обслуживания

**Обоснование**:
- Не требует отдельного сервера БД
- Встроенная поддержка в Python
- Достаточно для объемов данных бота
- Простое резервное копирование
- При необходимости легко мигрировать на PostgreSQL

### 2. Структура базы данных

```sql
CREATE TABLE user_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    request_date DATE NOT NULL,
    tokens_used INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_analytics_user_id ON user_analytics(user_id);
CREATE INDEX idx_user_analytics_date ON user_analytics(request_date);
CREATE INDEX idx_user_analytics_user_date ON user_analytics(user_id, request_date);
```

---

## Компоненты для реализации

### 1. user_analytics.py - новый модуль

#### Основные функции:
```python
class UserAnalytics:
    def __init__(self, db_path: str = "user_analytics.db")
    async def init_database(self) -> None
    async def record_usage(self, user_id: int, username: str, tokens_used: int) -> None
    async def get_user_daily_usage(self, user_id: int, date: str) -> int
    async def get_user_total_usage(self, user_id: int) -> int
    async def get_all_users_usage_by_date(self, date: str) -> List[dict]
    async def close(self) -> None
```

#### Детали реализации:
- Использовать `aiosqlite` для асинхронной работы с SQLite
- Автоматическое создание БД при первом запуске
- Обработка ошибок БД с логированием
- Группировка записей по дням для оптимизации

### 2. Интеграция с OpenAI API

#### Модификация openai_handler.py:
- Добавить подсчет токенов из ответа OpenAI API
- Токены доступны в объекте `run` после выполнения
- Поля: `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`

#### Точки интеграции:
```python
# В функции send_message_and_get_response()
response = await openai_client.beta.threads.runs.retrieve(
    thread_id=thread_id,
    run_id=run.id
)
tokens_used = response.usage.total_tokens if response.usage else 0

# Записать в аналитику
await analytics.record_usage(user_id, username, tokens_used)
```

### 3. Модификация существующих модулей

#### main.py изменения:
- Импортировать `UserAnalytics`
- Создать глобальный экземпляр аналитики
- Передавать `username` в функции обработки сообщений
- Инициализировать БД при запуске бота

#### Получение username:
```python
def get_username(update) -> str:
    user = update.effective_user
    return user.username or user.first_name or f"user_{user.id}"
```

---

## План поэтапной реализации

### Этап 1: Создание модуля user_analytics.py
1. Создать класс `UserAnalytics`
2. Реализовать подключение к SQLite с aiosqlite
3. Создать методы для инициализации БД
4. Реализовать метод `record_usage()`
5. Добавить базовые методы для чтения данных
6. Покрыть основные исключения

### Этап 2: Интеграция с OpenAI API
1. Модифицировать `send_message_and_get_response()` в openai_handler.py
2. Добавить извлечение данных о токенах из ответа OpenAI
3. Обработать случаи, когда данные о токенах недоступны
4. Добавить логирование использования токенов

### Этап 3: Интеграция с основным ботом
1. Модифицировать `main.py` для инициализации аналитики
2. Добавить передачу username в обработчики
3. Интегрировать запись данных в `handle_message()`
4. Добавить graceful shutdown для корректного закрытия БД

### Этап 4: Обновление конфигурации
1. Добавить настройки БД в `config.py`
2. Обновить `requirements.txt` с новой зависимостью
3. Добавить переменные окружения для пути к БД

---

## Технические детали

### Зависимости
Добавить в requirements.txt:
```
aiosqlite==0.20.0  # Async SQLite driver
```

### Переменные окружения
```bash
# В .env файл
ANALYTICS_DB_PATH=./data/user_analytics.db
```

### Структура данных для записи
```python
{
    "user_id": 123456789,
    "username": "john_doe",
    "request_date": "2025-01-15",
    "tokens_used": 150,
    "created_at": "2025-01-15 14:30:25"
}
```

### Обработка ошибок
- Логировать все ошибки БД в bot.log
- При недоступности БД продолжать работу бота
- Retry логика для временных сбоев БД
- Валидация входных данных

---

## Рекомендации по реализации

### Производительность
- Использовать batch insert для множественных записей
- Индексы по user_id и date для быстрых запросов
- Периодическая очистка старых данных (опционально)

### Безопасность
- Параметризованные запросы для защиты от SQL инъекций
- Валидация user_id и tokens_used
- Ограничение размера username

### Мониторинг
- Логировать успешные записи на уровне DEBUG
- Метрики: количество записей в день, размер БД
- Алерты при ошибках записи аналитики

---

## Будущие расширения (не в текущем scope)

### Возможные доработки:
- Миграция на PostgreSQL для масштабирования
- API для экспорта аналитики
- Дашборд для визуализации данных
- Агрегированные таблицы для ускорения отчетов
- Retention анализ пользователей

---

**Дата создания плана**: 2025-01-15  
**Дата завершения**: 2025-01-15  
**Приоритет**: Средний  
**Время реализации**: Выполнено за 1 день ✅  
**Ответственный**: Backend разработчик  
**Статус**: ЗАВЕРШЕНО - готово к продакшену
