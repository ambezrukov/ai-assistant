"""
Модуль кэширования TTS файлов
"""

import os
import time
import hashlib
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class TTSCache:
    """Класс для управления кэшем TTS файлов"""

    def __init__(self, cache_dir: str = "data/tts_cache", base_url: str = "https://your-server.com"):
        """
        Инициализация кэша

        Args:
            cache_dir: Директория для хранения кэшированных файлов
            base_url: Базовый URL сервера для генерации ссылок
        """
        self.cache_dir = cache_dir
        self.base_url = base_url.rstrip('/')
        self._ensure_cache_directory()

    def _ensure_cache_directory(self):
        """Создает директорию для кэша, если не существует"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"Создана директория для TTS кэша: {self.cache_dir}")

    def get_filename(self, text: str) -> str:
        """
        Генерирует имя файла на основе хэша текста

        Args:
            text: Текст для озвучивания

        Returns:
            Имя файла (например, "abc123.mp3")
        """
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"{text_hash}.mp3"

    def get_file_path(self, text: str) -> str:
        """
        Получает полный путь к файлу в кэше

        Args:
            text: Текст для озвучивания

        Returns:
            Полный путь к файлу
        """
        filename = self.get_filename(text)
        return os.path.join(self.cache_dir, filename)

    def exists(self, text: str) -> bool:
        """
        Проверяет, существует ли файл в кэше

        Args:
            text: Текст для озвучивания

        Returns:
            True если файл существует, иначе False
        """
        file_path = self.get_file_path(text)
        return os.path.exists(file_path)

    def get_url(self, text: str) -> str:
        """
        Получает URL для скачивания аудио-файла

        Args:
            text: Текст для озвучивания

        Returns:
            URL файла
        """
        filename = self.get_filename(text)
        return f"{self.base_url}/api/v1/tts/{filename}"

    def save(self, text: str, file_path: str) -> str:
        """
        Сохраняет файл в кэш (копирует из временного файла)

        Args:
            text: Текст для озвучивания
            file_path: Путь к временному файлу

        Returns:
            Путь к сохранённому файлу в кэше
        """
        cache_path = self.get_file_path(text)

        # Если файл уже существует, не копируем
        if os.path.exists(cache_path):
            logger.debug(f"TTS файл уже в кэше: {cache_path}")
            return cache_path

        # Копировать файл в кэш
        import shutil
        shutil.copy2(file_path, cache_path)
        logger.info(f"TTS файл сохранён в кэш: {cache_path}")

        return cache_path

    def cleanup_old_files(self, days: int = 7) -> int:
        """
        Удаляет файлы старше указанного количества дней

        Args:
            days: Удалить файлы старше N дней

        Returns:
            Количество удалённых файлов
        """
        if not os.path.exists(self.cache_dir):
            return 0

        current_time = time.time()
        max_age = days * 86400  # Дни в секунды
        deleted_count = 0

        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.mp3'):
                continue

            file_path = os.path.join(self.cache_dir, filename)

            try:
                file_age = current_time - os.path.getmtime(file_path)

                if file_age > max_age:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.debug(f"Удалён старый TTS файл: {filename}")

            except Exception as e:
                logger.error(f"Ошибка при удалении файла {filename}: {e}")

        if deleted_count > 0:
            logger.info(f"Очищено {deleted_count} старых TTS файлов")

        return deleted_count

    def get_cache_size(self) -> int:
        """
        Получает размер кэша в байтах

        Returns:
            Размер кэша
        """
        if not os.path.exists(self.cache_dir):
            return 0

        total_size = 0

        for filename in os.listdir(self.cache_dir):
            file_path = os.path.join(self.cache_dir, filename)
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)

        return total_size

    def get_cache_info(self) -> dict:
        """
        Получает информацию о кэше

        Returns:
            Словарь с информацией о кэше
        """
        if not os.path.exists(self.cache_dir):
            return {
                'files_count': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0.0
            }

        files = [f for f in os.listdir(self.cache_dir) if f.endswith('.mp3')]
        total_size = self.get_cache_size()

        return {
            'files_count': len(files),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }


def get_or_create_tts(text: str, base_url: str, cache_dir: str = "data/tts_cache") -> str:
    """
    Вспомогательная функция для получения URL TTS файла
    (создаёт файл, если не существует)

    Args:
        text: Текст для озвучивания
        base_url: Базовый URL сервера
        cache_dir: Директория кэша

    Returns:
        URL для скачивания аудио
    """
    cache = TTSCache(cache_dir, base_url)
    return cache.get_url(text)
