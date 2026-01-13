"""
Интеграция с Ollama для локальной LLM
"""

import json
from typing import Dict, Any, List, Optional
import requests

from utils.config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)

# Загрузить конфигурацию
config = load_config()
ollama_config = config.get('ollama', {})
OLLAMA_URL = ollama_config.get('url', 'http://localhost:11434')
OLLAMA_MODEL = ollama_config.get('model', 'llama3.2')
OLLAMA_ENABLED = ollama_config.get('enabled', False)


class OllamaClient:
    """Клиент для работы с Ollama"""

    def __init__(self, base_url: str = None, model: str = None):
        """
        Инициализация клиента Ollama

        Args:
            base_url: URL Ollama сервера
            model: Название модели
        """
        self.base_url = base_url or OLLAMA_URL
        self.model = model or OLLAMA_MODEL
        self.api_url = f"{self.base_url}/api"

        logger.info(f"Ollama клиент инициализирован (URL: {self.base_url}, модель: {self.model})")

    def is_available(self) -> bool:
        """
        Проверяет доступность Ollama сервера

        Returns:
            True если сервер доступен
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama не доступен: {e}")
            return False

    def generate(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Генерирует ответ через Ollama

        Args:
            prompt: Запрос пользователя
            system: Системный промпт
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов

        Returns:
            Текст ответа

        Raises:
            Exception: При ошибке запроса
        """
        logger.info(f"Генерация ответа через Ollama (модель: {self.model})")

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }

            if system:
                payload["system"] = system

            response = requests.post(
                f"{self.api_url}/generate",
                json=payload,
                timeout=60
            )

            response.raise_for_status()
            result = response.json()

            text = result.get("response", "").strip()
            logger.info(f"Получен ответ от Ollama ({len(text)} символов)")

            return text

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка Ollama API: {e}", exc_info=True)
            raise Exception(f"Ollama API error: {str(e)}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Генерирует ответ в формате чата

        Args:
            messages: История сообщений [{"role": "user", "content": "..."}]
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов

        Returns:
            Текст ответа
        """
        logger.info(f"Чат-запрос к Ollama (модель: {self.model})")

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

            response = requests.post(
                f"{self.api_url}/chat",
                json=payload,
                timeout=60
            )

            response.raise_for_status()
            result = response.json()

            message = result.get("message", {})
            text = message.get("content", "").strip()

            logger.info(f"Получен ответ от Ollama ({len(text)} символов)")

            return text

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка Ollama chat API: {e}", exc_info=True)
            raise Exception(f"Ollama chat API error: {str(e)}")

    def classify_intent(self, message: str) -> Dict[str, Any]:
        """
        Классифицирует намерение пользователя (для роутинга запросов)

        Args:
            message: Текст сообщения

        Returns:
            {
                "intent": "add_task" | "add_event" | "create_note" | "query" | "other",
                "confidence": 0.0-1.0,
                "entities": {...}
            }
        """
        system_prompt = """Ты - классификатор намерений. Определи намерение пользователя из списка:
- add_task: добавить задачу в список дел
- add_event: добавить событие в календарь
- create_note: создать заметку
- add_shopping: добавить товар в список покупок
- query: узнать информацию (календарь, задачи, заметки)
- other: другое

Ответь ТОЛЬКО в формате JSON:
{"intent": "add_task", "confidence": 0.95}"""

        prompt = f"Сообщение пользователя: {message}"

        try:
            response = self.generate(prompt, system=system_prompt, temperature=0.3, max_tokens=100)

            # Попытаться распарсить JSON
            result = json.loads(response)

            logger.info(f"Намерение классифицировано: {result}")
            return result

        except Exception as e:
            logger.warning(f"Ошибка классификации намерения: {e}")
            return {"intent": "other", "confidence": 0.0}


# Глобальный экземпляр (lazy init)
_ollama_instance = None


def get_ollama_client() -> Optional[OllamaClient]:
    """
    Получить глобальный экземпляр OllamaClient

    Returns:
        OllamaClient если включен и доступен, иначе None
    """
    global _ollama_instance

    if not OLLAMA_ENABLED:
        return None

    if _ollama_instance is None:
        _ollama_instance = OllamaClient()

        # Проверить доступность
        if not _ollama_instance.is_available():
            logger.warning("Ollama включен в конфиге, но сервер недоступен")
            return None

    return _ollama_instance


def is_ollama_available() -> bool:
    """Проверяет доступность Ollama"""
    client = get_ollama_client()
    return client is not None and client.is_available()
