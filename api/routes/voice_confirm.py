"""
Route для голосового подтверждения действий (через распознавание "Да"/"Нет")
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from api.middleware.auth import verify_token
from api.models import CommandResponse, ErrorResponse
from agent.claude_agent import ClaudeAgent
from utils.database import Database
from utils.config import load_config
from utils.logger import get_logger
from integrations.tts import get_or_create_tts_url
from integrations.whisper import transcribe_audio
import tempfile
import os

logger = get_logger(__name__)
router = APIRouter()

# Загрузить конфигурацию и инициализировать зависимости
config = load_config()
db = Database(config['database']['path'])
agent = ClaudeAgent(config)


@router.post(
    "/voice-confirm",
    response_model=CommandResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Confirmation not found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Голосовое подтверждение действия",
    description="Обрабатывает голосовое подтверждение (распознаёт 'Да'/'Нет' из аудио)"
)
async def voice_confirm_action(
    audio: UploadFile = File(..., description="Аудио файл с ответом (да/нет)"),
    confirmation_id: str = Form(..., description="ID подтверждения"),
    user_id: str = Form(None, description="ID пользователя"),
    token: str = Depends(verify_token)
) -> CommandResponse:
    """
    Обрабатывает голосовое подтверждение действия

    Распознаёт аудио через Whisper и определяет, согласен ли пользователь

    Args:
        audio: Аудио файл с ответом пользователя
        confirmation_id: ID подтверждения из БД
        user_id: ID пользователя
        token: Валидированный API токен

    Returns:
        Результат выполнения действия или отмены
    """

    user_id = user_id or "api_user"

    logger.info(f"Получено голосовое подтверждение от {user_id}: ID={confirmation_id}")

    temp_file_path = None

    try:
        # Сохранить аудио во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1]) as temp_file:
            content = await audio.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        logger.debug(f"Аудио сохранено: {temp_file_path}")

        # Распознать речь
        try:
            transcribed_text = transcribe_audio(temp_file_path, language="ru")
            logger.info(f"Распознанный текст: {transcribed_text}")
        except Exception as e:
            logger.error(f"Ошибка распознавания речи: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Speech recognition failed: {str(e)}"
            )

        # Определить намерение (Да или Нет)
        confirmed = _detect_confirmation_intent(transcribed_text)

        if confirmed is None:
            # Не удалось понять ответ
            logger.warning(f"Не удалось определить намерение: {transcribed_text}")

            response_text = "Извините, я не поняла ваш ответ. Скажите 'да' или 'нет'."
            audio_url = get_or_create_tts_url(response_text)

            return CommandResponse(
                status="needs_clarification",
                action="confirm",
                confirmation_text="Скажите 'да' для подтверждения или 'нет' для отмены",
                response_text=response_text,
                audio_url=audio_url,
                confirmation_id=confirmation_id
            )

        # Получить данные подтверждения из БД
        confirmation = await db.get_confirmation(confirmation_id)

        if not confirmation:
            logger.warning(f"Подтверждение не найдено: {confirmation_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Confirmation not found or expired"
            )

        # Проверить статус
        if confirmation['status'] != 'pending':
            logger.warning(f"Подтверждение уже обработано: {confirmation_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Confirmation already {confirmation['status']}"
            )

        if confirmed:
            # Пользователь подтвердил - выполнить действие
            await db.update_confirmation_status(confirmation_id, 'confirmed')

            result = await agent.execute_confirmed_action(confirmation, user_id)

            response_text = result.get('message', '✅ Действие выполнено')

            logger.info(f"Действие выполнено: {confirmation_id}")

            # Сгенерировать TTS URL
            audio_url = get_or_create_tts_url(response_text)

            return CommandResponse(
                status="success",
                action="executed",
                confirmation_text=None,
                response_text=response_text,
                audio_url=audio_url,
                confirmation_id=None
            )

        else:
            # Пользователь отклонил
            await db.update_confirmation_status(confirmation_id, 'rejected')

            logger.info(f"Действие отклонено: {confirmation_id}")

            response_text = "Хорошо, действие отменено"
            audio_url = get_or_create_tts_url(response_text)

            return CommandResponse(
                status="success",
                action="executed",
                confirmation_text=None,
                response_text=response_text,
                audio_url=audio_url,
                confirmation_id=None
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового подтверждения: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing voice confirmation: {str(e)}"
        )
    finally:
        # Удалить временный файл
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Временный файл удалён: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл: {e}")


def _detect_confirmation_intent(text: str) -> bool:
    """
    Определяет намерение пользователя по распознанному тексту

    Args:
        text: Распознанный текст

    Returns:
        True - если пользователь согласен
        False - если пользователь отказался
        None - если не удалось определить
    """
    text_lower = text.lower().strip()

    # Позитивные ответы
    positive_keywords = [
        'да', 'yes', 'ага', 'давай', 'конечно', 'согласен',
        'согласна', 'ок', 'окей', 'хорошо', 'верно', 'правильно',
        'подтверждаю', 'подтверждай', 'делай', 'сделай'
    ]

    # Негативные ответы
    negative_keywords = [
        'нет', 'no', 'неа', 'не надо', 'не нужно', 'отмена',
        'отмени', 'отменяй', 'не согласен', 'не согласна',
        'неправильно', 'неверно', 'ошибка', 'стоп'
    ]

    # Проверить позитивные
    for keyword in positive_keywords:
        if keyword in text_lower:
            logger.info(f"Обнаружено подтверждение: '{keyword}' в '{text}'")
            return True

    # Проверить негативные
    for keyword in negative_keywords:
        if keyword in text_lower:
            logger.info(f"Обнаружен отказ: '{keyword}' в '{text}'")
            return False

    # Не удалось определить
    logger.warning(f"Не удалось определить намерение в тексте: '{text}'")
    return None
