"""
Claude AI Agent с Function Calling
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from anthropic import Anthropic

from utils.logger import get_logger
from utils.config import load_config
from agent.tools import TOOLS, get_system_prompt, get_tool_by_name
from integrations.ollama_client import get_ollama_client, is_ollama_available

logger = get_logger(__name__)


class ClaudeAgent:
    """Класс для работы с Claude AI через Function Calling"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация агента

        Args:
            config: Конфигурация (если None, загружается автоматически)
        """
        if config is None:
            config = load_config()

        self.config = config
        self.api_key = config['claude']['api_key']
        self.model = config['claude'].get('model', 'claude-sonnet-4-20250514')
        self.haiku_model = config['claude'].get('haiku_model', 'claude-3-5-haiku-20241022')
        self.max_tokens = config['claude'].get('max_tokens', 4096)
        self.temperature = config['claude'].get('temperature', 0.7)
        self.use_dynamic_model = config['claude'].get('use_dynamic_model', True)
        self.use_ollama_fallback = config.get('ollama', {}).get('enabled', False)

        # Инициализация Anthropic клиента
        self.client = Anthropic(api_key=self.api_key)

        # Инициализация Ollama (если включен)
        self.ollama_client = None
        if self.use_ollama_fallback and is_ollama_available():
            self.ollama_client = get_ollama_client()
            logger.info("Ollama доступен для гибридного режима")

        logger.info(f"Claude Agent инициализирован (модель: {self.model}, Haiku: {self.haiku_model}, динамический выбор: {self.use_dynamic_model}, Ollama: {self.use_ollama_fallback})")

    def _classify_request_complexity(self, message: str) -> str:
        """
        Классифицирует сложность запроса для выбора модели

        Args:
            message: Текст запроса пользователя

        Returns:
            'simple' или 'complex'
        """
        message_lower = message.lower()

        # Простые команды - используем Haiku
        simple_patterns = [
            'добав', 'запиш', 'создай', 'напомни',
            'список', 'покупк', 'задач',
            'что у меня', 'покажи', 'когда',
            'удали', 'отмени'
        ]

        # Сложные запросы - используем Sonnet/Opus
        complex_patterns = [
            'проанализируй', 'сравни', 'объясни',
            'как лучше', 'посоветуй', 'помоги разобраться',
            'что думаешь', 'распиши подробно'
        ]

        # Проверка на сложные паттерны
        for pattern in complex_patterns:
            if pattern in message_lower:
                logger.debug(f"Запрос классифицирован как сложный (паттерн: {pattern})")
                return 'complex'

        # Проверка на простые паттерны
        for pattern in simple_patterns:
            if pattern in message_lower:
                logger.debug(f"Запрос классифицирован как простой (паттерн: {pattern})")
                return 'simple'

        # По умолчанию - длинные сообщения считаем сложными
        if len(message) > 100:
            logger.debug("Запрос классифицирован как сложный (длина > 100 символов)")
            return 'complex'

        logger.debug("Запрос классифицирован как простой (по умолчанию)")
        return 'simple'

    def _select_model(self, message: str) -> str:
        """
        Выбирает подходящую модель на основе сложности запроса

        Args:
            message: Текст запроса

        Returns:
            Название модели для использования
        """
        if not self.use_dynamic_model:
            return self.model

        complexity = self._classify_request_complexity(message)

        if complexity == 'simple':
            logger.info(f"Используем Haiku для простого запроса: {self.haiku_model}")
            return self.haiku_model
        else:
            logger.info(f"Используем основную модель для сложного запроса: {self.model}")
            return self.model

    def _can_use_ollama(self, message: str) -> bool:
        """
        Проверяет, можно ли использовать Ollama для данного запроса

        Args:
            message: Текст запроса

        Returns:
            True если Ollama подходит для этого запроса
        """
        if not self.ollama_client:
            return False

        # Ollama используется только для очень простых команд
        message_lower = message.lower()

        # Список команд, которые Ollama может обработать
        ollama_patterns = [
            'добав', 'запиш', 'создай', 'напомни',
            'покупк', 'молок', 'хлеб', 'яйц',
        ]

        for pattern in ollama_patterns:
            if pattern in message_lower and len(message) < 50:
                return True

        return False

    async def process_message(
        self,
        message: str,
        user_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Обрабатывает сообщение пользователя через Claude

        Args:
            message: Текст сообщения
            user_id: ID пользователя
            conversation_history: История разговора (опционально)

        Returns:
            Результат обработки с полями:
            - action: "confirm" или "executed"
            - action_type: тип действия
            - confirmation_text: текст для подтверждения (если action="confirm")
            - response_text: текст ответа пользователю
            - confirmation_id: ID подтверждения (если action="confirm")
            - tokens_used: количество использованных токенов
        """
        logger.info(f"Обработка сообщения от {user_id}: {message}")

        try:
            # Подготовить системный промпт с текущей датой/временем
            today = datetime.now().strftime("%Y-%m-%d (%A)")
            current_time = datetime.now().strftime("%H:%M")
            system_prompt = get_system_prompt(today, current_time)

            # Подготовить историю сообщений
            messages = []

            if conversation_history:
                for msg in conversation_history:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            # Добавить текущее сообщение
            messages.append({
                "role": "user",
                "content": message
            })

            # Выбрать подходящую модель
            selected_model = self._select_model(message)

            # Выполнить запрос к Claude
            response = self.client.messages.create(
                model=selected_model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                tools=TOOLS,
                messages=messages
            )

            logger.info(f"Получен ответ от Claude (stop_reason: {response.stop_reason})")

            # Подсчитать использованные токены
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            # Обработать ответ
            return await self._process_response(response, user_id, tokens_used)

        except Exception as e:
            logger.error(f"Ошибка при обработке через Claude: {e}", exc_info=True)
            return {
                "action": "executed",
                "action_type": "error",
                "response_text": f"❌ Произошла ошибка: {str(e)}",
                "tokens_used": 0
            }

    async def _process_response(
        self,
        response,
        user_id: str,
        tokens_used: int
    ) -> Dict[str, Any]:
        """
        Обрабатывает ответ от Claude

        Args:
            response: Ответ от Claude API
            user_id: ID пользователя
            tokens_used: Количество использованных токенов

        Returns:
            Результат обработки
        """
        # Если Claude хочет использовать инструменты
        if response.stop_reason == "tool_use":
            return await self._handle_tool_use(response, user_id, tokens_used)

        # Если Claude просто ответил текстом
        elif response.stop_reason == "end_turn":
            # Извлечь текстовый ответ
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content += block.text

            return {
                "action": "executed",
                "action_type": "general",
                "response_text": text_content,
                "tokens_used": tokens_used
            }

        else:
            logger.warning(f"Неожиданный stop_reason: {response.stop_reason}")
            return {
                "action": "executed",
                "action_type": "unknown",
                "response_text": "Получен ответ от ассистента",
                "tokens_used": tokens_used
            }

    async def _handle_tool_use(
        self,
        response,
        user_id: str,
        tokens_used: int
    ) -> Dict[str, Any]:
        """
        Обрабатывает использование инструментов Claude

        Args:
            response: Ответ от Claude с tool_use
            user_id: ID пользователя
            tokens_used: Количество использованных токенов

        Returns:
            Результат с запросом на подтверждение
        """
        # Извлечь все tool_use блоки
        tool_uses = [block for block in response.content if block.type == "tool_use"]

        if not tool_uses:
            return {
                "action": "executed",
                "action_type": "no_tools",
                "response_text": "Не удалось определить действие",
                "tokens_used": tokens_used
            }

        # Пока обрабатываем только первый инструмент
        tool_use = tool_uses[0]
        tool_name = tool_use.name
        tool_input = tool_use.input

        logger.info(f"Claude хочет использовать инструмент: {tool_name}")
        logger.debug(f"Параметры: {tool_input}")

        # Проверить, требует ли действие подтверждения
        requires_confirmation = self._requires_confirmation(tool_name)

        if requires_confirmation:
            # Создать запрос на подтверждение
            confirmation_id = str(uuid.uuid4())
            confirmation_text = self._generate_confirmation_text(tool_name, tool_input)

            return {
                "action": "confirm",
                "action_type": tool_name,
                "confirmation_id": confirmation_id,
                "confirmation_text": confirmation_text,
                "response_text": "",  # Будет заполнено после подтверждения
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tokens_used": tokens_used
            }
        else:
            # Выполнить действие сразу
            result = await self._execute_tool(tool_name, tool_input, user_id)

            return {
                "action": "executed",
                "action_type": tool_name,
                "response_text": result["message"],
                "tokens_used": tokens_used
            }

    def _requires_confirmation(self, tool_name: str) -> bool:
        """
        Проверяет, требует ли инструмент подтверждения

        Args:
            tool_name: Название инструмента

        Returns:
            True если требуется подтверждение
        """
        # Действия, требующие подтверждения
        confirmation_required = [
            "add_calendar_event",
            "add_task",
            "add_shopping_item",
            "create_note"
        ]

        return tool_name in confirmation_required

    def _generate_confirmation_text(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Генерирует текст запроса на подтверждение

        Args:
            tool_name: Название инструмента
            tool_input: Параметры инструмента

        Returns:
            Текст для подтверждения
        """
        if tool_name == "add_calendar_event":
            summary = tool_input.get("summary", "событие")
            start_time = tool_input.get("start_time", "")

            # Преобразовать ISO время в читаемый формат
            try:
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%d %B в %H:%M")
            except:
                formatted_time = start_time

            return f"📅 Правильно ли я понял: добавить событие '{summary}' на {formatted_time}?"

        elif tool_name == "add_task":
            title = tool_input.get("title", "задачу")
            return f"✅ Правильно ли я понял: добавить задачу '{title}'?"

        elif tool_name == "add_shopping_item":
            items = tool_input.get("items", [])
            items_str = ", ".join(items)
            return f"🛒 Правильно ли я понял: добавить в покупки: {items_str}?"

        elif tool_name == "create_note":
            title = tool_input.get("title", "заметку")
            return f"📝 Правильно ли я понял: создать заметку '{title}'?"

        else:
            return f"Правильно ли я понял: выполнить действие {tool_name}?"

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Выполняет инструмент

        Args:
            tool_name: Название инструмента
            tool_input: Параметры
            user_id: ID пользователя

        Returns:
            Результат выполнения с полем "message"
        """
        logger.info(f"Выполнение инструмента: {tool_name}")

        try:
            # Импорты интеграций
            from integrations.google_calendar import get_calendar
            from integrations.google_tasks import get_tasks as get_tasks_client
            from integrations.obsidian import get_vault

            if tool_name == "add_calendar_event":
                # Интеграция с Google Calendar (асинхронно)
                calendar = get_calendar()
                result = await calendar.add_event_async(
                    summary=tool_input.get('summary'),
                    start_time=tool_input.get('start_time'),
                    end_time=tool_input.get('end_time'),
                    description=tool_input.get('description'),
                    location=tool_input.get('location')
                )
                return {
                    "success": True,
                    "message": f"✅ Событие '{tool_input.get('summary')}' добавлено в календарь"
                }

            elif tool_name == "get_calendar_events":
                # Интеграция с Google Calendar (асинхронно)
                calendar = get_calendar()
                events = await calendar.get_events_async(
                    time_min=tool_input.get('time_min'),
                    time_max=tool_input.get('time_max'),
                    max_results=tool_input.get('max_results', 10)
                )

                if not events:
                    return {
                        "success": True,
                        "message": "📅 События не найдены"
                    }

                # Форматировать события для ответа
                events_text = []
                for event in events:
                    start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                    events_text.append(f"• {event['summary']} ({start.strftime('%d.%m в %H:%M')})")

                return {
                    "success": True,
                    "message": f"📅 Найдено событий: {len(events)}\n" + "\n".join(events_text)
                }

            elif tool_name == "add_task":
                # Интеграция с Google Tasks
                tasks = get_tasks_client()
                result = tasks.add_task(
                    title=tool_input.get('title'),
                    notes=tool_input.get('notes'),
                    due_date=tool_input.get('due_date')
                )
                return {
                    "success": True,
                    "message": f"✅ Задача '{tool_input.get('title')}' добавлена"
                }

            elif tool_name == "add_shopping_item":
                # Интеграция с Google Tasks
                tasks = get_tasks_client()
                items = tool_input.get("items", [])
                result = tasks.add_shopping_items(items)
                return {
                    "success": True,
                    "message": f"🛒 Добавлено в покупки: {', '.join(items)}"
                }

            elif tool_name == "get_tasks":
                # Интеграция с Google Tasks
                tasks_client = get_tasks_client()
                task_list = tool_input.get('task_list', 'tasks')
                show_completed = tool_input.get('show_completed', False)

                if task_list == 'shopping':
                    task_list_items = tasks_client.get_shopping_list(show_completed)
                else:
                    task_list_items = tasks_client.get_tasks(show_completed=show_completed)

                if not task_list_items:
                    return {
                        "success": True,
                        "message": "📋 Задачи не найдены"
                    }

                # Форматировать задачи
                tasks_text = []
                for task in task_list_items:
                    status_icon = "✅" if task['status'] == 'completed' else "⬜"
                    tasks_text.append(f"{status_icon} {task['title']}")

                return {
                    "success": True,
                    "message": f"📋 Найдено задач: {len(task_list_items)}\n" + "\n".join(tasks_text[:10])
                }

            elif tool_name == "create_note":
                # Интеграция с Obsidian
                vault = get_vault()
                result = vault.create_note(
                    title=tool_input.get('title'),
                    content=tool_input.get('content'),
                    tags=tool_input.get('tags')
                )
                return {
                    "success": True,
                    "message": f"📝 Заметка '{tool_input.get('title')}' создана в Obsidian"
                }

            elif tool_name == "search_notes":
                # Интеграция с Obsidian
                vault = get_vault()
                results = vault.search_notes(
                    query=tool_input.get('query'),
                    limit=tool_input.get('limit', 5)
                )

                if not results:
                    return {
                        "success": True,
                        "message": f"🔍 Заметки по запросу '{tool_input.get('query')}' не найдены"
                    }

                # Форматировать результаты
                notes_text = []
                for note in results:
                    notes_text.append(f"• {note['title']}")

                return {
                    "success": True,
                    "message": f"🔍 Найдено заметок: {len(results)}\n" + "\n".join(notes_text)
                }

            else:
                return {
                    "success": False,
                    "message": f"❌ Неизвестный инструмент: {tool_name}"
                }

        except Exception as e:
            logger.error(f"Ошибка при выполнении инструмента {tool_name}: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"❌ Ошибка при выполнении действия: {str(e)}"
            }

    async def execute_confirmed_action(
        self,
        confirmation_data: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Выполняет действие после подтверждения пользователем

        Args:
            confirmation_data: Данные подтверждения (из БД)
            user_id: ID пользователя

        Returns:
            Результат выполнения
        """
        action_data = json.loads(confirmation_data['action_data'])

        tool_name = action_data.get('tool_name')
        tool_input = action_data.get('tool_input')

        if not tool_name or not tool_input:
            return {
                "success": False,
                "message": "❌ Некорректные данные подтверждения"
            }

        # Выполнить инструмент
        result = await self._execute_tool(tool_name, tool_input, user_id)

        return result
