#!/usr/bin/env python3
"""
Скрипт для просмотра аналитики пользователей бота.
Показывает данные из базы данных user_analytics.db.
"""

import asyncio
import sys
from datetime import date, timedelta
from user_analytics import analytics


async def show_all_data():
    """Показывает все записи в базе данных."""
    try:
        import aiosqlite
        async with aiosqlite.connect(analytics.db_path) as db:
            cursor = await db.execute("""
                SELECT user_id, username, request_date, tokens_used, created_at
                FROM user_analytics 
                ORDER BY created_at DESC
                LIMIT 50
            """)
            
            results = await cursor.fetchall()
            
            if not results:
                print("📊 База данных пуста - данных пока нет.")
                return
                
            print("📊 Последние 50 записей в базе данных:")
            print("-" * 80)
            print(f"{'User ID':<12} {'Username':<15} {'Date':<12} {'Tokens':<8} {'Created At':<20}")
            print("-" * 80)
            
            for row in results:
                user_id, username, req_date, tokens, created_at = row
                username_short = (username[:12] + "...") if username and len(username) > 15 else (username or "N/A")
                print(f"{user_id:<12} {username_short:<15} {req_date:<12} {tokens:<8} {created_at[:19]:<20}")
                
    except Exception as e:
        print(f"❌ Ошибка при чтении данных: {e}")


async def show_user_stats():
    """Показывает статистику по пользователям."""
    try:
        import aiosqlite
        async with aiosqlite.connect(analytics.db_path) as db:
            # Общая статистика по пользователям
            cursor = await db.execute("""
                SELECT 
                    user_id, 
                    username,
                    SUM(tokens_used) as total_tokens,
                    COUNT(*) as requests_count,
                    MIN(request_date) as first_date,
                    MAX(request_date) as last_date
                FROM user_analytics 
                GROUP BY user_id, username
                ORDER BY total_tokens DESC
            """)
            
            results = await cursor.fetchall()
            
            if not results:
                print("📊 Статистика пользователей пуста.")
                return
                
            print("\n📈 Статистика по пользователям:")
            print("-" * 90)
            print(f"{'User ID':<12} {'Username':<15} {'Total Tokens':<12} {'Requests':<10} {'First Use':<12} {'Last Use':<12}")
            print("-" * 90)
            
            for row in results:
                user_id, username, total_tokens, requests, first_date, last_date = row
                username_short = (username[:12] + "...") if username and len(username) > 15 else (username or "N/A")
                print(f"{user_id:<12} {username_short:<15} {total_tokens:<12} {requests:<10} {first_date:<12} {last_date:<12}")
                
    except Exception as e:
        print(f"❌ Ошибка при получении статистики: {e}")


async def show_daily_stats():
    """Показывает статистику по дням."""
    try:
        import aiosqlite
        async with aiosqlite.connect(analytics.db_path) as db:
            cursor = await db.execute("""
                SELECT 
                    request_date,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(*) as total_requests,
                    SUM(tokens_used) as total_tokens,
                    AVG(tokens_used) as avg_tokens
                FROM user_analytics 
                GROUP BY request_date
                ORDER BY request_date DESC
                LIMIT 30
            """)
            
            results = await cursor.fetchall()
            
            if not results:
                print("📊 Дневная статистика пуста.")
                return
                
            print("\n📅 Статистика по дням (последние 30 дней):")
            print("-" * 80)
            print(f"{'Date':<12} {'Users':<8} {'Requests':<10} {'Total Tokens':<12} {'Avg Tokens':<12}")
            print("-" * 80)
            
            for row in results:
                req_date, unique_users, total_requests, total_tokens, avg_tokens = row
                avg_tokens_rounded = round(avg_tokens, 1) if avg_tokens else 0
                print(f"{req_date:<12} {unique_users:<8} {total_requests:<10} {total_tokens:<12} {avg_tokens_rounded:<12}")
                
    except Exception as e:
        print(f"❌ Ошибка при получении дневной статистики: {e}")


async def show_database_info():
    """Показывает общую информацию о базе данных."""
    try:
        import aiosqlite
        import os
        
        if not os.path.exists(analytics.db_path):
            print(f"❌ База данных не найдена: {analytics.db_path}")
            return
            
        file_size = os.path.getsize(analytics.db_path)
        
        async with aiosqlite.connect(analytics.db_path) as db:
            # Общее количество записей
            cursor = await db.execute("SELECT COUNT(*) FROM user_analytics")
            total_records = (await cursor.fetchone())[0]
            
            # Количество уникальных пользователей
            cursor = await db.execute("SELECT COUNT(DISTINCT user_id) FROM user_analytics")
            unique_users = (await cursor.fetchone())[0]
            
            # Общее количество токенов
            cursor = await db.execute("SELECT SUM(tokens_used) FROM user_analytics")
            total_tokens = (await cursor.fetchone())[0] or 0
            
            # Дата первой и последней записи
            cursor = await db.execute("SELECT MIN(created_at), MAX(created_at) FROM user_analytics")
            date_range = await cursor.fetchone()
            
            print(f"🗃️  Информация о базе данных:")
            print(f"   📍 Путь: {analytics.db_path}")
            print(f"   📏 Размер файла: {file_size} байт ({file_size/1024:.1f} KB)")
            print(f"   📊 Всего записей: {total_records}")
            print(f"   👥 Уникальных пользователей: {unique_users}")
            print(f"   🎯 Общее количество токенов: {total_tokens}")
            if date_range[0] and date_range[1]:
                print(f"   📅 Период данных: {date_range[0][:19]} - {date_range[1][:19]}")
                
    except Exception as e:
        print(f"❌ Ошибка при получении информации о базе: {e}")


async def main():
    """Основная функция для отображения аналитики."""
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command in ['help', '-h', '--help']:
            print("🔍 Использование:")
            print("  python view_analytics.py           - показать все данные")
            print("  python view_analytics.py users     - статистика по пользователям") 
            print("  python view_analytics.py daily     - статистика по дням")
            print("  python view_analytics.py info      - информация о базе")
            print("  python view_analytics.py help      - эта справка")
            return
        elif command == 'users':
            await show_database_info()
            await show_user_stats()
            return
        elif command == 'daily':
            await show_database_info()
            await show_daily_stats()
            return
        elif command == 'info':
            await show_database_info()
            return
    
    # По умолчанию показываем всё
    await show_database_info()
    await show_all_data()
    await show_user_stats()
    await show_daily_stats()


if __name__ == "__main__":
    print("🚀 Просмотр аналитики Telegram GPT Bot")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Просмотр прерван пользователем")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc() 