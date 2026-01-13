"""
Модуль загрузки конфигурации
"""

import yaml
import os
from typing import Dict, Any
from dotenv import load_dotenv


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Загружает конфигурацию из YAML файла и переменных окружения

    Args:
        config_path: Путь к файлу конфигурации

    Returns:
        Словарь с конфигурацией

    Raises:
        FileNotFoundError: Если файл конфигурации не найден
        yaml.YAMLError: Если файл конфигурации содержит ошибки
    """

    # Загрузить переменные окружения из .env файла
    load_dotenv()

    # Проверить наличие файла конфигурации
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Файл конфигурации {config_path} не найден. "
            f"Скопируйте config.yaml.example в config.yaml и заполните настройки."
        )

    # Загрузить YAML
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Переопределить значения из переменных окружения (если есть)
    # Приоритет: переменные окружения > config.yaml

    # Telegram
    if os.getenv('TELEGRAM_BOT_TOKEN'):
        config['telegram']['bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN')

    # API
    if os.getenv('API_TOKEN'):
        config['api']['token'] = os.getenv('API_TOKEN')

    # Claude
    if os.getenv('CLAUDE_API_KEY'):
        config['claude']['api_key'] = os.getenv('CLAUDE_API_KEY')

    # OpenAI
    if os.getenv('OPENAI_API_KEY'):
        config['openai']['api_key'] = os.getenv('OPENAI_API_KEY')

    # Google Cloud (опционально)
    if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    # Валидация обязательных полей
    _validate_config(config)

    return config


def _validate_config(config: Dict[str, Any]) -> None:
    """
    Проверяет наличие обязательных полей в конфигурации

    Args:
        config: Словарь с конфигурацией

    Raises:
        ValueError: Если отсутствуют обязательные поля
    """

    required_fields = [
        ('telegram', 'bot_token'),
        ('api', 'token'),
        ('claude', 'api_key'),
        ('openai', 'api_key'),
    ]

    missing_fields = []

    for section, field in required_fields:
        if section not in config:
            missing_fields.append(f"{section}.{field}")
        elif field not in config[section]:
            missing_fields.append(f"{section}.{field}")
        elif not config[section][field] or config[section][field].startswith('YOUR_'):
            missing_fields.append(f"{section}.{field}")

    if missing_fields:
        raise ValueError(
            f"Отсутствуют или не заполнены обязательные поля в конфигурации:\n"
            f"{', '.join(missing_fields)}\n\n"
            f"Пожалуйста, заполните их в config.yaml или .env файле."
        )


def get_config_value(config: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Безопасно получает значение из вложенного словаря конфигурации

    Args:
        config: Словарь с конфигурацией
        *keys: Путь к значению (например, 'google', 'calendar', 'token_file')
        default: Значение по умолчанию, если ключ не найден

    Returns:
        Значение из конфигурации или default

    Example:
        >>> config = {'google': {'calendar': {'token_file': 'token.json'}}}
        >>> get_config_value(config, 'google', 'calendar', 'token_file')
        'token.json'
    """

    result = config

    for key in keys:
        if isinstance(result, dict) and key in result:
            result = result[key]
        else:
            return default

    return result
