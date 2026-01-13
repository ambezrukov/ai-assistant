"""
Route для получения TTS аудио файлов
"""

import os
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from utils.config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Загрузить конфигурацию
config = load_config()
TTS_CACHE_DIR = config.get('tts', {}).get('cache_dir', 'data/tts_cache')


@router.get(
    "/tts/{filename}",
    response_class=FileResponse,
    responses={
        404: {"description": "Audio file not found"},
        500: {"description": "Internal Server Error"}
    },
    summary="Получить TTS аудио файл",
    description="Возвращает озвученный аудио файл из кэша"
)
async def get_tts_file(filename: str) -> FileResponse:
    """
    Отдаёт аудио-файл с озвученным текстом

    Args:
        filename: Имя файла (md5_hash.mp3)

    Returns:
        Аудио файл
    """

    logger.debug(f"Запрос TTS файла: {filename}")

    # Проверить имя файла на безопасность
    if '..' in filename or '/' in filename or '\\' in filename:
        logger.warning(f"Попытка path traversal: {filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )

    # Проверить расширение
    if not filename.endswith('.mp3'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .mp3 files are supported"
        )

    # Полный путь к файлу
    file_path = os.path.join(TTS_CACHE_DIR, filename)

    # Проверить существование файла
    if not os.path.exists(file_path):
        logger.warning(f"TTS файл не найден: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )

    # Проверить, что это действительно файл
    if not os.path.isfile(file_path):
        logger.warning(f"Путь не является файлом: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )

    logger.info(f"Отдаём TTS файл: {filename}")

    # Вернуть файл с кэшированием
    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=filename,
        headers={
            "Cache-Control": "public, max-age=86400",  # Кэш на 24 часа
            "Accept-Ranges": "bytes"
        }
    )
