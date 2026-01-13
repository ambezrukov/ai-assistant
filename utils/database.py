"""
Модуль работы с базой данных SQLite
"""

import aiosqlite
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)


class Database:
    """Класс для работы с SQLite базой данных"""

    def __init__(self, db_path: str = "data/assistant.db"):
        """
        Инициализация базы данных

        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self._ensure_db_directory()

    def _ensure_db_directory(self):
        """Создает директорию для БД, если не существует"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Создана директория для БД: {db_dir}")

    async def init_db(self):
        """Инициализирует таблицы в базе данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица для хранения истории сообщений
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT
                )
            """)

            # Таблица для подтверждений действий
            await db.execute("""
                CREATE TABLE IF NOT EXISTS confirmations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    action_data TEXT NOT NULL,
                    confirmation_text TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at DATETIME
                )
            """)

            # Таблица для статистики использования
            await db.execute("""
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    interface TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    tokens_used INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Индексы для оптимизации запросов
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_user_id
                ON messages(user_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp
                ON messages(timestamp)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_confirmations_user_id
                ON confirmations(user_id)
            """)

            await db.commit()
            logger.info("База данных инициализирована")

    async def save_message(
        self,
        user_id: str,
        role: str,
        content: str,
        session_id: Optional[str] = None
    ) -> int:
        """
        Сохраняет сообщение в историю

        Args:
            user_id: ID пользователя
            role: Роль (user/assistant)
            content: Содержимое сообщения
            session_id: ID сессии (опционально)

        Returns:
            ID созданной записи
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO messages (user_id, role, content, session_id)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, role, content, session_id)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_message_history(
        self,
        user_id: str,
        limit: int = 10,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает историю сообщений пользователя

        Args:
            user_id: ID пользователя
            limit: Максимальное количество сообщений
            session_id: ID сессии (если нужна история конкретной сессии)

        Returns:
            Список сообщений
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if session_id:
                cursor = await db.execute(
                    """
                    SELECT * FROM messages
                    WHERE user_id = ? AND session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (user_id, session_id, limit)
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM messages
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (user_id, limit)
                )

            rows = await cursor.fetchall()
            return [dict(row) for row in reversed(rows)]

    async def save_confirmation(
        self,
        confirmation_id: str,
        user_id: str,
        action_type: str,
        action_data: str,
        confirmation_text: str
    ) -> None:
        """
        Сохраняет запрос на подтверждение

        Args:
            confirmation_id: Уникальный ID подтверждения
            user_id: ID пользователя
            action_type: Тип действия
            action_data: Данные действия (JSON)
            confirmation_text: Текст подтверждения
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO confirmations
                (id, user_id, action_type, action_data, confirmation_text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (confirmation_id, user_id, action_type, action_data, confirmation_text)
            )
            await db.commit()
            logger.info(f"Сохранен запрос на подтверждение: {confirmation_id}")

    async def get_confirmation(self, confirmation_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные подтверждения

        Args:
            confirmation_id: ID подтверждения

        Returns:
            Данные подтверждения или None
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM confirmations WHERE id = ?",
                (confirmation_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_confirmation_status(
        self,
        confirmation_id: str,
        status: str
    ) -> None:
        """
        Обновляет статус подтверждения

        Args:
            confirmation_id: ID подтверждения
            status: Новый статус (confirmed/rejected)
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE confirmations
                SET status = ?, confirmed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, confirmation_id)
            )
            await db.commit()
            logger.info(f"Обновлен статус подтверждения {confirmation_id}: {status}")

    async def save_usage_stats(
        self,
        user_id: str,
        interface: str,
        action_type: str,
        tokens_used: int = 0
    ) -> None:
        """
        Сохраняет статистику использования

        Args:
            user_id: ID пользователя
            interface: Интерфейс (telegram/api)
            action_type: Тип действия
            tokens_used: Количество использованных токенов
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO usage_stats (user_id, interface, action_type, tokens_used)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, interface, action_type, tokens_used)
            )
            await db.commit()

    async def get_usage_stats(
        self,
        user_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Получает статистику использования за период

        Args:
            user_id: ID пользователя
            days: Количество дней

        Returns:
            Список записей статистики
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM usage_stats
                WHERE user_id = ?
                AND timestamp >= datetime('now', '-' || ? || ' days')
                ORDER BY timestamp DESC
                """,
                (user_id, days)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def cleanup_old_data(self, days: int = 30) -> None:
        """
        Очищает старые данные из базы

        Args:
            days: Удалить данные старше указанного количества дней
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Удалить старые сообщения
            await db.execute(
                """
                DELETE FROM messages
                WHERE timestamp < datetime('now', '-' || ? || ' days')
                """,
                (days,)
            )

            # Удалить старые подтверждения
            await db.execute(
                """
                DELETE FROM confirmations
                WHERE created_at < datetime('now', '-' || ? || ' days')
                """,
                (days,)
            )

            await db.commit()
            logger.info(f"Удалены данные старше {days} дней")
