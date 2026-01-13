"""
Интеграция с Google Tasks API
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)

# Загрузить конфигурацию
config = load_config()
SCOPES = ['https://www.googleapis.com/auth/tasks']
CREDENTIALS_FILE = config['google']['tasks']['credentials_file']
TOKEN_FILE = config['google']['tasks']['token_file']
TASK_LIST_ID = config['google']['tasks'].get('task_list_id', '@default')
SHOPPING_LIST_ID = config['google']['tasks'].get('shopping_list_id', '@default')


class GoogleTasks:
    """Класс для работы с Google Tasks API"""

    def __init__(self):
        """Инициализация клиента Google Tasks"""
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Аутентификация через OAuth 2.0"""
        creds = None

        # Проверить существующий токен
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        # Если токен недействителен или отсутствует
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Обновление токена Google Tasks")
                creds.refresh(Request())
            else:
                # Запросить новый токен
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Файл credentials не найден: {CREDENTIALS_FILE}\n"
                        f"Создайте OAuth 2.0 credentials в Google Cloud Console"
                    )

                logger.info("Запуск OAuth flow для Google Tasks")
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Сохранить токен
            os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
            logger.info(f"Токен сохранён: {TOKEN_FILE}")

        # Создать сервис
        self.service = build('tasks', 'v1', credentials=creds)
        logger.info("Google Tasks API инициализирован")

    def add_task(
        self,
        title: str,
        notes: str = None,
        due_date: str = None,
        task_list_id: str = None
    ) -> Dict[str, Any]:
        """
        Добавляет задачу в список

        Args:
            title: Название задачи
            notes: Описание/заметки
            due_date: Срок выполнения (ISO 8601)
            task_list_id: ID списка задач (по умолчанию из конфига)

        Returns:
            Данные созданной задачи

        Example:
            >>> tasks = GoogleTasks()
            >>> tasks.add_task(
            ...     title="Купить продукты",
            ...     notes="Молоко, хлеб, яйца",
            ...     due_date="2025-01-10T18:00:00Z"
            ... )
        """

        task_list_id = task_list_id or TASK_LIST_ID

        try:
            # Подготовить задачу
            task = {'title': title}

            if notes:
                task['notes'] = notes

            if due_date:
                # Google Tasks ожидает RFC 3339 формат
                task['due'] = due_date

            # Создать задачу
            created_task = self.service.tasks().insert(
                tasklist=task_list_id,
                body=task
            ).execute()

            logger.info(f"Задача создана: {created_task['id']} - {title}")

            return {
                'success': True,
                'task_id': created_task['id'],
                'title': title,
                'status': created_task.get('status'),
                'link': created_task.get('selfLink')
            }

        except HttpError as e:
            logger.error(f"Ошибка Google Tasks API: {e}", exc_info=True)
            raise Exception(f"Failed to create task: {str(e)}")

        except Exception as e:
            logger.error(f"Ошибка при создании задачи: {e}", exc_info=True)
            raise

    def add_shopping_items(self, items: List[str]) -> Dict[str, Any]:
        """
        Добавляет товары в список покупок

        Args:
            items: Список товаров

        Returns:
            Результат добавления

        Example:
            >>> tasks = GoogleTasks()
            >>> tasks.add_shopping_items(["молоко", "хлеб", "яйца"])
        """

        try:
            created_count = 0

            for item in items:
                # Создать задачу для каждого товара
                task = {
                    'title': item.strip()
                }

                self.service.tasks().insert(
                    tasklist=SHOPPING_LIST_ID,
                    body=task
                ).execute()

                created_count += 1

            logger.info(f"Добавлено {created_count} товаров в список покупок")

            return {
                'success': True,
                'count': created_count,
                'items': items
            }

        except HttpError as e:
            logger.error(f"Ошибка Google Tasks API: {e}", exc_info=True)
            raise Exception(f"Failed to add shopping items: {str(e)}")

        except Exception as e:
            logger.error(f"Ошибка при добавлении товаров: {e}", exc_info=True)
            raise

    def get_tasks(
        self,
        task_list_id: str = None,
        show_completed: bool = False,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Получает список задач

        Args:
            task_list_id: ID списка задач
            show_completed: Показывать завершенные задачи
            max_results: Максимальное количество

        Returns:
            Список задач

        Example:
            >>> tasks = GoogleTasks()
            >>> my_tasks = tasks.get_tasks(show_completed=False)
        """

        task_list_id = task_list_id or TASK_LIST_ID

        try:
            # Параметры запроса
            params = {
                'tasklist': task_list_id,
                'maxResults': max_results
            }

            if show_completed:
                params['showCompleted'] = True
                params['showHidden'] = True

            # Запрос к API
            results = self.service.tasks().list(**params).execute()
            tasks = results.get('items', [])

            logger.info(f"Получено {len(tasks)} задач")

            # Форматировать задачи
            formatted_tasks = []
            for task in tasks:
                formatted_tasks.append({
                    'id': task['id'],
                    'title': task.get('title', '(Без названия)'),
                    'notes': task.get('notes', ''),
                    'status': task.get('status'),
                    'due': task.get('due', ''),
                    'completed': task.get('completed', ''),
                    'updated': task.get('updated', '')
                })

            return formatted_tasks

        except HttpError as e:
            logger.error(f"Ошибка Google Tasks API: {e}", exc_info=True)
            raise Exception(f"Failed to get tasks: {str(e)}")

        except Exception as e:
            logger.error(f"Ошибка при получении задач: {e}", exc_info=True)
            raise

    def get_shopping_list(self, show_completed: bool = False) -> List[Dict[str, Any]]:
        """
        Получает список покупок

        Args:
            show_completed: Показывать купленные товары

        Returns:
            Список покупок
        """
        return self.get_tasks(
            task_list_id=SHOPPING_LIST_ID,
            show_completed=show_completed
        )

    def complete_task(self, task_id: str, task_list_id: str = None) -> bool:
        """
        Отмечает задачу как выполненную

        Args:
            task_id: ID задачи
            task_list_id: ID списка задач

        Returns:
            True если успешно
        """

        task_list_id = task_list_id or TASK_LIST_ID

        try:
            # Получить задачу
            task = self.service.tasks().get(
                tasklist=task_list_id,
                task=task_id
            ).execute()

            # Обновить статус
            task['status'] = 'completed'

            self.service.tasks().update(
                tasklist=task_list_id,
                task=task_id,
                body=task
            ).execute()

            logger.info(f"Задача выполнена: {task_id}")
            return True

        except HttpError as e:
            logger.error(f"Ошибка при завершении задачи: {e}", exc_info=True)
            return False

    def delete_task(self, task_id: str, task_list_id: str = None) -> bool:
        """
        Удаляет задачу

        Args:
            task_id: ID задачи
            task_list_id: ID списка задач

        Returns:
            True если успешно удалена
        """

        task_list_id = task_list_id or TASK_LIST_ID

        try:
            self.service.tasks().delete(
                tasklist=task_list_id,
                task=task_id
            ).execute()

            logger.info(f"Задача удалена: {task_id}")
            return True

        except HttpError as e:
            logger.error(f"Ошибка при удалении задачи: {e}", exc_info=True)
            return False

    def get_task_lists(self) -> List[Dict[str, Any]]:
        """
        Получает все списки задач

        Returns:
            Список всех списков задач
        """

        try:
            results = self.service.tasklists().list().execute()
            lists = results.get('items', [])

            logger.info(f"Получено {len(lists)} списков задач")

            formatted_lists = []
            for task_list in lists:
                formatted_lists.append({
                    'id': task_list['id'],
                    'title': task_list.get('title', ''),
                    'updated': task_list.get('updated', '')
                })

            return formatted_lists

        except HttpError as e:
            logger.error(f"Ошибка при получении списков: {e}", exc_info=True)
            raise Exception(f"Failed to get task lists: {str(e)}")


# Глобальный экземпляр (lazy init)
_tasks_instance = None


def get_tasks() -> GoogleTasks:
    """Получить глобальный экземпляр GoogleTasks"""
    global _tasks_instance
    if _tasks_instance is None:
        _tasks_instance = GoogleTasks()
    return _tasks_instance
