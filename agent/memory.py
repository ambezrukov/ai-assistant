"""
Система персистентной памяти для AI-ассистента
Хранит историю действий, частые паттерны и предпочтения пользователя
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
import json

from utils.database import Database
from utils.logger import get_logger

logger = get_logger(__name__)


class UserMemory:
    """
    Персистентная память для пользователя
    Анализирует историю и предоставляет контекст для улучшения ответов
    """

    def __init__(self, user_id: str, db: Database):
        """
        Инициализация памяти пользователя

        Args:
            user_id: ID пользователя
            db: Экземпляр базы данных
        """
        self.user_id = user_id
        self.db = db
        logger.debug(f"Инициализирована память для пользователя {user_id}")

    async def get_context_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Получает сводку контекста пользователя за период

        Args:
            days: Количество дней для анализа

        Returns:
            Словарь с контекстной информацией
        """
        logger.info(f"Получение контекста для {self.user_id} за {days} дней")

        # Получить статистику действий
        stats = await self.db.get_usage_stats(self.user_id, days=days)

        # Получить недавние сообщения
        recent_messages = await self.db.get_message_history(self.user_id, limit=50)

        # Анализировать частые действия
        action_types = [stat['action_type'] for stat in stats]
        frequent_actions = Counter(action_types).most_common(5)

        # Анализировать частые слова в запросах
        user_messages = [msg['content'] for msg in recent_messages if msg['role'] == 'user']
        frequent_keywords = self._extract_frequent_keywords(user_messages)

        # Определить временные паттерны (когда пользователь активен)
        active_hours = self._analyze_active_hours(recent_messages)

        summary = {
            "user_id": self.user_id,
            "total_interactions": len(stats),
            "frequent_actions": [
                {"action": action, "count": count}
                for action, count in frequent_actions
            ],
            "frequent_keywords": frequent_keywords,
            "active_hours": active_hours,
            "last_interaction": recent_messages[0]['timestamp'] if recent_messages else None
        }

        logger.debug(f"Сводка контекста: {summary}")
        return summary

    def _extract_frequent_keywords(self, messages: List[str], top_n: int = 10) -> List[str]:
        """
        Извлекает частые ключевые слова из сообщений

        Args:
            messages: Список сообщений
            top_n: Количество топовых слов

        Returns:
            Список частых ключевых слов
        """
        # Простой анализ: разделить на слова и посчитать частоту
        # Исключить стоп-слова
        stop_words = {
            'в', 'на', 'и', 'с', 'по', 'для', 'не', 'что', 'это', 'как',
            'а', 'я', 'у', 'из', 'за', 'к', 'до', 'о', 'об', 'от', 'про',
            'добавь', 'покажи', 'создай', 'запиши', 'напомни'
        }

        words = []
        for msg in messages:
            # Привести к нижнему регистру и разделить
            msg_words = msg.lower().split()
            # Фильтровать стоп-слова и короткие слова
            words.extend([
                word for word in msg_words
                if len(word) > 3 and word not in stop_words
            ])

        # Посчитать частоту
        counter = Counter(words)
        return [word for word, count in counter.most_common(top_n)]

    def _analyze_active_hours(self, messages: List[Dict[str, Any]]) -> List[int]:
        """
        Анализирует в какие часы пользователь наиболее активен

        Args:
            messages: История сообщений

        Returns:
            Список часов (0-23) когда пользователь активен
        """
        hours = []
        for msg in messages:
            try:
                timestamp = datetime.fromisoformat(msg['timestamp'])
                hours.append(timestamp.hour)
            except:
                continue

        # Найти часы с наибольшей активностью
        if not hours:
            return []

        counter = Counter(hours)
        # Вернуть часы с активностью выше среднего
        avg_activity = sum(counter.values()) / len(counter)
        active_hours = [hour for hour, count in counter.items() if count > avg_activity]

        return sorted(active_hours)

    async def get_frequent_shopping_items(self, limit: int = 10) -> List[str]:
        """
        Получает часто покупаемые товары

        Args:
            limit: Максимальное количество товаров

        Returns:
            Список частых товаров
        """
        logger.info(f"Получение частых покупок для {self.user_id}")

        # Получить историю сообщений с действиями add_shopping_item
        messages = await self.db.get_message_history(self.user_id, limit=200)

        shopping_items = []
        for msg in messages:
            if msg['role'] == 'user' and any(
                keyword in msg['content'].lower()
                for keyword in ['молоко', 'хлеб', 'яйца', 'сыр', 'масло', 'покупк']
            ):
                # Извлечь возможные названия товаров
                words = msg['content'].lower().split()
                # Простая эвристика: слова после "добавь", "купить"
                for i, word in enumerate(words):
                    if word in ['добавь', 'купить', 'купи'] and i + 1 < len(words):
                        item = words[i + 1].strip(',.:;')
                        if len(item) > 2:
                            shopping_items.append(item)

        # Посчитать частоту
        counter = Counter(shopping_items)
        return [item for item, count in counter.most_common(limit)]

    async def get_context_prompt(self) -> str:
        """
        Генерирует текстовый промпт с контекстом пользователя
        для добавления в системный промпт LLM

        Returns:
            Текст с контекстом
        """
        summary = await self.get_context_summary(days=30)

        # Формировать человеко-читаемый контекст
        context_parts = []

        if summary['total_interactions'] > 0:
            context_parts.append(f"Пользователь взаимодействовал с ассистентом {summary['total_interactions']} раз за последний месяц.")

        if summary['frequent_actions']:
            actions_str = ", ".join([
                f"{action['action']}" for action in summary['frequent_actions'][:3]
            ])
            context_parts.append(f"Частые действия: {actions_str}.")

        if summary['frequent_keywords']:
            keywords_str = ", ".join(summary['frequent_keywords'][:5])
            context_parts.append(f"Часто упоминаемые темы: {keywords_str}.")

        # Получить частые покупки
        frequent_items = await self.get_frequent_shopping_items(limit=5)
        if frequent_items:
            items_str = ", ".join(frequent_items)
            context_parts.append(f"Часто покупаемые товары: {items_str}.")

        if summary['active_hours']:
            # Определить время суток
            morning = any(h in range(6, 12) for h in summary['active_hours'])
            afternoon = any(h in range(12, 18) for h in summary['active_hours'])
            evening = any(h in range(18, 23) for h in summary['active_hours'])

            times = []
            if morning:
                times.append("утром")
            if afternoon:
                times.append("днём")
            if evening:
                times.append("вечером")

            if times:
                context_parts.append(f"Пользователь обычно активен {' и '.join(times)}.")

        if not context_parts:
            return "Это новый пользователь."

        return " ".join(context_parts)


