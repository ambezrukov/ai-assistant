"""
Интеграция с Whisper для распознавания речи
Поддерживает:
- OpenAI Whisper API (облачный)
- faster-whisper (локальный)
"""

import os
from typing import Optional
from openai import OpenAI
from utils.config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)

# Загрузить конфигурацию
config = load_config()
whisper_provider = config.get('whisper', {}).get('provider', 'openai')

# Инициализация OpenAI client (новый API)
client = OpenAI(api_key=config.get('openai', {}).get('api_key', ''))

# Инициализация faster-whisper (если выбран)
_faster_whisper_model = None

if whisper_provider == 'local':
    try:
        from faster_whisper import WhisperModel

        model_size = config.get('whisper', {}).get('model_size', 'base')
        device = config.get('whisper', {}).get('device', 'cpu')
        compute_type = config.get('whisper', {}).get('compute_type', 'int8')

        logger.info(f"Инициализация faster-whisper (модель: {model_size}, устройство: {device})")
        _faster_whisper_model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
        logger.info("faster-whisper инициализирован успешно")
    except ImportError:
        logger.warning("faster-whisper не установлен, используем OpenAI API")
        whisper_provider = 'openai'
    except Exception as e:
        logger.error(f"Ошибка при инициализации faster-whisper: {e}")
        whisper_provider = 'openai'


def _transcribe_with_faster_whisper(audio_file_path: str, language: str = "ru") -> str:
    """
    Распознаёт речь через локальный faster-whisper

    Args:
        audio_file_path: Путь к аудио-файлу
        language: Язык аудио

    Returns:
        Распознанный текст
    """
    if _faster_whisper_model is None:
        raise Exception("faster-whisper не инициализирован")

    logger.info(f"Распознавание через faster-whisper: {audio_file_path}")

    segments, info = _faster_whisper_model.transcribe(
        audio_file_path,
        language=language,
        beam_size=5,
        vad_filter=True  # Voice Activity Detection для лучшего качества
    )

    # Собрать текст из сегментов
    text = " ".join([segment.text.strip() for segment in segments])

    logger.info(f"Распознано (faster-whisper): {text}")
    return text


def _transcribe_with_openai(audio_file_path: str, language: str = "ru") -> str:
    """
    Распознаёт речь через OpenAI Whisper API

    Args:
        audio_file_path: Путь к аудио-файлу
        language: Язык аудио

    Returns:
        Распознанный текст
    """
    logger.info(f"Распознавание через OpenAI Whisper API: {audio_file_path}")

    with open(audio_file_path, "rb") as audio_file:
        # Вызов Whisper API (новый формат)
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language,
            response_format="text"
        )

    # Получить текст из ответа
    text = transcript.strip() if isinstance(transcript, str) else str(transcript).strip()

    logger.info(f"Распознано (OpenAI): {text}")
    return text


def transcribe_audio(audio_file_path: str, language: str = "ru") -> str:
    """
    Распознаёт речь в текст (автоматический выбор провайдера)

    Args:
        audio_file_path: Путь к аудио-файлу
        language: Язык аудио (по умолчанию русский)

    Returns:
        Распознанный текст

    Raises:
        Exception: При ошибке распознавания
    """
    global whisper_provider

    try:
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Аудио файл не найден: {audio_file_path}")

        # Выбор провайдера
        if whisper_provider == 'local':
            try:
                return _transcribe_with_faster_whisper(audio_file_path, language)
            except Exception as e:
                logger.warning(f"Ошибка faster-whisper, переключаемся на OpenAI API: {e}")
                whisper_provider = 'openai'
                return _transcribe_with_openai(audio_file_path, language)
        else:
            return _transcribe_with_openai(audio_file_path, language)

    except Exception as openai_err:
        if "openai" in str(type(openai_err).__module__):
            logger.error(f"Ошибка OpenAI Whisper API: {openai_err}", exc_info=True)
            raise Exception(f"Whisper API error: {str(openai_err)}")
        raise

    except FileNotFoundError as e:
        logger.error(str(e))
        raise Exception(str(e))

    except Exception as e:
        logger.error(f"Неожиданная ошибка при распознавании: {e}", exc_info=True)
        raise Exception(f"Transcription error: {str(e)}")


def transcribe_audio_with_prompt(
    audio_file_path: str,
    prompt: str = None,
    language: str = "ru"
) -> str:
    """
    Распознаёт речь с дополнительным промптом для улучшения точности

    Args:
        audio_file_path: Путь к аудио-файлу
        prompt: Подсказка для Whisper (например, специальные термины)
        language: Язык аудио

    Returns:
        Распознанный текст
    """

    logger.info(f"Распознавание с промптом: {audio_file_path}")

    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                prompt=prompt,
                response_format="text"
            )

        text = transcript.strip() if isinstance(transcript, str) else str(transcript).strip()

        logger.info(f"Распознано (с промптом): {text}")
        return text

    except Exception as e:
        logger.error(f"Ошибка при распознавании с промптом: {e}", exc_info=True)
        raise Exception(f"Transcription error: {str(e)}")


# Временная заглушка для тестирования без API ключа
def transcribe_audio_stub(audio_file_path: str) -> str:
    """
    Заглушка для тестирования без Whisper API

    Args:
        audio_file_path: Путь к аудио-файлу

    Returns:
        Тестовый текст
    """
    logger.warning("Используется заглушка Whisper API (тестовый режим)")
    return "Привет, Ассистент. Запиши на завтра в 15:00 встречу с врачом."
