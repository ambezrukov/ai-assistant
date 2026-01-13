"""
Telegram бот для AI-ассистента
"""

import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from typing import Dict, Any

from utils.config import load_config
from utils.logger import get_logger
from utils.database import Database
from bot.message_handler import MessageHandlerBot
from bot.voice_handler import VoiceHandlerBot

logger = get_logger(__name__)


class TelegramBot:
    """Основной класс Telegram бота"""

    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация бота

        Args:
            config: Конфигурация из config.yaml
        """
        self.config = config
        self.bot_token = config['telegram']['bot_token']
        self.allowed_users = config['telegram']['allowed_users']

        # База данных
        self.db = Database(config['database']['path'])

        # Обработчики
        self.message_handler = MessageHandlerBot(config, self.db)
        self.voice_handler = VoiceHandlerBot(config, self.db)

        # Application
        self.application = None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /start

        Args:
            update: Telegram update
            context: Callback context
        """
        user_id = update.effective_user.id

        # Проверка авторизации
        if user_id not in self.allowed_users:
            await update.message.reply_text(
                "❌ У вас нет доступа к этому боту."
            )
            logger.warning(f"Неавторизованная попытка доступа: {user_id}")
            return

        welcome_message = """
👋 Привет! Я ваш персональный AI-ассистент.

Я могу помочь вам с:
• 📅 Google Calendar (добавление и просмотр событий)
• ✅ Google Tasks (задачи и списки покупок)
• 📝 Obsidian (создание заметок)

Просто напишите мне естественным языком, что вам нужно!

Примеры команд:
• "Запиши на завтра в 15:00 встречу с врачом"
• "Что у меня на этой неделе?"
• "Добавь в покупки молоко и хлеб"
• "Создай заметку про новый проект"

Команды:
/help - Помощь
/stats - Статистика использования
/cancel - Отменить текущее действие

Вы также можете отправить голосовое сообщение!
"""

        await update.message.reply_text(welcome_message)
        logger.info(f"Пользователь {user_id} запустил бота")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /help

        Args:
            update: Telegram update
            context: Callback context
        """
        help_message = """
📖 Справка по AI-ассистенту

**Google Calendar:**
• "Запиши встречу на завтра в 15:00"
• "Что у меня в понедельник?"
• "Покажи события на следующую неделю"

**Google Tasks:**
• "Добавь задачу: купить продукты"
• "Покажи мои задачи"
• "Добавь в покупки молоко, хлеб, яйца"

**Obsidian:**
• "Создай заметку про книгу"
• "Запиши идею: новый проект"

**Голосовые команды:**
Отправьте голосовое сообщение - я распознаю речь и выполню команду.

**Подтверждения:**
Для важных действий (добавление событий, задач) я попрошу подтверждение.

**Команды:**
/start - Приветствие
/help - Эта справка
/stats - Статистика использования
/cancel - Отменить текущее действие
"""

        await update.message.reply_text(help_message, parse_mode='Markdown')

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /stats

        Args:
            update: Telegram update
            context: Callback context
        """
        user_id = str(update.effective_user.id)

        # Получить статистику за последние 30 дней
        stats = await self.db.get_usage_stats(user_id, days=30)

        if not stats:
            await update.message.reply_text(
                "📊 Статистика использования пока отсутствует."
            )
            return

        # Подсчитать статистику
        total_requests = len(stats)
        total_tokens = sum(s.get('tokens_used', 0) for s in stats)

        # Подсчитать по типам действий
        action_counts = {}
        for stat in stats:
            action_type = stat.get('action_type', 'unknown')
            action_counts[action_type] = action_counts.get(action_type, 0) + 1

        stats_message = f"""
📊 **Статистика использования (30 дней)**

Всего запросов: {total_requests}
Использовано токенов: {total_tokens:,}

**По типам действий:**
"""

        for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
            stats_message += f"• {action}: {count}\n"

        await update.message.reply_text(stats_message, parse_mode='Markdown')

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработчик команды /cancel

        Args:
            update: Telegram update
            context: Callback context
        """
        # Очистить контекст пользователя
        context.user_data.clear()

        await update.message.reply_text(
            "❌ Текущее действие отменено."
        )

    async def check_authorization(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Проверка авторизации пользователя

        Args:
            update: Telegram update
            context: Callback context

        Returns:
            True если пользователь авторизован, иначе False
        """
        user_id = update.effective_user.id

        if user_id not in self.allowed_users:
            await update.message.reply_text(
                "❌ У вас нет доступа к этому боту."
            )
            logger.warning(f"Неавторизованная попытка доступа: {user_id}")
            return False

        return True

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Глобальный обработчик ошибок

        Args:
            update: Telegram update
            context: Callback context
        """
        logger.error(f"Ошибка при обработке update: {context.error}", exc_info=context.error)

        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка при обработке вашего запроса. "
                "Пожалуйста, попробуйте ещё раз или обратитесь к администратору."
            )

    def setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""

        # Команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("cancel", self.cancel_command))

        # Обработчик текстовых сообщений
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.message_handler.handle_text_message
            )
        )

        # Обработчик голосовых сообщений
        self.application.add_handler(
            MessageHandler(
                filters.VOICE,
                self.voice_handler.handle_voice_message
            )
        )

        # Обработчик callback запросов (для кнопок подтверждения)
        self.application.add_handler(
            CallbackQueryHandler(self.message_handler.handle_callback_query)
        )

        # Глобальный обработчик ошибок
        self.application.add_error_handler(self.error_handler)

        logger.info("Обработчики команд настроены")

    async def post_init(self, application: Application):
        """
        Действия после инициализации бота

        Args:
            application: Telegram Application
        """
        # Инициализация базы данных
        await self.db.init_db()
        logger.info("База данных инициализирована")

        # Установить команды бота в меню
        await application.bot.set_my_commands([
            ("start", "Начать работу с ботом"),
            ("help", "Показать справку"),
            ("stats", "Статистика использования"),
            ("cancel", "Отменить текущее действие")
        ])

        logger.info("Telegram бот готов к работе")

    async def start(self):
        """Запуск бота"""

        # Создать Application
        self.application = (
            Application.builder()
            .token(self.bot_token)
            .post_init(self.post_init)
            .build()
        )

        # Настроить обработчики
        self.setup_handlers()

        # Запустить бота
        logger.info("Запуск Telegram бота...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

        logger.info("✅ Telegram бот запущен")

        # Держать бота запущенным
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Остановка Telegram бота...")
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram бот остановлен")


async def main():
    """Точка входа для тестирования бота"""
    config = load_config()
    bot = TelegramBot(config)
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