class MemoryManager:
    """
    Менеджер памяти для всех пользователей
    Управляет созданием и хранением экземпляров UserMemory
    """

    def __init__(self, db: Database):
        """
        Инициализация менеджера памяти

        Args:
            db: Экземпляр базы данных
        """
        self.db = db
        self._cache: Dict[str, UserMemory] = {}
        logger.info("MemoryManager инициализирован")

    def get_user_memory(self, user_id: str) -> UserMemory:
        """
        Получает или создаёт память пользователя

        Args:
            user_id: ID пользователя

        Returns:
            UserMemory для данного пользователя
        """
        if user_id not in self._cache:
            self._cache[user_id] = UserMemory(user_id, self.db)

        return self._cache[user_id]

    async def get_enriched_system_prompt(
        self,
        base_prompt: str,
        user_id: str
    ) -> str:
        """
        Обогащает системный промпт контекстом пользователя

        Args:
            base_prompt: Базовый системный промпт
            user_id: ID пользователя

        Returns:
            Обогащённый промпт
        """
        user_memory = self.get_user_memory(user_id)
        user_context = await user_memory.get_context_prompt()

        enriched_prompt = f"""{base_prompt}

## Контекст пользователя

{user_context}

Используй эту информацию, чтобы лучше понимать запросы пользователя и предлагать релевантные действия."""

        logger.debug(f"Системный промпт обогащён контекстом для {user_id}")
        return enriched_prompt

    async def save_action_pattern(
        self,
        user_id: str,
        action_type: str,
        action_data: Dict[str, Any]
    ):
        """
        Сохраняет паттерн действия для будущего анализа

        Args:
            user_id: ID пользователя
            action_type: Тип действия
            action_data: Данные действия
        """
        # Сохранить в статистику
        await self.db.save_usage_stats(
            user_id=user_id,
            interface='memory',
            action_type=action_type,
            tokens_used=0
        )

        logger.debug(f"Сохранён паттерн действия: {action_type} для {user_id}")

    async def cleanup_old_memories(self, days: int = 90):
        """
        Очищает старые записи памяти

        Args:
            days: Удалить данные старше указанного количества дней
        """
        logger.info(f"Очистка памяти старше {days} дней")
        await self.db.cleanup_old_data(days=days)


# Глобальный экземпляр менеджера памяти
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(db: Optional[Database] = None) -> MemoryManager:
    """
    Получает глобальный экземпляр MemoryManager

    Args:
        db: Database экземпляр (если нужно создать новый менеджер)

    Returns:
        MemoryManager
    """
    global _memory_manager

    if _memory_manager is None:
        if db is None:
            from utils.config import load_config
            config = load_config()
            db = Database(config['database']['path'])

        _memory_manager = MemoryManager(db)

    return _memory_manager
