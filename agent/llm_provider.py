"""
Абстракция для работы с различными LLM провайдерами
Позволяет легко переключаться между Claude API и Ollama
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LLMResponse:
    """Унифицированный ответ от LLM"""
    text: str
    model_used: str
    tokens_used: int
    stop_reason: str
    raw_response: Any = None


class LLMProvider(ABC):
    """Базовый класс для LLM провайдера"""

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        tools: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """
        Генерирует ответ от LLM

        Args:
            messages: История сообщений
            system_prompt: Системный промпт
            tools: Список доступных инструментов (function calling)
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов

        Returns:
            LLMResponse с текстом ответа и метаданными
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Проверяет доступность провайдера"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Возвращает название провайдера"""
        pass


class ClaudeProvider(LLMProvider):
    """Провайдер для Claude API (Anthropic)"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Инициализация Claude провайдера

        Args:
            api_key: API ключ Anthropic
            model: Модель Claude для использования
        """
        from anthropic import Anthropic

        self.client = Anthropic(api_key=api_key)
        self.model = model
        logger.info(f"Claude провайдер инициализирован (модель: {model})")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        tools: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """Генерирует ответ через Claude API"""
        logger.debug(f"Запрос к Claude (модель: {self.model})")

        try:
            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            if tools:
                kwargs["tools"] = tools

            response = self.client.messages.create(**kwargs)

            # Извлечь текстовый контент
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content += block.text

            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            logger.info(f"Получен ответ от Claude (токенов: {tokens_used})")

            return LLMResponse(
                text=text_content,
                model_used=self.model,
                tokens_used=tokens_used,
                stop_reason=response.stop_reason,
                raw_response=response
            )

        except Exception as e:
            logger.error(f"Ошибка Claude API: {e}", exc_info=True)
            raise

    def is_available(self) -> bool:
        """Claude всегда доступен если есть API ключ"""
        return True

    def get_name(self) -> str:
        return f"Claude ({self.model})"


