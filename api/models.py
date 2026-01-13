"""
Pydantic модели для API запросов и ответов
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


# Модели запросов

class TextCommandRequest(BaseModel):
    """Запрос на обработку текстовой команды"""
    text: str = Field(..., description="Текст команды", min_length=1)
    user_id: Optional[str] = Field(None, description="ID пользователя (опционально)")
    context_id: Optional[str] = Field(None, description="ID контекста разговора")


class ConfirmRequest(BaseModel):
    """Запрос на подтверждение действия"""
    confirmation_id: str = Field(..., description="ID подтверждения")
    confirmed: bool = Field(..., description="True - подтверждено, False - отклонено")
    user_id: Optional[str] = Field(None, description="ID пользователя (опционально)")


# Модели ответов

class CommandResponse(BaseModel):
    """Ответ на команду"""
    status: Literal["success", "error"] = Field(..., description="Статус выполнения")
    action: Literal["confirm", "executed"] = Field(..., description="Тип действия")
    confirmation_text: Optional[str] = Field(None, description="Текст для подтверждения")
    response_text: str = Field(..., description="Текст ответа пользователю")
    audio_url: Optional[str] = Field(None, description="URL озвученного ответа")
    confirmation_id: Optional[str] = Field(None, description="ID подтверждения")
    error: Optional[str] = Field(None, description="Текст ошибки")


class HealthResponse(BaseModel):
    """Ответ health check"""
    status: Literal["ok", "error"] = Field(..., description="Статус сервера")
    version: str = Field(..., description="Версия API")


class ErrorResponse(BaseModel):
    """Ответ с ошибкой"""
    status: Literal["error"] = "error"
    error: str = Field(..., description="Описание ошибки")
    detail: Optional[str] = Field(None, description="Детали ошибки")
