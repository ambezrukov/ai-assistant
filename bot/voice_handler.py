"""
Обработчик голосовых сообщений для Telegram бота
"""

import os
import uuid
from telegram import Update
from telegram.ext import ContextTypes
from typing import Dict, Any

from utils.logger import get_logger
from utils.database import Database

logger = get_logger(__name__)


class VoiceHandlerBot:
    """Класс для обработки голосовых сообщений"""

    def __init__(self, config: Dict[str, Any], db: Database):
        """
        Инициализация обработчика

        Args:
            config: Конфигурация
            db: База данных
        """
        self.config = config
        self.db = db
        self.temp_dir = "data/temp"
        self._ensure_temp_directory()

    def _ensure_temp_directory(self):
        """Создает директорию для временных файлов"""
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir, exist_ok=True)
            logger.info(f"Создана директория для временных файлов: {self.temp_dir}")

    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработка голосового сообщения

        Args:
            update: Telegram update
            context: Callback context
        """
        user_id = str(update.effective_user.id)

        logger.info(f"Получено голосовое сообщение от {user_id}")

        # Показать индикатор "записывает голосовое..."
        await update.message.chat.send_action("record_voice")

        try:
            # 1. Скачать голосовое сообщение
            voice_file = await update.message.voice.get_file()

            # Создать уникальное имя файла
            temp_filename = f"{uuid.uuid4()}.ogg"
            temp_filepath = os.path.join(self.temp_dir, temp_filename)

            # Скачать файл
            await voice_file.download_to_drive(temp_filepath)
            logger.info(f"Голосовое сообщение сохранено: {temp_filepath}")

            # Показать индикатор "печатает..."
            await update.message.chat.send_action("typing")

            # 2. Распознать речь через Whisper API
            transcribed_text = await self._transcribe_audio(temp_filepath)

            if not transcribed_text:
                await update.message.reply_text(
                    "❌ Не удалось распознать речь. Пожалуйста, попробуйте ещё раз."
                )
                return

            logger.info(f"Распознанный текст: {transcribed_text}")

            # Отправить распознанный текст пользователю
            await update.message.reply_text(
                f"🎤 Вы сказали: _{transcribed_text}_",
                parse_mode='Markdown'
            )

            # 3. Обработать как текстовое сообщение
            # Сохранить в БД
            await self.db.save_message(
                user_id=user_id,
                role="user",
                content=transcribed_text
            )

            # TODO: Обработать через Claude Agent
            response = await self._process_with_agent(transcribed_text, user_id)

            # Сохранить ответ в БД
            await self.db.save_message(
                user_id=user_id,
                role="assistant",
                content=response.get('response_text', '')
            )

            # Отправить ответ
            await update.message.reply_text(
                response.get('response_text', 'Понял вас!')
            )

            # Сохранить статистику
            await self.db.save_usage_stats(
                user_id=user_id,
                interface="telegram_voice",
                action_type=response.get('action_type', 'voice_message'),
                tokens_used=response.get('tokens_used', 0)
            )

        except Exception as e:
            logger.error(f"Ошибка при обработке голосового сообщения: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке голосового сообщения. "
                "Пожалуйста, попробуйте ещё раз."
            )

        finally:
            # Удалить временный файл
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                    logger.debug(f"Удален временный файл: {temp_filepath}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл: {e}")

    async def _transcribe_audio(self, audio_filepath: str) -> str:
        """
        Распознать аудио в текст через Whisper API

        Args:
            audio_filepath: Путь к аудио-файлу

        Returns:
            Распознанный текст
        """
        try:
            from integrations.whisper import transcribe_audio

            # Распознать через Whisper API
            text = transcribe_audio(audio_filepath, language="ru")
            return text

        except Exception as e:
            logger.error(f"Ошибка при распознавании аудио: {e}", exc_info=True)
            return ""

    async def _process_with_agent(
        self,
        message: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Обработать сообщение через Claude Agent

        Args:
            message: Текст сообщения
            user_id: ID пользователя

        Returns:
            Результат обработки
        """
        # TODO: Интеграция с Claude Agent будет реализована на этапе 3
        # Пока возвращаем заглушку

        return {
            'action': 'executed',
            'action_type': 'voice_general',
            'response_text': f'Получил ваше голосовое сообщение.\n\n'
                             f'(Интеграция с Claude Agent и Whisper будет реализована на следующих этапах)',
            'tokens_used': 100
        }

    async def cleanup_old_temp_files(self, hours: int = 24):
        """
        Очистить старые временные файлы

        Args:
            hours: Удалить файлы старше N часов
        """
        import time

        if not os.path.exists(self.temp_dir):
            return

        current_time = time.time()
        max_age = hours * 3600  # Часы в секунды
        deleted_count = 0

        for filename in os.listdir(self.temp_dir):
            filepath = os.path.join(self.temp_dir, filename)

            if not os.path.isfile(filepath):
                continue

            try:
                file_age = current_time - os.path.getmtime(filepath)

                if file_age > max_age:
                    os.remove(filepath)
                    deleted_count += 1
                    logger.debug(f"Удален старый временный файл: {filename}")

            except Exception as e:
                logger.warning(f"Ошибка при удалении файла {filename}: {e}")

        if deleted_count > 0:
            logger.info(f"Очищено {deleted_count} старых временных файлов")