class OllamaProvider(LLMProvider):
    """Провайдер для локального Ollama"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        """
        Инициализация Ollama провайдера

        Args:
            base_url: URL Ollama сервера
            model: Модель для использования
        """
        import requests

        self.base_url = base_url
        self.model = model
        self.api_url = f"{base_url}/api"
        self._requests = requests

        logger.info(f"Ollama провайдер инициализирован (модель: {model})")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        tools: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """Генерирует ответ через Ollama"""
        logger.debug(f"Запрос к Ollama (модель: {self.model})")

        # Примечание: Ollama не поддерживает function calling напрямую
        # Для простых команд это не нужно

        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }

            if system_prompt:
                # Добавить системный промпт как первое сообщение
                payload["messages"] = [
                    {"role": "system", "content": system_prompt}
                ] + messages

            response = self._requests.post(
                f"{self.api_url}/chat",
                json=payload,
                timeout=60
            )

            response.raise_for_status()
            result = response.json()

            message = result.get("message", {})
            text = message.get("content", "").strip()

            # Ollama не возвращает точное количество токенов
            # Приблизительная оценка: 1 токен ≈ 4 символа
            tokens_used = len(text) // 4

            logger.info(f"Получен ответ от Ollama (символов: {len(text)})")

            return LLMResponse(
                text=text,
                model_used=self.model,
                tokens_used=tokens_used,
                stop_reason="stop",
                raw_response=result
            )

        except Exception as e:
            logger.error(f"Ошибка Ollama API: {e}", exc_info=True)
            raise

    def is_available(self) -> bool:
        """Проверяет доступность Ollama сервера"""
        try:
            response = self._requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def get_name(self) -> str:
        return f"Ollama ({self.model})"


class HybridLLMRouter:
    """
    Умный роутер между несколькими LLM провайдерами
    Выбирает оптимальный провайдер на основе сложности запроса
    """

    def __init__(
        self,
        primary_provider: LLMProvider,
        fallback_provider: Optional[LLMProvider] = None,
        use_fallback_for_simple: bool = False
    ):
        """
        Инициализация роутера

        Args:
            primary_provider: Основной провайдер (Claude)
            fallback_provider: Резервный провайдер (Ollama)
            use_fallback_for_simple: Использовать fallback для простых запросов
        """
        self.primary = primary_provider
        self.fallback = fallback_provider
        self.use_fallback_for_simple = use_fallback_for_simple

        logger.info(f"Hybrid роутер инициализирован:")
        logger.info(f"  - Основной: {primary_provider.get_name()}")
        if fallback_provider:
            logger.info(f"  - Резервный: {fallback_provider.get_name()}")
            logger.info(f"  - Использовать резервный для простых: {use_fallback_for_simple}")

    def classify_complexity(self, message: str) -> str:
        """
        Классифицирует сложность запроса

        Args:
            message: Текст сообщения

        Returns:
            'simple' или 'complex'
        """
        message_lower = message.lower()

        # Простые команды
        simple_patterns = [
            'добав', 'запиш', 'создай', 'напомни',
            'список', 'покупк', 'задач',
            'что у меня', 'покажи', 'когда',
            'удали', 'отмени'
        ]

        # Сложные запросы
        complex_patterns = [
            'проанализируй', 'сравни', 'объясни',
            'как лучше', 'посоветуй', 'помоги разобраться',
            'что думаешь', 'распиши подробно'
        ]

        # Проверка на сложные паттерны
        for pattern in complex_patterns:
            if pattern in message_lower:
                return 'complex'

        # Проверка на простые паттерны
        for pattern in simple_patterns:
            if pattern in message_lower:
                return 'simple'

        # Длинные сообщения считаем сложными
        if len(message) > 100:
            return 'complex'

        return 'simple'

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        tools: List[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        force_primary: bool = False
    ) -> LLMResponse:
        """
        Генерирует ответ через подходящий провайдер

        Args:
            messages: История сообщений
            system_prompt: Системный промпт
            tools: Инструменты (function calling)
            temperature: Температура
            max_tokens: Максимум токенов
            force_primary: Принудительно использовать основной провайдер

        Returns:
            LLMResponse от выбранного провайдера
        """
        # Определить сложность последнего сообщения
        last_message = messages[-1]["content"] if messages else ""
        complexity = self.classify_complexity(last_message)

        # Выбрать провайдер
        use_fallback = (
            not force_primary and
            self.fallback is not None and
            self.use_fallback_for_simple and
            complexity == 'simple' and
            tools is None  # Ollama не поддерживает function calling
        )

        if use_fallback and self.fallback.is_available():
            logger.info(f"Используем резервный провайдер для простого запроса: {self.fallback.get_name()}")
            provider = self.fallback
        else:
            logger.info(f"Используем основной провайдер: {self.primary.get_name()}")
            provider = self.primary

        # Генерация
        try:
            response = await provider.generate(
                messages=messages,
                system_prompt=system_prompt,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens
            )

            logger.info(f"Ответ получен от {provider.get_name()} (токенов: {response.tokens_used})")
            return response

        except Exception as e:
            # Если основной провайдер упал - попробовать резервный
            if provider == self.primary and self.fallback and self.fallback.is_available():
                logger.warning(f"Основной провайдер недоступен, используем резервный")
                return await self.fallback.generate(
                    messages=messages,
                    system_prompt=system_prompt,
                    tools=None,  # Ollama не поддерживает tools
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            else:
                raise


def create_llm_router(config: Dict[str, Any]) -> HybridLLMRouter:
    """
    Создаёт LLM роутер на основе конфигурации

    Args:
        config: Конфигурация проекта

    Returns:
        Настроенный HybridLLMRouter
    """
    # Создать Claude провайдер (основной)
    claude_config = config.get('claude', {})
    primary = ClaudeProvider(
        api_key=claude_config['api_key'],
        model=claude_config.get('model', 'claude-sonnet-4-20250514')
    )

    # Создать Ollama провайдер (если включен)
    fallback = None
    ollama_config = config.get('ollama', {})
    if ollama_config.get('enabled', False):
        try:
            fallback = OllamaProvider(
                base_url=ollama_config.get('url', 'http://localhost:11434'),
                model=ollama_config.get('model', 'llama3.2')
            )

            # Проверить доступность
            if not fallback.is_available():
                logger.warning("Ollama включен в конфиге, но сервер недоступен")
                fallback = None
        except Exception as e:
            logger.warning(f"Не удалось инициализировать Ollama: {e}")
            fallback = None

    # Создать роутер
    router = HybridLLMRouter(
        primary_provider=primary,
        fallback_provider=fallback,
        use_fallback_for_simple=ollama_config.get('enabled', False)
    )

    return router
