"""
Route для обработки текстовых команд
"""

from fastapi import APIRouter, Depends, HTTPException, status
from api.middleware.auth import verify_token
from api.models import TextCommandRequest, CommandResponse, ErrorResponse
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
    "/text-command",
    response_model=CommandResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Обработать текстовую команду",
    description="Принимает текстовую команду и обрабатывает её через Claude AI"
)
async def text_command(
    request: TextCommandRequest,
    token: str = Depends(verify_token)
) -> CommandResponse:
    """
    Обрабатывает текстовую команду от пользователя

    Args:
        request: Запрос с текстом команды
        token: Валидированный API токен

    Returns:
        Ответ с результатом обработки
    """

    user_id = request.user_id or "api_user"

    logger.info(f"Получена текстовая команда от {user_id}: {request.text}")

    try:
        # Сохранить сообщение пользователя в БД
        await db.save_message(
            user_id=user_id,
            role="user",
            content=request.text,
            session_id=request.context_id
        )

        # Получить историю разговора для контекста
        conversation_history = []
        if request.context_id:
            messages = await db.get_message_history(
                user_id=user_id,
                limit=5,
                session_id=request.context_id
            )
            conversation_history = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
            ]

        # Обработать через Claude Agent
        result = await agent.process_message(
            message=request.text,
            user_id=user_id,
            conversation_history=conversation_history
        )

        # Сохранить ответ ассистента в БД
        response_text = result.get('confirmation_text') or result.get('response_text', '')
        await db.save_message(
            user_id=user_id,
            role="assistant",
            content=response_text,
            session_id=request.context_id
        )

        # Сохранить статистику
        await db.save_usage_stats(
            user_id=user_id,
            interface="api_text",
            action_type=result.get('action_type', 'text_command'),
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

        logger.info(f"Команда обработана успешно (action: {result['action']})")
        return response

    except Exception as e:
        logger.error(f"Ошибка при обработке текстовой команды: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing command: {str(e)}"
        )
