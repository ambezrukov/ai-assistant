"""
Middleware для авторизации API запросов
"""

from fastapi import Header, HTTPException, status
from utils.config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)

# Загрузить конфигурацию один раз при импорте
try:
    config = load_config()
    API_TOKEN = config['api']['token']
except Exception as e:
    logger.error(f"Ошибка при загрузке конфигурации в auth middleware: {e}")
    API_TOKEN = None


async def verify_token(authorization: str = Header(...)) -> str:
    """
    Проверяет Bearer токен в заголовке Authorization

    Args:
        authorization: Заголовок Authorization (формат: "Bearer YOUR_TOKEN")

    Returns:
        Токен если валиден

    Raises:
        HTTPException: Если токен невалиден или отсутствует
    """

    if not API_TOKEN:
        logger.error("API токен не настроен в конфигурации")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error"
        )

    # Проверить формат заголовка
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning(f"Неверный формат заголовка Authorization: {authorization}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: 'Bearer YOUR_TOKEN'",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Извлечь токен
    token = authorization.replace("Bearer ", "").strip()

    # Проверить токен
    if token != API_TOKEN:
        logger.warning(f"Неверный API токен: {token[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    logger.debug("API токен валиден")
    return token
