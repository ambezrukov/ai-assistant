"""
Обработчик текстовых сообщений для Telegram бота
"""

import uuid
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Dict, Any

from utils.logger import get_logger
from utils.database import Database
from agent.claude_agent import ClaudeAgent

logger = get_logger(__name__)


class MessageHandlerBot:
    """Класс для обработки текстовых сообщений"""

    def __init__(self, config: Dict[str, Any], db: Database):
        """
        Инициализация обработчика

        Args:
            config: Конфигурация
            db: База данных
        """
        self.config = config
        self.db = db
        # Инициализация Claude Agent
        self.agent = ClaudeAgent(config)

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработка текстового сообщения

        Args:
            update: Telegram update
            context: Callback context
        """
        user_id = str(update.effective_user.id)
        message_text = update.message.text

        logger.info(f"Получено сообщение от {user_id}: {message_text}")

        # Показать индикатор "печатает..."
        await update.message.chat.send_action("typing")

        try:
            # Сохранить сообщение пользователя в БД
            await self.db.save_message(
                user_id=user_id,
                role="user",
                content=message_text
            )

            # TODO: Обработать через Claude Agent
            # На данный момент - заглушка
            response = await self._process_with_agent(message_text, user_id, context)

            # Сохранить ответ ассистента в БД
            await self.db.save_message(
                user_id=user_id,
                role="assistant",
                content=response.get('response_text', '')
            )

            # Если требуется подтверждение
            if response.get('action') == 'confirm':
                await self._send_confirmation(update, context, response)
            else:
                # Просто отправить ответ
                await update.message.reply_text(
                    response.get('response_text', 'Понял вас!')
                )

            # Сохранить статистику
            await self.db.save_usage_stats(
                user_id=user_id,
                interface="telegram",
                action_type=response.get('action_type', 'message'),
                tokens_used=response.get('tokens_used', 0)
            )

        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке вашего сообщения. "
                "Пожалуйста, попробуйте ещё раз."
            )

    async def _process_with_agent(
        self,
        message: str,
        user_id: str,
        context: ContextTypes.DEFAULT_TYPE
    ) -> Dict[str, Any]:
        """
        Обработать сообщение через Claude Agent

        Args:
            message: Текст сообщения
            user_id: ID пользователя
            context: Callback context

        Returns:
            Результат обработки
        """
        # Получить историю разговора для контекста
        history = await self.get_conversation_history(user_id, limit=5)

        # Преобразовать историю в формат для Claude
        conversation_history = []
        if history:
            for msg in await self.db.get_message_history(user_id, limit=5):
                conversation_history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Обработать через Claude Agent
        response = await self.agent.process_message(
            message=message,
            user_id=user_id,
            conversation_history=conversation_history
        )

        return response

    async def _send_confirmation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        response: Dict[str, Any]
    ):
        """
        Отправить запрос на подтверждение с кнопками

        Args:
            update: Telegram update
            context: Callback context
            response: Ответ от агента с данными подтверждения
        """
        confirmation_id = response['confirmation_id']
        confirmation_text = response['confirmation_text']

        # Сохранить данные подтверждения в БД
        await self.db.save_confirmation(
            confirmation_id=confirmation_id,
            user_id=str(update.effective_user.id),
            action_type=response.get('action_type', 'unknown'),
            action_data=json.dumps(response),
            confirmation_text=confirmation_text
        )

        # Создать кнопки
        keyboard = [
            [
                InlineKeyboardButton("✅ Да", callback_data=f"confirm_yes_{confirmation_id}"),
                InlineKeyboardButton("❌ Нет", callback_data=f"confirm_no_{confirmation_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправить сообщение с кнопками
        await update.message.reply_text(
            confirmation_text,
            reply_markup=reply_markup
        )

        logger.info(f"Отправлен запрос на подтверждение: {confirmation_id}")

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработка нажатий на кнопки подтверждения

        Args:
            update: Telegram update
            context: Callback context
        """
        query = update.callback_query
        await query.answer()  # Убрать "часики" с кнопки

        callback_data = query.data
        user_id = str(update.effective_user.id)

        logger.info(f"Callback от {user_id}: {callback_data}")

        try:
            # Парсим callback_data: confirm_yes_{id} или confirm_no_{id}
            parts = callback_data.split('_')
            if len(parts) < 3:
                await query.edit_message_text("❌ Неверные данные подтверждения")
                return

            action = parts[1]  # yes или no
            confirmation_id = '_'.join(parts[2:])  # ID может содержать underscore

            # Получить данные подтверждения из БД
            confirmation = await self.db.get_confirmation(confirmation_id)

            if not confirmation:
                await query.edit_message_text("❌ Подтверждение не найдено или истекло")
                return

            # Проверить, что это тот же пользователь
            if confirmation['user_id'] != user_id:
                await query.edit_message_text("❌ Это не ваше подтверждение")
                return

            # Проверить статус
            if confirmation['status'] != 'pending':
                await query.edit_message_text("❌ Это подтверждение уже обработано")
                return

            if action == "yes":
                # Подтверждено
                await self.db.update_confirmation_status(confirmation_id, 'confirmed')

                # Выполнить действие через Claude Agent
                result = await self.agent.execute_confirmed_action(confirmation, user_id)

                response_text = result.get('message', '✅ Действие выполнено')

                await query.edit_message_text(f"✅ Подтверждено!\n\n{response_text}")

                logger.info(f"Подтверждение {confirmation_id} выполнено")

            elif action == "no":
                # Отклонено
                await self.db.update_confirmation_status(confirmation_id, 'rejected')

                await query.edit_message_text("❌ Действие отменено")

                logger.info(f"Подтверждение {confirmation_id} отклонено")

            else:
                await query.edit_message_text("❌ Неизвестное действие")

        except Exception as e:
            logger.error(f"Ошибка при обработке callback: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Произошла ошибка при обработке вашего ответа"
            )

    async def get_conversation_history(self, user_id: str, limit: int = 5) -> str:
        """
        Получить историю разговора для контекста

        Args:
            user_id: ID пользователя
            limit: Максимальное количество сообщений

        Returns:
            Форматированная история разговора
        """
        messages = await self.db.get_message_history(user_id, limit=limit)

        if not messages:
            return ""

        history = []
        for msg in messages:
            role = "User" if msg['role'] == 'user' else "Assistant"
            history.append(f"{role}: {msg['content']}")

        return "\n".join(history)
