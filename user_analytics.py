import aiosqlite
import os
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from logger import logger
from config import ANALYTICS_DB_PATH


class UserAnalytics:
    """
    Класс для сбора и хранения аналитики использования бота пользователями.
    Отслеживает потребление токенов OpenAI API по пользователям и датам.
    """
    
    def __init__(self, db_path: str = None):
        """
        Инициализация с путем к базе данных.
        
        Args:
            db_path: Путь к файлу SQLite базы данных
        """
        self.db_path = db_path or ANALYTICS_DB_PATH or "user_analytics.db"
        # Создаем директорию если она не существует
        db_dir = os.path.dirname(self.db_path)
        if db_dir:  # Проверяем, что директория не пустая
            os.makedirs(db_dir, exist_ok=True)
        
    async def init_database(self) -> None:
        """
        Инициализация базы данных и создание таблиц.
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Создание таблицы для аналитики пользователей
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS user_analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        username TEXT,
                        request_date DATE NOT NULL,
                        tokens_used INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Создание индексов для оптимизации запросов
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_analytics_user_id 
                    ON user_analytics(user_id)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_analytics_date 
                    ON user_analytics(request_date)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_analytics_user_date 
                    ON user_analytics(user_id, request_date)
                """)
                
                await db.commit()
                logger.info(f"User analytics database initialized at {self.db_path}")
                
        except Exception as e:
            logger.error(f"Error initializing user analytics database: {e}")
            raise
    
    async def record_usage(self, user_id: int, username: str, tokens_used: int) -> None:
        """
        Записывает использование токенов пользователем.
        
        Args:
            user_id: Telegram ID пользователя
            username: Имя пользователя или никнейм
            tokens_used: Количество использованных токенов
        """
        if not isinstance(user_id, int) or user_id <= 0:
            logger.warning(f"Invalid user_id: {user_id}")
            return
            
        if not isinstance(tokens_used, int) or tokens_used < 0:
            logger.warning(f"Invalid tokens_used: {tokens_used}")
            return
            
        # Обрезаем username до разумного размера
        if username and len(username) > 100:
            username = username[:100]
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                current_date = date.today().isoformat()
                
                await db.execute("""
                    INSERT INTO user_analytics 
                    (user_id, username, request_date, tokens_used) 
                    VALUES (?, ?, ?, ?)
                """, (user_id, username, current_date, tokens_used))
                
                await db.commit()
                
                logger.debug(f"Recorded usage: user_id={user_id}, username={username}, "
                           f"date={current_date}, tokens={tokens_used}")
                           
        except Exception as e:
            logger.error(f"Error recording usage for user {user_id}: {e}")
    
    async def get_user_daily_usage(self, user_id: int, target_date: str) -> int:
        """
        Получает общое количество токенов, использованных пользователем за день.
        
        Args:
            user_id: Telegram ID пользователя
            target_date: Дата в формате YYYY-MM-DD
            
        Returns:
            Общее количество токенов за день
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT SUM(tokens_used) as total_tokens
                    FROM user_analytics 
                    WHERE user_id = ? AND request_date = ?
                """, (user_id, target_date))
                
                result = await cursor.fetchone()
                return result[0] if result and result[0] else 0
                
        except Exception as e:
            logger.error(f"Error getting daily usage for user {user_id}: {e}")
            return 0
    
    async def get_user_total_usage(self, user_id: int) -> int:
        """
        Получает общее количество токенов, использованных пользователем за все время.
        
        Args:
            user_id: Telegram ID пользователя
            
        Returns:
            Общее количество токенов
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT SUM(tokens_used) as total_tokens
                    FROM user_analytics 
                    WHERE user_id = ?
                """, (user_id,))
                
                result = await cursor.fetchone()
                return result[0] if result and result[0] else 0
                
        except Exception as e:
            logger.error(f"Error getting total usage for user {user_id}: {e}")
            return 0
    
    async def get_all_users_usage_by_date(self, target_date: str) -> List[Dict[str, Any]]:
        """
        Получает использование токенов всеми пользователями за определенную дату.
        
        Args:
            target_date: Дата в формате YYYY-MM-DD
            
        Returns:
            Список словарей с данными о пользователях и их использовании
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT user_id, username, SUM(tokens_used) as total_tokens
                    FROM user_analytics 
                    WHERE request_date = ?
                    GROUP BY user_id, username
                    ORDER BY total_tokens DESC
                """, (target_date,))
                
                results = await cursor.fetchall()
                
                return [
                    {
                        "user_id": row[0],
                        "username": row[1],
                        "total_tokens": row[2]
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"Error getting usage by date {target_date}: {e}")
            return []
    
    async def get_user_usage_stats(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Получает статистику использования пользователя за последние N дней.
        
        Args:
            user_id: Telegram ID пользователя
            days: Количество дней для анализа
            
        Returns:
            Словарь со статистикой пользователя
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT 
                        request_date,
                        SUM(tokens_used) as daily_tokens
                    FROM user_analytics 
                    WHERE user_id = ? 
                    AND request_date >= date('now', '-{} days')
                    GROUP BY request_date
                    ORDER BY request_date DESC
                """.format(days), (user_id,))
                
                daily_stats = await cursor.fetchall()
                
                # Получаем общую статистику
                total_usage = await self.get_user_total_usage(user_id)
                
                return {
                    "user_id": user_id,
                    "total_tokens": total_usage,
                    "daily_usage": [
                        {"date": row[0], "tokens": row[1]} 
                        for row in daily_stats
                    ],
                    "days_analyzed": days
                }
                
        except Exception as e:
            logger.error(f"Error getting usage stats for user {user_id}: {e}")
            return {"user_id": user_id, "total_tokens": 0, "daily_usage": [], "days_analyzed": days}
    
    async def close(self) -> None:
        """
        Закрытие соединения с базой данных.
        В случае aiosqlite это не критично, но добавлено для совместимости.
        """
        logger.debug("User analytics connection closed")


# Глобальный экземпляр для использования в приложении
analytics = UserAnalytics() 