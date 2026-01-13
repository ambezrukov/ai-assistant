"""
Route для обработки голосовых команд
"""

import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from api.middleware.auth import verify_token
from api.models import CommandResponse, ErrorResponse
from agent.claude_agent import ClaudeAgent
from utils.database import Database
from utils.config import load_config
from utils.logger import get_logger
from integrations.whisper import transcribe_audio
from integrations.tts import get_or_create_tts_url

logger = get_logger(__name__)
router = APIRouter()

# Загрузить конфигурацию и инициализировать зависимости
config = load_config()
db = Database(config['database']['path'])
agent = ClaudeAgent(config)

# Временная директория для аудио файлов
TEMP_DIR = "data/temp"
os.makedirs(TEMP_DIR, exist_ok=True)


@router.post(
    "/voice-command",
    response_model=CommandResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Обработать голосовую команду",
    description="Принимает аудио файл, распознаёт речь через Whisper и обрабатывает команду"
)
async def voice_command(
    audio: UploadFile = File(..., description="Аудио файл (.ogg, .mp3, .wav, .m4a)"),
    token: str = Depends(verify_token)
) -> CommandResponse:
    """
    Обрабатывает голосовую команду от пользователя

    Args:
        audio: Аудио файл с командой
        token: Валидированный API токен

    Returns:
        Ответ с результатом обработки
    """

    user_id = "api_user"
    temp_filepath = None

    logger.info(f"Получена голосовая команда от {user_id}")

    try:
        # Проверить расширение файла
        filename = audio.filename or "audio.ogg"
        file_ext = os.path.splitext(filename)[1].lower()

        allowed_extensions = ['.ogg', '.mp3', '.wav', '.m4a', '.opus']
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported audio format. Allowed: {', '.join(allowed_extensions)}"
            )

        # Сохранить временный файл
        temp_filename = f"{uuid.uuid4()}{file_ext}"
        temp_filepath = os.path.join(TEMP_DIR, temp_filename)

        with open(temp_filepath, "wb") as f:
            content = await audio.read()
            f.write(content)

        logger.info(f"Аудио файл сохранён: {temp_filepath} ({len(content)} bytes)")

        # Распознать речь через Whisper API
        transcribed_text = transcribe_audio(temp_filepath, language="ru")

        if not transcribed_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not transcribe audio. Please try again."
            )

        logger.info(f"Распознанный текст: {transcribed_text}")

        # Сохранить сообщение в БД
        await db.save_message(
            user_id=user_id,
            role="user",
            content=transcribed_text
        )

        # Обработать через Claude Agent
        result = await agent.process_message(
            message=transcribed_text,
            user_id=user_id,
            conversation_history=[]
        )

        # Сохранить ответ в БД
        response_text = result.get('confirmation_text') or result.get('response_text', '')
        await db.save_message(
            user_id=user_id,
            role="assistant",
            content=response_text
        )

        # Сохранить статистику
        await db.save_usage_stats(
            user_id=user_id,
            interface="api_voice",
            action_type=result.get('action_type', 'voice_command'),
            tokens_used=result.get('tokens_used', 0)
        )

        # Сгенерировать TTS URL
        tts_text = result.get('confirmation_text') or result.get('response_text', '')
        audio_url = get_or_create_tts_url(tts_text) if tts_text else None

        # Сформировать ответ
        response = CommandResponse(
            status="success",
            action=result['action'],
            confirmation_text=result.get('confirmation_text'),
            response_text=result.get('response_text', ''),
            audio_url=audio_url,
            confirmation_id=result.get('confirmation_id')
        )

        logger.info(f"Голосовая команда обработана успешно")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обработке голосовой команды: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing voice command: {str(e)}"
        )

    finally:
        # Удалить временный файл
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
                logger.debug(f"Удалён временный файл: {temp_filepath}")
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл: {e}")
