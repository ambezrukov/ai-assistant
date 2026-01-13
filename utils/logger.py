"""
Модуль настройки логирования для AI-ассистента
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
import yaml


def setup_logger(name: str = "ai_assistant", config_path: str = "config.yaml") -> logging.Logger:
    """
    Настраивает и возвращает logger с конфигурацией из config.yaml

    Args:
        name: Имя logger'а
        config_path: Путь к файлу конфигурации

    Returns:
        Настроенный logger
    """

    # Загрузить конфигурацию
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            log_config = config.get('logging', {})
    except FileNotFoundError:
        # Если конфиг не найден, использовать значения по умолчанию
        log_config = {
            'level': 'INFO',
            'file': 'logs/assistant.log',
            'max_bytes': 10485760,
            'backup_count': 5,
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }

    # Создать logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_config.get('level', 'INFO')))

    # Очистить существующие handlers
    logger.handlers.clear()

    # Создать папку для логов, если не существует
    log_file = log_config.get('file', 'logs/assistant.log')
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Форматтер для файла (JSON)
    json_formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Форматтер для консоли (обычный текст)
    console_formatter = logging.Formatter(
        fmt=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler для файла (с ротацией)
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=log_config.get('max_bytes', 10485760),  # 10 MB по умолчанию
        backupCount=log_config.get('backup_count', 5),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(json_formatter)

    # Handler для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Добавить handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "ai_assistant") -> logging.Logger:
    """
    Получить существующий logger или создать новый

    Args:
        name: Имя logger'а

    Returns:
        Logger
    """
    logger = logging.getLogger(name)

    # Если logger ещё не настроен, настроить его
    if not logger.handlers:
        return setup_logger(name)

    return logger
