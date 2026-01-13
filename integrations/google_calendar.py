"""
Интеграция с Google Calendar API
Поддерживает синхронные и асинхронные вызовы
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)

# Thread pool для асинхронных операций
_executor = ThreadPoolExecutor(max_workers=4)

# Загрузить конфигурацию
config = load_config()
SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = config['google']['calendar']['credentials_file']
TOKEN_FILE = config['google']['calendar']['token_file']
DEFAULT_CALENDAR_ID = config['google']['calendar'].get('default_calendar_id', 'primary')


class GoogleCalendar:
    """Класс для работы с Google Calendar API"""

    def __init__(self):
        """Инициализация клиента Google Calendar"""
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
                logger.info("Обновление токена Google Calendar")
                creds.refresh(Request())
            else:
                # Запросить новый токен
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Файл credentials не найден: {CREDENTIALS_FILE}\n"
                        f"Создайте OAuth 2.0 credentials в Google Cloud Console"
                    )

                logger.info("Запуск OAuth flow для Google Calendar")
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
        self.service = build('calendar', 'v3', credentials=creds)
        logger.info("Google Calendar API инициализирован")

    def add_event(
        self,
        summary: str,
        start_time: str,
        end_time: str = None,
        description: str = None,
        location: str = None,
        calendar_id: str = None
    ) -> Dict[str, Any]:
        """
        Добавляет событие в календарь

        Args:
            summary: Название события
            start_time: Время начала (ISO 8601 формат)
            end_time: Время окончания (опционально, по умолчанию +1 час)
            description: Описание события
            location: Место проведения
            calendar_id: ID календаря (по умолчанию primary)

        Returns:
            Данные созданного события

        Example:
            >>> calendar = GoogleCalendar()
            >>> calendar.add_event(
            ...     summary="Встреча с врачом",
            ...     start_time="2025-01-09T15:00:00",
            ...     description="Ежегодный осмотр"
            ... )
        """

        calendar_id = calendar_id or DEFAULT_CALENDAR_ID

        try:
            # Парсинг времени начала
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))

            # Если время окончания не указано, +1 час
            if not end_time:
                end_dt = start_dt + timedelta(hours=1)
                end_time = end_dt.isoformat()
            else:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

            # Подготовить данные события
            event = {
                'summary': summary,
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'Europe/Moscow',  # Можно сделать конфигурируемым
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'Europe/Moscow',
                }
            }

            if description:
                event['description'] = description

            if location:
                event['location'] = location

            # Создать событие
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()

            logger.info(f"Событие создано: {created_event['id']} - {summary}")

            return {
                'success': True,
                'event_id': created_event['id'],
                'summary': summary,
                'start': start_time,
                'end': end_time,
                'link': created_event.get('htmlLink')
            }

        except HttpError as e:
            logger.error(f"Ошибка Google Calendar API: {e}", exc_info=True)
            raise Exception(f"Failed to create event: {str(e)}")

        except Exception as e:
            logger.error(f"Ошибка при создании события: {e}", exc_info=True)
            raise

    def get_events(
        self,
        time_min: str,
        time_max: str,
        max_results: int = 10,
        calendar_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Получает список событий за период

        Args:
            time_min: Начало периода (ISO 8601)
            time_max: Конец периода (ISO 8601)
            max_results: Максимальное количество событий
            calendar_id: ID календаря

        Returns:
            Список событий

        Example:
            >>> calendar = GoogleCalendar()
            >>> events = calendar.get_events(
            ...     time_min="2025-01-09T00:00:00Z",
            ...     time_max="2025-01-10T23:59:59Z"
            ... )
        """

        calendar_id = calendar_id or DEFAULT_CALENDAR_ID

        try:
            # Запрос к API
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            logger.info(f"Получено {len(events)} событий из календаря")

            # Форматировать события
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))

                formatted_events.append({
                    'id': event['id'],
                    'summary': event.get('summary', '(Без названия)'),
                    'start': start,
                    'end': end,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'link': event.get('htmlLink', '')
                })

            return formatted_events

        except HttpError as e:
            logger.error(f"Ошибка Google Calendar API: {e}", exc_info=True)
            raise Exception(f"Failed to get events: {str(e)}")

        except Exception as e:
            logger.error(f"Ошибка при получении событий: {e}", exc_info=True)
            raise

    def delete_event(self, event_id: str, calendar_id: str = None) -> bool:
        """
        Удаляет событие

        Args:
            event_id: ID события
            calendar_id: ID календаря

        Returns:
            True если успешно удалено
        """

        calendar_id = calendar_id or DEFAULT_CALENDAR_ID

        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            logger.info(f"Событие удалено: {event_id}")
            return True

        except HttpError as e:
            logger.error(f"Ошибка при удалении события: {e}", exc_info=True)
            return False

    def update_event(
        self,
        event_id: str,
        summary: str = None,
        start_time: str = None,
        end_time: str = None,
        description: str = None,
        location: str = None,
        calendar_id: str = None
    ) -> Dict[str, Any]:
        """
        Обновляет событие

        Args:
            event_id: ID события
            summary: Новое название
            start_time: Новое время начала
            end_time: Новое время окончания
            description: Новое описание
            location: Новое место
            calendar_id: ID календаря

        Returns:
            Обновлённые данные события
        """

        calendar_id = calendar_id or DEFAULT_CALENDAR_ID

        try:
            # Получить существующее событие
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            # Обновить поля
            if summary:
                event['summary'] = summary
            if description:
                event['description'] = description
            if location:
                event['location'] = location
            if start_time:
                event['start']['dateTime'] = datetime.fromisoformat(
                    start_time.replace('Z', '+00:00')
                ).isoformat()
            if end_time:
                event['end']['dateTime'] = datetime.fromisoformat(
                    end_time.replace('Z', '+00:00')
                ).isoformat()

            # Сохранить изменения
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            logger.info(f"Событие обновлено: {event_id}")

            return {
                'success': True,
                'event_id': updated_event['id'],
                'summary': updated_event.get('summary'),
                'link': updated_event.get('htmlLink')
            }

        except HttpError as e:
            logger.error(f"Ошибка при обновлении события: {e}", exc_info=True)
            raise Exception(f"Failed to update event: {str(e)}")

    # Асинхронные методы

    async def add_event_async(self, **kwargs) -> Dict[str, Any]:
        """Асинхронная версия add_event"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, lambda: self.add_event(**kwargs))

    async def get_events_async(self, **kwargs) -> List[Dict[str, Any]]:
        """Асинхронная версия get_events"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, lambda: self.get_events(**kwargs))

    async def delete_event_async(self, event_id: str, calendar_id: str = None) -> bool:
        """Асинхронная версия delete_event"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self.delete_event, event_id, calendar_id)

    async def update_event_async(self, **kwargs) -> Dict[str, Any]:
        """Асинхронная версия update_event"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, lambda: self.update_event(**kwargs))


# Глобальный экземпляр (lazy init)
_calendar_instance = None


def get_calendar() -> GoogleCalendar:
    """Получить глобальный экземпляр GoogleCalendar"""
    global _calendar_instance
    if _calendar_instance is None:
        _calendar_instance = GoogleCalendar()
    return _calendar_instance
