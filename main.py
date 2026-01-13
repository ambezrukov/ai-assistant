"""
Главный файл для запуска AI-ассистента
Запускает Telegram бота и REST API сервер параллельно
"""

import asyncio
import multiprocessing
import sys
from utils.config import load_config
from utils.logger import setup_logger

logger = setup_logger()


def run_telegram_bot():
    """Запускает Telegram бота в отдельном процессе"""
    try:
        from bot.telegram_bot import TelegramBot

        config = load_config()
        bot = TelegramBot(config)

        # Запустить бота
        asyncio.run(bot.start())

    except KeyboardInterrupt:
        logger.info("Telegram бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка в Telegram боте: {e}", exc_info=True)
        sys.exit(1)


def run_api_server():
    """Запускает REST API сервер в отдельном процессе"""
    try:
        import uvicorn
        from utils.config import load_config

        config = load_config()

        # Запустить API сервер
        uvicorn.run(
            "api.app:app",
            host=config['api']['host'],
            port=config['api']['port'],
            reload=False,
            log_level="info",
            access_log=True
        )

    except KeyboardInterrupt:
        logger.info("API сервер остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка в API сервере: {e}", exc_info=True)
        sys.exit(1)


def main():
    """
    Главная функция - запускает оба сервиса параллельно
    """

    # Загрузить конфигурацию для проверки
    try:
        config = load_config()
        logger.info("Конфигурация загружена успешно")
    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Ошибка при загрузке конфигурации: {e}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("🚀 Запуск AI-ассистента v2.0")
    logger.info("=" * 60)

    # Создать процессы для обоих сервисов
    telegram_process = multiprocessing.Process(
        target=run_telegram_bot,
        name="TelegramBot"
    )

    api_process = multiprocessing.Process(
        target=run_api_server,
        name="APIServer"
    )

    try:
        # Запустить процессы
        logger.info("Запуск Telegram бота...")
        telegram_process.start()

        logger.info("Запуск REST API сервера...")
        api_process.start()

        logger.info("=" * 60)
        logger.info("✅ Все сервисы запущены")
        logger.info(f"📱 Telegram бот: работает (PID: {telegram_process.pid})")
        logger.info(f"🌐 REST API: http://{config['api']['host']}:{config['api']['port']}")
        logger.info("=" * 60)
        logger.info("Нажмите Ctrl+C для остановки")
        logger.info("=" * 60)

        # Ждать завершения процессов
        telegram_process.join()
        api_process.join()

    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("⏸️  Получен сигнал остановки...")
        logger.info("=" * 60)

        # Остановить процессы
        if telegram_process.is_alive():
            logger.info("Остановка Telegram бота...")
            telegram_process.terminate()
            telegram_process.join(timeout=10)

        if api_process.is_alive():
            logger.info("Остановка REST API сервера...")
            api_process.terminate()
            api_process.join(timeout=10)

        logger.info("=" * 60)
        logger.info("✅ Все сервисы остановлены")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)

        # Принудительно остановить процессы
        if telegram_process.is_alive():
            telegram_process.kill()
        if api_process.is_alive():
            api_process.kill()

        sys.exit(1)


if __name__ == "__main__":
    # Для Windows требуется freeze_support
    if sys.platform.startswith('win'):
        multiprocessing.freeze_support()

    main()
