"""
Route для подтверждения действий
"""

from fastapi import APIRouter, Depends, HTTPException, status
from api.middleware.auth import verify_token
from api.models import ConfirmRequest, CommandResponse, ErrorResponse
from agent.claude_agent import ClaudeAgent
from utils.database import Database
from utils.config import load_config
from utils.logger import get_logger
from integrations.tts import get_or_create_tts_url

logger = get_logger(__name__)
router = APIRouter()

# Загрузить конфигурацию и инициализировать зависимости
config = load_config()
db = Database(config['database']['path'])
agent = ClaudeAgent(config)


@router.post(
    "/confirm",
    response_model=CommandResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Confirmation not found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Подтвердить или отклонить действие",
    description="Обрабатывает подтверждение действия пользователем (Да/Нет)"
)
async def confirm_action(
    request: ConfirmRequest,
    token: str = Depends(verify_token)
) -> CommandResponse:
    """
    Обрабатывает подтверждение действия

    Args:
        request: Запрос с ID подтверждения и ответом
        token: Валидированный API токен

    Returns:
        Результат выполнения действия или отмены
    """

    user_id = request.user_id or "api_user"

    logger.info(
        f"Получено подтверждение от {user_id}: "
        f"ID={request.confirmation_id}, confirmed={request.confirmed}"
    )

    try:
        # Получить данные подтверждения из БД
        confirmation = await db.get_confirmation(request.confirmation_id)

        if not confirmation:
            logger.warning(f"Подтверждение не найдено: {request.confirmation_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Confirmation not found or expired"
            )

        # Проверить статус
        if confirmation['status'] != 'pending':
            logger.warning(f"Подтверждение уже обработано: {request.confirmation_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Confirmation already {confirmation['status']}"
            )

        if request.confirmed:
            # Пользователь подтвердил - выполнить действие
            await db.update_confirmation_status(request.confirmation_id, 'confirmed')

            result = await agent.execute_confirmed_action(confirmation, user_id)

            response_text = result.get('message', '✅ Действие выполнено')

            logger.info(f"Действие выполнено: {request.confirmation_id}")

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
            await db.update_confirmation_status(request.confirmation_id, 'rejected')

            logger.info(f"Действие отклонено: {request.confirmation_id}")

            response_text = "❌ Действие отменено"
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
        logger.error(f"Ошибка при обработке подтверждения: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing confirmation: {str(e)}"
        )
