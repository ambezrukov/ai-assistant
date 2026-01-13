"""
Интеграция с gTTS (Google Text-to-Speech) для озвучивания текста
"""

import os
from gtts import gTTS
from utils.config import load_config
from utils.logger import get_logger
from utils.cache import TTSCache

logger = get_logger(__name__)

# Загрузить конфигурацию
config = load_config()
TTS_LANGUAGE = config.get('tts', {}).get('language', 'ru')
TTS_CACHE_DIR = config.get('tts', {}).get('cache_dir', 'data/tts_cache')
BASE_URL = config.get('api', {}).get('base_url', 'https://your-server.com')

# Инициализировать кэш
tts_cache = TTSCache(cache_dir=TTS_CACHE_DIR, base_url=BASE_URL)


def text_to_speech(text: str, output_path: str = None, language: str = None) -> str:
    """
    Конвертирует текст в аудио через gTTS

    Args:
        text: Текст для озвучивания
        output_path: Путь для сохранения MP3 (опционально)
        language: Язык озвучивания (по умолчанию из конфига)

    Returns:
        Путь к сохранённому файлу
    """

    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    language = language or TTS_LANGUAGE

    logger.info(f"Генерация TTS для текста: {text[:50]}...")

    try:
        # Если путь не указан, использовать кэш
        if not output_path:
            output_path = tts_cache.get_file_path(text)

        # Проверить, существует ли файл в кэше
        if os.path.exists(output_path):
            logger.info(f"TTS файл уже существует в кэше: {output_path}")
            return output_path

        # Создать директорию если не существует
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Генерация TTS
        tts = gTTS(text=text, lang=language, slow=False)
        tts.save(output_path)

        logger.info(f"TTS файл сгенерирован: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Ошибка при генерации TTS: {e}", exc_info=True)
        raise Exception(f"TTS generation error: {str(e)}")


def get_or_create_tts_url(text: str) -> str:
    """
    Получает URL для озвученного текста (создаёт файл если не существует)

    Args:
        text: Текст для озвучивания

    Returns:
        URL для скачивания аудио
    """

    if not text or not text.strip():
        logger.warning("Пустой текст для TTS, возвращаем None")
        return None

    try:
        # Проверить, существует ли файл в кэше
        if tts_cache.exists(text):
            logger.debug(f"TTS файл в кэше")
        else:
            # Создать TTS файл
            file_path = tts_cache.get_file_path(text)
            text_to_speech(text, file_path)
            logger.info(f"Создан новый TTS файл")

        # Вернуть URL
        url = tts_cache.get_url(text)
        logger.info(f"TTS URL: {url}")
        return url

    except Exception as e:
        logger.error(f"Ошибка при получении TTS URL: {e}", exc_info=True)
        return None


def cleanup_old_tts_files(days: int = None):
    """
    Удаляет старые TTS файлы из кэша

    Args:
        days: Удалить файлы старше N дней (по умолчанию из конфига)
    """

    if days is None:
        days = config.get('tts', {}).get('cache_days', 7)

    logger.info(f"Очистка TTS кэша (файлы старше {days} дней)")

    try:
        deleted_count = tts_cache.cleanup_old_files(days=days)
        logger.info(f"Очищено {deleted_count} старых TTS файлов")
        return deleted_count

    except Exception as e:
        logger.error(f"Ошибка при очистке TTS кэша: {e}", exc_info=True)
        return 0


def get_tts_cache_info() -> dict:
    """
    Получает информацию о TTS кэше

    Returns:
        Словарь с информацией о кэше
    """

    try:
        info = tts_cache.get_cache_info()
        logger.debug(f"TTS кэш: {info}")
        return info

    except Exception as e:
        logger.error(f"Ошибка при получении информации о кэше: {e}", exc_info=True)
        return {
            'files_count': 0,
            'total_size_bytes': 0,
            'total_size_mb': 0.0
        }
