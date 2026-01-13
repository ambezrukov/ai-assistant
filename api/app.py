"""
FastAPI приложение для REST API
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time

from api.routes import voice, text, confirm, tts, voice_confirm
from api.models import HealthResponse, ErrorResponse
from utils.logger import get_logger
from utils.database import Database
from utils.config import load_config

logger = get_logger(__name__)

# Загрузить конфигурацию
config = load_config()

# Создать FastAPI приложение
app = FastAPI(
    title="AI Assistant API",
    version="2.0.0",
    description="REST API для персонального AI-ассистента с голосовой активацией",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)


# Middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене ограничить конкретными доменами
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирует все HTTP запросы"""
    start_time = time.time()

    # Обработать запрос
    response = await call_next(request)

    # Вычислить время обработки
    process_time = time.time() - start_time

    # Логировать
    logger.info(
        f"{request.method} {request.url.path} "
        f"- Status: {response.status_code} "
        f"- Time: {process_time:.3f}s"
    )

    return response


# Обработчик ошибок валидации
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обрабатывает ошибки валидации Pydantic"""
    logger.warning(f"Ошибка валидации запроса: {exc.errors()}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "error": "Validation error",
            "detail": exc.errors()
        }
    )


# Глобальный обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Обрабатывает все необработанные исключения"""
    logger.error(f"Необработанное исключение: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


# Подключение роутов
app.include_router(voice.router, prefix="/api/v1", tags=["Voice Commands"])
app.include_router(text.router, prefix="/api/v1", tags=["Text Commands"])
app.include_router(confirm.router, prefix="/api/v1", tags=["Confirmations"])
app.include_router(voice_confirm.router, prefix="/api/v1", tags=["Voice Confirmations"])
app.include_router(tts.router, prefix="/api/v1", tags=["TTS"])


# Health check endpoint
@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Проверка работоспособности",
    description="Возвращает статус API сервера"
)
async def health_check() -> HealthResponse:
    """Проверка работоспособности сервера"""
    return HealthResponse(
        status="ok",
        version="2.0.0"
    )


# Root endpoint
@app.get(
    "/",
    tags=["System"],
    summary="Root endpoint",
    description="Информация об API"
)
async def root():
    """Корневой endpoint с информацией об API"""
    return {
        "name": "AI Assistant API",
        "version": "2.0.0",
        "description": "REST API для персонального AI-ассистента",
        "docs": "/api/docs",
        "health": "/api/v1/health"
    }


# Событие при запуске приложения
@app.on_event("startup")
async def startup_event():
    """Выполняется при запуске приложения"""
    logger.info("=" * 60)
    logger.info("🚀 Запуск REST API сервера")
    logger.info("=" * 60)

    # Инициализировать базу данных
    db = Database(config['database']['path'])
    await db.init_db()

    logger.info("✅ REST API сервер готов к работе")
    logger.info(f"📖 Документация: http://{config['api']['host']}:{config['api']['port']}/api/docs")
    logger.info("=" * 60)


# Событие при остановке приложения
@app.on_event("shutdown")
async def shutdown_event():
    """Выполняется при остановке приложения"""
    logger.info("=" * 60)
    logger.info("⏸️  Остановка REST API сервера")
    logger.info("=" * 60)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.app:app",
        host=config['api']['host'],
        port=config['api']['port'],
        reload=False,
        log_level="info"
    )
