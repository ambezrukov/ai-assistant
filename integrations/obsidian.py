"""
Интеграция с Obsidian
Поддерживает:
- filesystem (прямой доступ к файлам)
- rest_api (Obsidian Local REST API плагин)
"""

import os
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from utils.config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)

# Отложенный импорт Git синхронизации для избежания циклических зависимостей
_git_sync = None

def _get_git_sync():
    """Ленивая загрузка Git синхронизации"""
    global _git_sync
    if _git_sync is None:
        try:
            from integrations.obsidian_git import get_git_sync
            _git_sync = get_git_sync()
        except Exception as e:
            logger.warning(f"Git синхронизация недоступна: {e}")
            _git_sync = False  # Флаг, что пытались загрузить
    return _git_sync if _git_sync is not False else None

# Загрузить конфигурацию
config = load_config()
VAULT_PATH = config['obsidian'].get('vault_path', '')
NOTES_FOLDER = config['obsidian'].get('notes_folder', 'Notes')
METHOD = config['obsidian'].get('method', 'filesystem')
REST_API_URL = config['obsidian'].get('rest_api_url', 'http://localhost:27123')
REST_API_KEY = config['obsidian'].get('rest_api_key', '')


class ObsidianRESTAPI:
    """Класс для работы с Obsidian через Local REST API плагин"""

    def __init__(self, api_url: str = None, api_key: str = None):
        """
        Инициализация Obsidian REST API клиента

        Args:
            api_url: URL Obsidian REST API
            api_key: API ключ
        """
        self.api_url = api_url or REST_API_URL
        self.api_key = api_key or REST_API_KEY
        self.notes_folder = NOTES_FOLDER
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        logger.info(f"Obsidian REST API клиент инициализирован (URL: {self.api_url})")

    def create_note(
        self,
        title: str,
        content: str,
        tags: List[str] = None,
        folder: str = None
    ) -> Dict[str, Any]:
        """Создаёт заметку через REST API"""
        folder = folder or self.notes_folder

        try:
            # Подготовить содержимое с frontmatter
            full_content = self._prepare_content(title, content, tags)

            # Безопасное имя файла
            safe_filename = self._sanitize_filename(title)
            file_path = f"{folder}/{safe_filename}.md"

            # Отправить запрос
            response = requests.put(
                f"{self.api_url}/vault/{file_path}",
                headers=self.headers,
                data=full_content.encode('utf-8'),
                timeout=10
            )

            response.raise_for_status()

            logger.info(f"Заметка создана через REST API: {file_path}")

            return {
                'success': True,
                'title': title,
                'file_path': file_path,
                'relative_path': file_path
            }

        except Exception as e:
            logger.error(f"Ошибка при создании заметки через REST API: {e}", exc_info=True)
            raise Exception(f"Failed to create note: {str(e)}")

    def search_notes(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Ищет заметки через REST API"""
        try:
            response = requests.post(
                f"{self.api_url}/search/simple",
                headers=self.headers,
                json={'query': query},
                timeout=10
            )

            response.raise_for_status()
            results = response.json()

            # Форматировать результаты
            formatted_results = []
            for item in results[:limit]:
                formatted_results.append({
                    'title': item.get('filename', '').replace('.md', ''),
                    'file_path': item.get('filename', ''),
                    'relative_path': item.get('filename', ''),
                    'excerpt': item.get('excerpt', '')
                })

            logger.info(f"Найдено {len(formatted_results)} заметок через REST API")
            return formatted_results

        except Exception as e:
            logger.error(f"Ошибка поиска через REST API: {e}", exc_info=True)
            raise Exception(f"Failed to search notes: {str(e)}")

    def read_note(self, file_path: str) -> Dict[str, Any]:
        """Читает заметку через REST API"""
        try:
            response = requests.get(
                f"{self.api_url}/vault/{file_path}",
                headers=self.headers,
                timeout=10
            )

            response.raise_for_status()
            content = response.text

            logger.info(f"Заметка прочитана через REST API: {file_path}")

            return {
                'success': True,
                'file_path': file_path,
                'content': content
            }

        except Exception as e:
            logger.error(f"Ошибка чтения через REST API: {e}", exc_info=True)
            raise Exception(f"Failed to read note: {str(e)}")

    def update_note(self, file_path: str, content: str) -> Dict[str, Any]:
        """Обновляет заметку через REST API"""
        try:
            response = requests.put(
                f"{self.api_url}/vault/{file_path}",
                headers=self.headers,
                data=content.encode('utf-8'),
                timeout=10
            )

            response.raise_for_status()

            logger.info(f"Заметка обновлена через REST API: {file_path}")

            return {
                'success': True,
                'file_path': file_path
            }

        except Exception as e:
            logger.error(f"Ошибка обновления через REST API: {e}", exc_info=True)
            raise Exception(f"Failed to update note: {str(e)}")

    def _prepare_content(self, title: str, content: str, tags: List[str] = None) -> str:
        """Подготавливает содержимое с frontmatter"""
        frontmatter_lines = [
            "---",
            f"title: {title}",
            f"created: {datetime.now().isoformat()}",
        ]

        if tags:
            tags_str = ", ".join(tags)
            frontmatter_lines.append(f"tags: [{tags_str}]")

        frontmatter_lines.append("---")
        frontmatter_lines.append("")

        content_lines = [
            f"# {title}",
            "",
            content
        ]

        return "\n".join(frontmatter_lines + content_lines)

    def _sanitize_filename(self, filename: str) -> str:
        """Очищает имя файла"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        max_length = 200
        if len(filename) > max_length:
            filename = filename[:max_length]

        return filename.strip()


class ObsidianVault:
    """Класс для работы с Obsidian хранилищем через filesystem"""

    def __init__(self, vault_path: str = None):
        """
        Инициализация Obsidian vault

        Args:
            vault_path: Путь к хранилищу Obsidian
        """
        self.vault_path = vault_path or VAULT_PATH
        self.notes_folder = NOTES_FOLDER
        self._validate_vault()

    def _validate_vault(self):
        """Проверяет существование хранилища"""
        if not os.path.exists(self.vault_path):
            raise FileNotFoundError(
                f"Obsidian vault не найден: {self.vault_path}\n"
                f"Укажите правильный путь в config.yaml"
            )

        if not os.path.isdir(self.vault_path):
            raise ValueError(f"Путь не является директорией: {self.vault_path}")

        logger.info(f"Obsidian vault: {self.vault_path}")

    def create_note(
        self,
        title: str,
        content: str,
        tags: List[str] = None,
        folder: str = None
    ) -> Dict[str, Any]:
        """
        Создаёт заметку в Obsidian

        Args:
            title: Название заметки (будет именем файла)
            content: Содержимое заметки в Markdown
            tags: Список тегов (опционально)
            folder: Папка для заметки (по умолчанию из конфига)

        Returns:
            Данные созданной заметки

        Example:
            >>> vault = ObsidianVault()
            >>> vault.create_note(
            ...     title="Новая идея",
            ...     content="Описание идеи",
            ...     tags=["проект", "идея"]
            ... )
        """

        folder = folder or self.notes_folder

        # Git pull перед операцией
        git_sync = _get_git_sync()
        if git_sync:
            git_sync.sync_before_operation()

        try:
            # Создать путь к папке
            folder_path = os.path.join(self.vault_path, folder)
            os.makedirs(folder_path, exist_ok=True)

            # Безопасное имя файла
            safe_filename = self._sanitize_filename(title)
            file_path = os.path.join(folder_path, f"{safe_filename}.md")

            # Если файл существует, добавить timestamp
            if os.path.exists(file_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(folder_path, f"{safe_filename}_{timestamp}.md")

            # Подготовить содержимое с frontmatter
            full_content = self._prepare_content(title, content, tags)

            # Создать файл
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)

            logger.info(f"Заметка создана: {file_path}")

            result = {
                'success': True,
                'title': title,
                'file_path': file_path,
                'relative_path': os.path.relpath(file_path, self.vault_path)
            }

            # Git commit + push после операции
            if git_sync:
                git_sync.sync_after_operation(f"Создана заметка: {title}")

            return result

        except Exception as e:
            logger.error(f"Ошибка при создании заметки: {e}", exc_info=True)
            raise Exception(f"Failed to create note: {str(e)}")

    def _prepare_content(self, title: str, content: str, tags: List[str] = None) -> str:
        """
        Подготавливает содержимое заметки с frontmatter

        Args:
            title: Название
            content: Содержимое
            tags: Теги

        Returns:
            Полное содержимое с frontmatter
        """

        # Frontmatter (YAML)
        frontmatter_lines = [
            "---",
            f"title: {title}",
            f"created: {datetime.now().isoformat()}",
        ]

        if tags:
            # Форматировать теги для Obsidian
            tags_str = ", ".join(tags)
            frontmatter_lines.append(f"tags: [{tags_str}]")

        frontmatter_lines.append("---")
        frontmatter_lines.append("")  # Пустая строка после frontmatter

        # Заголовок
        content_lines = [
            f"# {title}",
            "",
            content
        ]

        # Объединить всё
        full_content = "\n".join(frontmatter_lines + content_lines)

        return full_content

    def _sanitize_filename(self, filename: str) -> str:
        """
        Очищает имя файла от недопустимых символов

        Args:
            filename: Исходное имя

        Returns:
            Безопасное имя файла
        """

        # Заменить недопустимые символы
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Ограничить длину
        max_length = 200
        if len(filename) > max_length:
            filename = filename[:max_length]

        return filename.strip()

    def search_notes(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Ищет заметки по ключевым словам

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов

        Returns:
            Список найденных заметок

        Example:
            >>> vault = ObsidianVault()
            >>> results = vault.search_notes("проект")
        """

        try:
            results = []
            query_lower = query.lower()

            # Рекурсивно обойти все .md файлы
            for root, dirs, files in os.walk(self.vault_path):
                for file in files:
                    if not file.endswith('.md'):
                        continue

                    file_path = os.path.join(root, file)

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Поиск по содержимому
                        if query_lower in content.lower():
                            # Извлечь заголовок (первая строка с #)
                            title = file.replace('.md', '')
                            for line in content.split('\n'):
                                if line.startswith('# '):
                                    title = line.replace('# ', '').strip()
                                    break

                            results.append({
                                'title': title,
                                'file_path': file_path,
                                'relative_path': os.path.relpath(file_path, self.vault_path),
                                'excerpt': self._get_excerpt(content, query_lower)
                            })

                            # Лимит результатов
                            if len(results) >= limit:
                                break

                    except Exception as e:
                        logger.warning(f"Ошибка при чтении {file_path}: {e}")
                        continue

                if len(results) >= limit:
                    break

            logger.info(f"Найдено {len(results)} заметок по запросу: {query}")

            return results

        except Exception as e:
            logger.error(f"Ошибка при поиске заметок: {e}", exc_info=True)
            raise Exception(f"Failed to search notes: {str(e)}")

    def _get_excerpt(self, content: str, query: str, context_chars: int = 100) -> str:
        """
        Извлекает фрагмент текста вокруг найденного запроса

        Args:
            content: Содержимое заметки
            query: Поисковый запрос
            context_chars: Количество символов контекста

        Returns:
            Фрагмент текста
        """

        content_lower = content.lower()
        query_lower = query.lower()

        # Найти позицию запроса
        pos = content_lower.find(query_lower)
        if pos == -1:
            # Если не нашли, вернуть начало
            return content[:context_chars] + "..."

        # Извлечь контекст
        start = max(0, pos - context_chars)
        end = min(len(content), pos + len(query) + context_chars)

        excerpt = content[start:end]

        # Добавить многоточия
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(content):
            excerpt = excerpt + "..."

        return excerpt

    def read_note(self, file_path: str) -> Dict[str, Any]:
        """
        Читает заметку

        Args:
            file_path: Путь к файлу (относительный или абсолютный)

        Returns:
            Содержимое заметки
        """

        try:
            # Если путь относительный, сделать абсолютным
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.vault_path, file_path)

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            logger.info(f"Заметка прочитана: {file_path}")

            return {
                'success': True,
                'file_path': file_path,
                'content': content
            }

        except FileNotFoundError:
            raise Exception(f"Note not found: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при чтении заметки: {e}", exc_info=True)
            raise Exception(f"Failed to read note: {str(e)}")

    def update_note(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Обновляет заметку

        Args:
            file_path: Путь к файлу
            content: Новое содержимое

        Returns:
            Результат обновления
        """

        try:
            # Если путь относительный, сделать абсолютным
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.vault_path, file_path)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Заметка обновлена: {file_path}")

            return {
                'success': True,
                'file_path': file_path
            }

        except Exception as e:
            logger.error(f"Ошибка при обновлении заметки: {e}", exc_info=True)
            raise Exception(f"Failed to update note: {str(e)}")


# Глобальные экземпляры (lazy init)
_vault_instance = None
_rest_api_instance = None


def get_vault():
    """
    Получить экземпляр Obsidian клиента (выбор на основе конфигурации)

    Returns:
        ObsidianVault или ObsidianRESTAPI в зависимости от конфигурации
    """
    global _vault_instance, _rest_api_instance

    if METHOD == 'rest_api':
        if _rest_api_instance is None:
            _rest_api_instance = ObsidianRESTAPI()
        return _rest_api_instance
    else:
        if _vault_instance is None:
            _vault_instance = ObsidianVault()
        return _vault_instance
