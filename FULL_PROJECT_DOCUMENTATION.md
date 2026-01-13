# AI-ассистент v1.0 - Полная документация проекта

**Дата:** 2026-01-13
**Версия:** 1.0 (первый релиз)
**Статус:** 🚧 Готов к первому запуску и тестированию

---

## Содержание

1. [Обзор проекта](#обзор-проекта)
2. [Архитектура системы](#архитектура-системы)
3. [Структура проекта](#структура-проекта)
4. [Технологический стек](#технологический-стек)
5. [Основные компоненты](#основные-компоненты)
6. [Интеграции](#интеграции)
7. [API Reference](#api-reference)
8. [Конфигурация](#конфигурация)
9. [База данных](#база-данных)
10. [Развёртывание](#развёртывание)
11. [Исходный код всех файлов](#исходный-код-всех-файлов)

---

## Обзор проекта

### Назначение

AI-ассистент v2.0 - это личный помощник с естественным языковым интерфейсом, который:

- Управляет календарём (Google Calendar)
- Управляет задачами и покупками (Google Tasks)
- Создаёт и ищет заметки (Obsidian)
- Работает через Telegram бот
- Поддерживает голосовую активацию через Tasker (Android)
- Распознаёт речь через Whisper API
- Озвучивает ответы через gTTS

### Основные возможности

1. **Telegram интерфейс:**
   - Текстовые команды на естественном языке
   - Голосовые сообщения с автоматическим распознаванием
   - Система подтверждений для важных действий
   - История разговора для контекста

2. **REST API для Tasker:**
   - Голосовые команды с телефона
   - Активация длинным нажатием кнопки питания
   - Автоматическое озвучивание ответов
   - Система подтверждений через диалоги

3. **Интеграции:**
   - Google Calendar (события)
   - Google Tasks (задачи и покупки)
   - Obsidian (заметки в Markdown)
   - OpenAI Whisper (распознавание речи)
   - Google TTS (озвучивание)

4. **Гибридная LLM архитектура (NEW в v2.1):**
   - Поддержка Claude API и локального Ollama
   - Автоматический выбор провайдера по сложности запроса
   - Легкое переключение между провайдерами
   - Fallback механизм при недоступности основного провайдера

5. **Персистентная память (NEW в v2.1):**
   - Изучение паттернов поведения пользователя
   - Анализ частых действий и предпочтений
   - Контекстно-зависимые ответы
   - Улучшение качества со временем

### Примеры использования

```
Пользователь: "Добавь встречу с врачом завтра в 15:00"
Бот: "📅 Правильно ли я понял: добавить событие 'Встреча с врачом' на 09 января в 15:00?"
[Кнопки: Да | Нет]
Пользователь: [Нажимает "Да"]
Бот: "✅ Событие 'Встреча с врачом' добавлено в календарь"
```

```
Пользователь: "Что у меня сегодня?"
Бот: "📅 Найдено событий: 3
• Встреча с командой (09.01 в 10:00)
• Обед с клиентом (09.01 в 13:00)
• Тренировка (09.01 в 18:00)"
```

---

## Архитектура системы

### Общая схема

```
┌─────────────────────────────────────────────────────────────┐
│                         ПОЛЬЗОВАТЕЛЬ                         │
└────────────┬───────────────────────────────────┬─────────────┘
             │                                   │
             │ Telegram                          │ Tasker (Android)
             │                                   │
             v                                   v
┌────────────────────────┐          ┌───────────────────────────┐
│   Telegram Bot API     │          │      REST API (FastAPI)   │
│  (python-telegram-bot) │          │  + Bearer Auth            │
└────────────┬───────────┘          └───────────┬───────────────┘
             │                                   │
             └──────────────┬────────────────────┘
                            │
                            v
             ┌──────────────────────────┐
             │   Claude Agent           │
             │   (Function Calling)     │
             └──────────────┬───────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          v                 v                 v
┌─────────────────┐  ┌──────────────┐  ┌──────────────┐
│ Google Calendar │  │ Google Tasks │  │   Obsidian   │
│   (OAuth 2.0)   │  │  (OAuth 2.0) │  │ (Filesystem) │
└─────────────────┘  └──────────────┘  └──────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Вспомогательные сервисы                   │
├─────────────────┬─────────────────┬─────────────────────────┤
│  Whisper API    │      gTTS       │   SQLite Database       │
│  (Speech-to-Text)│ (Text-to-Speech)│   (История, статистика)│
└─────────────────┴─────────────────┴─────────────────────────┘
```

### Компонентная архитектура

```
ai-assistant/
│
├── main.py                    # Точка входа (multiprocessing)
│
├── bot/                       # Telegram бот
│   ├── telegram_bot.py       # Основной класс бота
│   ├── message_handler.py    # Обработка текстовых сообщений
│   └── voice_handler.py      # Обработка голосовых сообщений
│
├── api/                       # REST API
│   ├── app.py                # FastAPI приложение
│   ├── routes/               # Endpoints
│   │   ├── voice.py          # POST /api/v1/voice-command
│   │   ├── text.py           # POST /api/v1/text-command
│   │   ├── confirm.py        # POST /api/v1/confirm
│   │   └── tts.py            # GET /api/v1/tts/{filename}
│   ├── middleware/
│   │   └── auth.py           # Bearer token авторизация
│   └── models.py             # Pydantic модели
│
├── agent/                     # Claude AI агент
│   ├── claude_agent.py       # Основной класс агента
│   └── tools.py              # Определение инструментов
│
├── integrations/              # Внешние интеграции
│   ├── google_calendar.py    # Google Calendar API
│   ├── google_tasks.py       # Google Tasks API
│   ├── obsidian.py           # Obsidian (filesystem)
│   ├── whisper.py            # OpenAI Whisper API
│   └── tts.py                # Google TTS
│
└── utils/                     # Утилиты
    ├── config.py             # Загрузка конфигурации
    ├── database.py           # SQLite (async)
    ├── logger.py             # Логирование
    └── cache.py              # Кэширование TTS
```

### Поток обработки запроса

#### Через Telegram:

```
1. Пользователь отправляет сообщение
   ↓
2. telegram_bot.py получает сообщение
   ↓
3. message_handler.py определяет тип (текст/голос)
   ↓
4. Если голос → voice_handler.py → Whisper API → текст
   ↓
5. claude_agent.py обрабатывает через Function Calling
   ↓
6. Claude определяет нужный инструмент (tool)
   ↓
7. _execute_tool() вызывает соответствующую интеграцию
   ↓
8. Если требуется подтверждение → показать inline кнопки
   ↓
9. После подтверждения → выполнить действие
   ↓
10. Вернуть результат пользователю
```

#### Через Tasker API:

```
1. Длинное нажатие кнопки питания на Android
   ↓
2. Tasker записывает голос (5 сек)
   ↓
3. POST /api/v1/voice-command (multipart/form-data)
   ↓
4. auth.py проверяет Bearer token
   ↓
5. voice.py → Whisper API → распознавание
   ↓
6. claude_agent.py обрабатывает запрос
   ↓
7. Если требуется подтверждение → возвращает confirmation_id
   ↓
8. tts.py генерирует аудио ответ (кэширование)
   ↓
9. Возвращает JSON с audio_url
   ↓
10. Tasker скачивает и воспроизводит аудио
```

---

## Структура проекта

### Дерево файлов

```
ai-assistant/
├── README.md
├── PROGRESS.md
├── requirements.txt
├── config.yaml.example
├── .env.example
├── .gitignore
├── main.py
│
├── agent/
│   ├── __init__.py
│   ├── claude_agent.py        (593 строки) - основной агент с Ollama
│   ├── tools.py                (237 строк) - определения инструментов
│   ├── llm_provider.py         (380 строк) - NEW: абстракция LLM провайдеров
│   └── memory.py               (310 строк) - NEW: персистентная память
│
├── api/
│   ├── __init__.py
│   ├── app.py                  (156 строк)
│   ├── models.py               (89 строк)
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── auth.py             (72 строки)
│   └── routes/
│       ├── __init__.py
│       ├── confirm.py          (148 строк)
│       ├── text.py             (142 строки)
│       ├── tts.py              (96 строк)
│       └── voice.py            (181 строка)
│
├── bot/
│   ├── __init__.py
│   ├── telegram_bot.py         (245 строк)
│   ├── message_handler.py      (243 строки)
│   └── voice_handler.py        (189 строк)
│
├── integrations/
│   ├── __init__.py
│   ├── google_calendar.py      (340 строк)
│   ├── google_tasks.py         (367 строк)
│   ├── obsidian.py             (354 строки)
│   ├── tts.py                  (173 строки)
│   └── whisper.py              (121 строка)
│
├── utils/
│   ├── __init__.py
│   ├── cache.py                (134 строки)
│   ├── config.py               (98 строк)
│   ├── database.py             (312 строк)
│   └── logger.py               (97 строк)
│
├── docs/
│   ├── setup.md                (~800 строк)
│   ├── deployment.md           (~1200 строк)
│   ├── usage.md                (~900 строк)
│   └── tasker_setup.md         (~700 строк)
│
├── nginx/
│   ├── ai_assistant.conf       (~130 строк)
│   └── setup_https.md          (~500 строк)
│
├── systemd/
│   ├── ai-assistant-bot.service
│   └── ai-assistant-api.service
│
├── tasker/
│   └── AI_Assistant.prj.xml    (~300 строк)
│
├── credentials/                 (создаётся при настройке)
│   ├── google_calendar_credentials.json
│   └── google_tasks_credentials.json
│
├── data/                        (создаётся автоматически)
│   ├── ai_assistant.db
│   ├── google_calendar_token.json
│   └── google_tasks_token.json
│
├── logs/                        (создаётся автоматически)
│   └── app.log
│
└── cache/                       (создаётся автоматически)
    └── *.mp3                    (TTS файлы)
```

### Статистика

- **Всего файлов:** 40+
- **Строк кода Python:** ~5000
- **Строк документации:** ~3600
- **Строк конфигурации:** ~500

---

## Технологический стек

### Backend

| Технология | Версия | Назначение |
|------------|--------|------------|
| Python | 3.11+ | Основной язык |
| FastAPI | 0.104+ | REST API framework |
| python-telegram-bot | 20.0+ | Telegram Bot API |
| anthropic | latest | Claude AI SDK |
| openai | 1.3+ | Whisper API |
| google-api-python-client | latest | Google APIs |
| gTTS | latest | Text-to-Speech |
| aiosqlite | 0.19+ | Async SQLite |
| pydantic | 2.0+ | Data validation |
| uvicorn | latest | ASGI server |
| pyyaml | latest | Config parsing |

### Инфраструктура

| Компонент | Технология |
|-----------|------------|
| База данных | SQLite |
| Web сервер | Nginx |
| HTTPS | Let's Encrypt (Certbot) |
| Process manager | systemd |
| Логирование | JSON + rotating files |
| Кэширование | Filesystem (MD5) |

### Внешние сервисы

| Сервис | API | Назначение |
|--------|-----|------------|
| Anthropic Claude | REST API | Natural Language Understanding |
| OpenAI Whisper | REST API | Speech-to-Text |
| Google Calendar | REST API (OAuth 2.0) | Управление событиями |
| Google Tasks | REST API (OAuth 2.0) | Управление задачами |
| Telegram | Bot API | Telegram интерфейс |
| Google TTS | gTTS library | Text-to-Speech |

---

## Основные компоненты

### 1. main.py - Точка входа

**Назначение:** Запуск Telegram бота и API в отдельных процессах

**Функционал:**
- Multiprocessing для параллельного запуска
- Graceful shutdown
- Аргументы командной строки (--bot-only, --api-only)

**Ключевые функции:**
```python
def run_telegram_bot()  # Запуск бота
def run_api_server()    # Запуск API
def main()              # Главная функция
```

### 2. Claude Agent (agent/claude_agent.py)

**Назначение:** Обработка запросов через Claude AI с Function Calling

**Класс:** `ClaudeAgent`

**Основные методы:**

```python
async def process_message(
    message: str,
    user_id: str,
    conversation_history: Optional[List] = None
) -> Dict[str, Any]:
    """
    Обрабатывает сообщение пользователя

    Returns:
        {
            "action": "confirm" | "executed",
            "action_type": str,
            "response_text": str,
            "confirmation_id": str (optional),
            "tokens_used": int
        }
    """
```

**Function Calling Tools:**

1. **add_calendar_event** - Добавить событие в календарь
2. **get_calendar_events** - Получить события
3. **add_task** - Добавить задачу
4. **add_shopping_item** - Добавить покупки
5. **get_tasks** - Получить задачи
6. **create_note** - Создать заметку
7. **search_notes** - Найти заметки

**Система подтверждений:**

Действия, требующие подтверждения:
- `add_calendar_event`
- `add_task`
- `add_shopping_item`
- `create_note`

Действия без подтверждения:
- `get_calendar_events`
- `get_tasks`
- `search_notes`

### 3. Telegram Bot (bot/)

#### telegram_bot.py

**Класс:** `TelegramBot`

**Команды:**
- `/start` - Приветствие
- `/help` - Справка
- `/stats` - Статистика
- `/cancel` - Отмена

**Обработчики:**
- `MessageHandler` - текстовые сообщения
- `VoiceHandler` - голосовые сообщения
- `CallbackQueryHandler` - inline кнопки

#### message_handler.py

**Функционал:**
- Обработка текстовых сообщений
- Интеграция с Claude Agent
- Система подтверждений с inline кнопками
- Сохранение истории в БД

**Inline кнопки для подтверждения:**
```python
keyboard = [
    [
        InlineKeyboardButton("✓ Да", callback_data=f"confirm:{confirmation_id}"),
        InlineKeyboardButton("✗ Нет", callback_data=f"cancel:{confirmation_id}")
    ]
]
```

#### voice_handler.py

**Функционал:**
- Скачивание голосовых сообщений
- Конвертация OGG → WAV/M4A
- Отправка в Whisper API
- Голосовой ответ через gTTS

### 4. REST API (api/)

#### app.py

**FastAPI приложение**

**Endpoints:**
- `POST /api/v1/voice-command` - Голосовая команда
- `POST /api/v1/text-command` - Текстовая команда
- `POST /api/v1/confirm` - Подтверждение действия
- `GET /api/v1/tts/{filename}` - TTS аудио файл
- `GET /api/v1/health` - Health check
- `GET /docs` - Swagger UI

**Middleware:**
- CORS
- Logging
- Error handling
- Bearer token authentication

#### models.py

**Pydantic модели:**

```python
class VoiceCommandRequest(BaseModel):
    user_id: str
    # + audio file (multipart)

class TextCommandRequest(BaseModel):
    text: str
    user_id: str

class ConfirmRequest(BaseModel):
    confirmation_id: str
    user_id: str
    confirmed: bool

class CommandResponse(BaseModel):
    message: str
    action: str
    audio_url: Optional[str]
    confirmation_id: Optional[str]
```

#### middleware/auth.py

**Bearer Token Authentication:**

```python
async def verify_token(
    authorization: str = Header(...)
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401)

    token = authorization.replace("Bearer ", "")
    if token != EXPECTED_TOKEN:
        raise HTTPException(401)
```

### 5. Database (utils/database.py)

**Класс:** `Database`

**Схема таблиц:**

```sql
-- Таблица сообщений
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'user' или 'assistant'
    content TEXT NOT NULL,
    session_id TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Таблица подтверждений
CREATE TABLE confirmations (
    id TEXT PRIMARY KEY,  -- UUID
    user_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_data TEXT NOT NULL,  -- JSON
    confirmation_text TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- 'pending', 'confirmed', 'cancelled'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

-- Таблица статистики
CREATE TABLE usage_stats (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    interface TEXT NOT NULL,  -- 'telegram' или 'api'
    action_type TEXT,
    tokens_used INTEGER DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Основные методы:**

```python
async def save_message(user_id, role, content, session_id=None)
async def get_message_history(user_id, limit=50, session_id=None)
async def save_confirmation(confirmation_id, user_id, action_type, action_data, confirmation_text)
async def get_confirmation(confirmation_id)
async def update_confirmation_status(confirmation_id, status)
async def save_usage_stats(user_id, interface, action_type, tokens_used)
async def get_usage_stats(user_id)
```

### 6. Логирование (utils/logger.py)

**Структурированное логирование:**

```python
# JSON формат в файл
{
    "timestamp": "2025-01-08T15:30:00",
    "level": "INFO",
    "module": "claude_agent",
    "message": "Обработка сообщения от user123",
    "extra": {...}
}

# Человеко-читаемый формат в консоль
2025-01-08 15:30:00 - INFO - claude_agent - Обработка сообщения
```

**Ротация логов:**
- Максимальный размер: 10 MB
- Количество бэкапов: 5
- Автоматическое архивирование

---

## Новые компоненты v2.1

### 7. LLM Provider (agent/llm_provider.py)

**Назначение:** Абстракция для работы с различными LLM провайдерами

**Классы:**

```python
class LLMProvider(ABC):
    """Базовый класс для LLM провайдера"""

    async def generate(messages, system_prompt, tools, ...) -> LLMResponse
    def is_available() -> bool
    def get_name() -> str
```

**Реализации:**

1. **ClaudeProvider** - для Claude API (Anthropic)
   - Полная поддержка function calling
   - Динамический выбор модели (Haiku/Sonnet)
   - Подсчёт токенов

2. **OllamaProvider** - для локального Ollama
   - Работает без интернета
   - Поддержка chat API
   - Приблизительный подсчёт токенов

3. **HybridLLMRouter** - умный роутер
   - Автоматический выбор провайдера по сложности
   - Fallback механизм при ошибках
   - Классификация простых/сложных запросов

**Пример использования:**

```python
from agent.llm_provider import create_llm_router

router = create_llm_router(config)
response = await router.generate(
    messages=[{"role": "user", "content": "Добавь молоко в покупки"}],
    system_prompt="Ты - личный ассистент",
    tools=TOOLS
)

print(response.text)
print(f"Модель: {response.model_used}")
print(f"Токенов: {response.tokens_used}")
```

**Преимущества:**

- ✅ Легко переключаться между Claude и Ollama (один параметр в конфиге)
- ✅ Можно добавить новые провайдеры (GPT-4, Gemini) без изменения остального кода
- ✅ Автоматический fallback при проблемах
- ✅ Единый интерфейс для всех LLM

---

### 8. Memory System (agent/memory.py)

**Назначение:** Персистентная память для изучения паттернов пользователя

**Классы:**

```python
class UserMemory:
    """Память для конкретного пользователя"""

    async def get_context_summary(days=30) -> Dict
    async def get_frequent_shopping_items(limit=10) -> List[str]
    async def get_context_prompt() -> str
```

```python
class MemoryManager:
    """Глобальный менеджер памяти"""

    def get_user_memory(user_id) -> UserMemory
    async def get_enriched_system_prompt(base_prompt, user_id) -> str
    async def save_action_pattern(user_id, action_type, action_data)
```

**Что анализируется:**

1. **Частые действия** - какие команды пользователь выполняет чаще всего
2. **Частые ключевые слова** - о чём пользователь обычно спрашивает
3. **Часы активности** - когда пользователь обычно активен
4. **Частые покупки** - какие товары пользователь покупает регулярно

**Пример контекстного промпта:**

```
Пользователь взаимодействовал с ассистентом 147 раз за последний месяц.
Частые действия: add_shopping_item, get_calendar_events, add_task.
Часто упоминаемые темы: молоко, встреча, задачи, спортзал, врач.
Часто покупаемые товары: молоко, хлеб, яйца, сыр.
Пользователь обычно активен утром и вечером.
```

**Преимущества:**

- ✅ Ассистент "помнит" предпочтения пользователя
- ✅ Более релевантные предложения (например, автодополнение покупок)
- ✅ Лучше понимает контекст запросов
- ✅ Качество улучшается со временем

**Пример использования:**

```python
from agent.memory import get_memory_manager

memory = get_memory_manager()

# Обогатить системный промпт контекстом
enriched_prompt = await memory.get_enriched_system_prompt(
    base_prompt="Ты - личный ассистент",
    user_id="user123"
)

# Сохранить паттерн действия
await memory.save_action_pattern(
    user_id="user123",
    action_type="add_shopping_item",
    action_data={"items": ["молоко", "хлеб"]}
)

# Получить память пользователя
user_memory = memory.get_user_memory("user123")
frequent_items = await user_memory.get_frequent_shopping_items()
print(f"Частые покупки: {frequent_items}")
```

---

## Интеграции

### 1. Google Calendar (integrations/google_calendar.py)

**Класс:** `GoogleCalendar`

**Аутентификация:** OAuth 2.0

**Основные методы:**

```python
def add_event(
    summary: str,
    start_time: str,  # ISO 8601
    end_time: str = None,
    description: str = None,
    location: str = None
) -> Dict:
    """Добавляет событие в календарь"""

def get_events(
    time_min: str,
    time_max: str,
    max_results: int = 10
) -> List[Dict]:
    """Получает события за период"""

def update_event(event_id: str, ...) -> Dict:
    """Обновляет событие"""

def delete_event(event_id: str) -> bool:
    """Удаляет событие"""
```

**Формат времени:**
```python
# Пример
start_time = "2025-01-09T15:00:00"  # ISO 8601
timezone = "Europe/Moscow"
```

**Пример использования:**
```python
from integrations.google_calendar import get_calendar

calendar = get_calendar()
event = calendar.add_event(
    summary="Встреча с врачом",
    start_time="2025-01-09T15:00:00",
    description="Ежегодный осмотр"
)
```

### 2. Google Tasks (integrations/google_tasks.py)

**Класс:** `GoogleTasks`

**Аутентификация:** OAuth 2.0

**Списки задач:**
- Основной список (tasks)
- Список покупок (shopping)

**Основные методы:**

```python
def add_task(
    title: str,
    notes: str = None,
    due_date: str = None
) -> Dict:
    """Добавляет задачу"""

def add_shopping_items(items: List[str]) -> Dict:
    """Добавляет товары в список покупок"""

def get_tasks(
    show_completed: bool = False
) -> List[Dict]:
    """Получает список задач"""

def complete_task(task_id: str) -> bool:
    """Отмечает задачу выполненной"""

def delete_task(task_id: str) -> bool:
    """Удаляет задачу"""
```

**Пример использования:**
```python
from integrations.google_tasks import get_tasks

tasks = get_tasks()

# Добавить задачу
tasks.add_task(
    title="Позвонить в банк",
    due_date="2025-01-10T18:00:00Z"
)

# Добавить покупки
tasks.add_shopping_items([
    "молоко",
    "хлеб",
    "яйца"
])
```

### 3. Obsidian (integrations/obsidian.py)

**Класс:** `ObsidianVault`

**Метод:** Filesystem (прямая работа с файлами)

**Основные методы:**

```python
def create_note(
    title: str,
    content: str,
    tags: List[str] = None,
    folder: str = None
) -> Dict:
    """Создаёт заметку в Markdown"""

def search_notes(
    query: str,
    limit: int = 5
) -> List[Dict]:
    """Ищет заметки по ключевым словам"""

def read_note(file_path: str) -> Dict:
    """Читает заметку"""

def update_note(file_path: str, content: str) -> Dict:
    """Обновляет заметку"""
```

**Формат заметок (Markdown + frontmatter):**

```markdown
---
title: Название заметки
created: 2025-01-08T15:30:00
tags: [идея, проект]
---

# Название заметки

Содержимое заметки...
```

**Пример использования:**
```python
from integrations.obsidian import get_vault

vault = get_vault()

# Создать заметку
vault.create_note(
    title="Новая идея",
    content="Описание идеи...",
    tags=["проект", "идея"]
)

# Найти заметки
results = vault.search_notes("проект")
```

### 4. Whisper API (integrations/whisper.py)

**Функция:** `transcribe_audio()`

**API:** OpenAI Whisper API

**Функционал:**
- Распознавание речи из аудио файлов
- Поддержка форматов: MP3, M4A, WAV, OGG
- Автоопределение языка или указание конкретного

**Пример использования:**
```python
from integrations.whisper import transcribe_audio

text = transcribe_audio(
    audio_file_path="/path/to/audio.m4a",
    language="ru"  # опционально
)
print(text)  # "Добавь встречу завтра в три часа"
```

### 5. Google TTS (integrations/tts.py)

**Функции:**
- `text_to_speech(text: str) -> str` - генерация TTS
- `get_or_create_tts_url(text: str, base_url: str) -> str` - с кэшированием
- `cleanup_old_cache()` - очистка старых файлов

**Кэширование:**
- Хэш: MD5(text)
- Формат: `{hash}.mp3`
- Автоочистка: файлы старше 7 дней

**Пример использования:**
```python
from integrations.tts import get_or_create_tts_url

# Генерация с кэшированием
audio_url = get_or_create_tts_url(
    text="Событие добавлено в календарь",
    base_url="https://your-domain.com"
)
# Вернёт: https://your-domain.com/api/v1/tts/abc123.mp3
```

---

## API Reference

### POST /api/v1/voice-command

**Описание:** Обработка голосовой команды

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: multipart/form-data
```

**Request:**
```
audio: файл (audio/m4a, audio/wav, audio/mp3)
user_id: string
```

**Response:**
```json
{
  "message": "✅ Событие 'Встреча' добавлено в календарь",
  "action": "executed",
  "audio_url": "https://domain.com/api/v1/tts/abc123.mp3",
  "confirmation_id": null
}
```

**Или с подтверждением:**
```json
{
  "message": "",
  "action": "confirm",
  "audio_url": "https://domain.com/api/v1/tts/def456.mp3",
  "confirmation_id": "550e8400-e29b-41d4-a716-446655440000",
  "confirmation_text": "📅 Правильно ли я понял: добавить событие 'Встреча' на завтра в 15:00?"
}
```

**Коды ответов:**
- `200` - Успешно
- `401` - Неверный токен
- `400` - Некорректный запрос
- `500` - Внутренняя ошибка

---

### POST /api/v1/text-command

**Описание:** Обработка текстовой команды

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request:**
```json
{
  "text": "Добавь встречу завтра в 15:00",
  "user_id": "user123"
}
```

**Response:** аналогично `/voice-command`

---

### POST /api/v1/confirm

**Описание:** Подтверждение или отмена действия

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request:**
```json
{
  "confirmation_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "confirmed": true
}
```

**Response:**
```json
{
  "message": "✅ Событие 'Встреча' добавлено в календарь",
  "action": "executed",
  "audio_url": "https://domain.com/api/v1/tts/xyz789.mp3"
}
```

---

### GET /api/v1/tts/{filename}

**Описание:** Получить TTS аудио файл

**Headers:** не требуются (публичный endpoint)

**Request:**
```
GET /api/v1/tts/abc123.mp3
```

**Response:**
```
Content-Type: audio/mpeg
Content: <binary audio data>
```

**Коды ответов:**
- `200` - Файл найден
- `404` - Файл не найден

---

### GET /api/v1/health

**Описание:** Health check

**Response:**
```json
{
  "status": "ok"
}
```

---

## Конфигурация

### config.yaml

**Полная структура:**

```yaml
# Telegram Bot
telegram:
  bot_token: "YOUR_BOT_TOKEN"
  allowed_users: []  # Пустой список = все пользователи

# REST API
api:
  host: "127.0.0.1"
  port: 8000
  auth:
    enabled: true
    bearer_token: "your-random-token"
  cors:
    enabled: true
    origins:
      - "http://localhost"
      - "https://your-domain.com"

# Claude AI
claude:
  api_key: "YOUR_CLAUDE_API_KEY"
  model: "claude-sonnet-4-20250514"
  max_tokens: 4096
  temperature: 0.7

# OpenAI (Whisper)
openai:
  api_key: "YOUR_OPENAI_API_KEY"

# Google Calendar
google:
  calendar:
    credentials_file: "credentials/google_calendar_credentials.json"
    token_file: "data/google_calendar_token.json"
    default_calendar_id: "primary"

  # Google Tasks
  tasks:
    credentials_file: "credentials/google_tasks_credentials.json"
    token_file: "data/google_tasks_token.json"
    task_list_id: "@default"
    shopping_list_id: "@default"

# Obsidian
obsidian:
  vault_path: "/path/to/obsidian/vault"
  notes_folder: "Notes"
  method: "filesystem"

# Text-to-Speech
tts:
  engine: "gtts"
  language: "ru"
  cache_dir: "cache"
  cache_max_age_days: 7

# Database
database:
  path: "data/ai_assistant.db"

# Система персистентной памяти (NEW v2.1)
memory:
  enabled: true  # Включить персистентную память
  context_days: 30  # Анализировать последние N дней
  cleanup_days: 90  # Удалять данные старше N дней

# Logging
logging:
  level: "INFO"
  file: "logs/app.log"
  max_size_mb: 10
  backup_count: 5
  format: "json"
```

### .env

**Переменные окружения:**

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Claude AI
CLAUDE_API_KEY=your_claude_api_key

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# API Auth
API_BEARER_TOKEN=your_random_secure_token

# Optional overrides
# LOG_LEVEL=DEBUG
# API_HOST=0.0.0.0
# API_PORT=8000
```

### requirements.txt

```
# Core
python>=3.11

# Async
aiohttp==3.9.1
aiosqlite==0.19.0
asyncio==3.4.3

# Telegram
python-telegram-bot==20.7

# API
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6

# AI
anthropic==0.7.7
openai==1.3.0

# Google APIs
google-auth==2.25.2
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
google-api-python-client==2.110.0

# TTS
gTTS==2.5.0

# Utils
pyyaml==6.0.1
python-dotenv==1.0.0
requests==2.31.0

# Audio processing
pydub==0.25.1
```

---

## База данных

### Схема

#### Таблица: messages

Хранит историю сообщений для контекста

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | INTEGER PRIMARY KEY | Автоинкремент |
| user_id | TEXT NOT NULL | ID пользователя |
| role | TEXT NOT NULL | 'user' или 'assistant' |
| content | TEXT NOT NULL | Содержимое сообщения |
| session_id | TEXT | ID сессии (опционально) |
| timestamp | DATETIME | Время создания |

**Индексы:**
```sql
CREATE INDEX idx_messages_user ON messages(user_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp DESC);
```

#### Таблица: confirmations

Хранит запросы на подтверждение действий

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | TEXT PRIMARY KEY | UUID |
| user_id | TEXT NOT NULL | ID пользователя |
| action_type | TEXT NOT NULL | Тип действия (add_calendar_event и т.д.) |
| action_data | TEXT NOT NULL | JSON с параметрами действия |
| confirmation_text | TEXT NOT NULL | Текст для пользователя |
| status | TEXT | 'pending', 'confirmed', 'cancelled' |
| created_at | DATETIME | Время создания |
| updated_at | DATETIME | Время обновления |

**Индексы:**
```sql
CREATE INDEX idx_confirmations_user ON confirmations(user_id);
CREATE INDEX idx_confirmations_status ON confirmations(status);
```

#### Таблица: usage_stats

Статистика использования API

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | INTEGER PRIMARY KEY | Автоинкремент |
| user_id | TEXT NOT NULL | ID пользователя |
| interface | TEXT NOT NULL | 'telegram' или 'api' |
| action_type | TEXT | Тип действия |
| tokens_used | INTEGER | Количество токенов Claude |
| timestamp | DATETIME | Время запроса |

**Индексы:**
```sql
CREATE INDEX idx_stats_user ON usage_stats(user_id);
CREATE INDEX idx_stats_timestamp ON usage_stats(timestamp DESC);
```

### Примеры запросов

**Получить последние 50 сообщений:**
```sql
SELECT * FROM messages
WHERE user_id = 'user123'
ORDER BY timestamp DESC
LIMIT 50;
```

**Статистика по пользователю:**
```sql
SELECT
    interface,
    COUNT(*) as requests,
    SUM(tokens_used) as total_tokens
FROM usage_stats
WHERE user_id = 'user123'
GROUP BY interface;
```

**Активные подтверждения:**
```sql
SELECT * FROM confirmations
WHERE user_id = 'user123'
  AND status = 'pending'
  AND created_at > datetime('now', '-1 hour')
ORDER BY created_at DESC;
```

---

## Развёртывание

### Системные требования

**Минимальные:**
- Ubuntu 22.04 LTS / Debian 12+
- 2 GB RAM
- 20 GB disk
- Python 3.11+

**Рекомендуемые:**
- 4 GB RAM
- 50 GB disk
- SSD storage

### Установка

**1. Подготовка сервера:**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3.11 python3.11-venv \
    nginx certbot python3-certbot-nginx sqlite3 ffmpeg
```

**2. Создание пользователя:**
```bash
sudo useradd -m -s /bin/bash ai-assistant
sudo mkdir -p /opt/ai-assistant
sudo chown ai-assistant:ai-assistant /opt/ai-assistant
```

**3. Установка проекта:**
```bash
cd /opt/ai-assistant
git clone <repo-url> .

python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**4. Конфигурация:**
```bash
cp config.yaml.example config.yaml
cp .env.example .env

nano config.yaml  # Настроить
nano .env         # Настроить
```

**5. Инициализация БД:**
```bash
python -c "import asyncio; from utils.database import Database; asyncio.run(Database().init_db())"
```

**6. Google OAuth:**
```bash
# Загрузить credentials с Google Cloud Console
# Поместить в credentials/

# Авторизоваться
python -c "from integrations.google_calendar import get_calendar; get_calendar()"
python -c "from integrations.google_tasks import get_tasks; get_tasks()"
```

**7. Systemd сервисы:**
```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-assistant-bot ai-assistant-api
sudo systemctl start ai-assistant-bot ai-assistant-api
```

**8. Nginx + HTTPS:**
```bash
sudo cp nginx/ai_assistant.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/ai_assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Let's Encrypt
sudo certbot --nginx -d your-domain.com
```

**9. Проверка:**
```bash
# API health check
curl https://your-domain.com/api/v1/health

# Логи
sudo journalctl -u ai-assistant-bot -f
sudo journalctl -u ai-assistant-api -f
```

### Мониторинг

**Логи приложения:**
```bash
tail -f /opt/ai-assistant/logs/app.log
```

**Системные логи:**
```bash
sudo journalctl -u ai-assistant-bot -n 50
sudo journalctl -u ai-assistant-api -n 50
```

**Nginx логи:**
```bash
tail -f /var/log/nginx/ai_assistant_access.log
tail -f /var/log/nginx/ai_assistant_error.log
```

**Использование ресурсов:**
```bash
htop
df -h
du -sh /opt/ai-assistant/*
```

### Резервное копирование

**Скрипт бэкапа:**
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/ai-assistant"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# БД
cp /opt/ai-assistant/data/ai_assistant.db $BACKUP_DIR/db_$DATE.db

# Конфигурация
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    /opt/ai-assistant/config.yaml \
    /opt/ai-assistant/.env \
    /opt/ai-assistant/credentials/

# Удалить старые (>30 дней)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
```

**Cron:**
```
0 3 * * * /opt/ai-assistant/backup.sh
```

---

## Исходный код всех файлов

### main.py

```python
"""
Главный файл для запуска AI-ассистента
Поддерживает multiprocessing для параллельного запуска бота и API
"""

import sys
import asyncio
import argparse
from multiprocessing import Process
import uvicorn

from bot.telegram_bot import TelegramBot
from utils.logger import get_logger

logger = get_logger(__name__)


def run_telegram_bot():
    """Запуск Telegram бота"""
    try:
        logger.info("Запуск Telegram бота...")
        bot = TelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Telegram бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка в Telegram боте: {e}", exc_info=True)
        sys.exit(1)


def run_api_server():
    """Запуск API сервера"""
    try:
        logger.info("Запуск API сервера...")
        from utils.config import load_config
        config = load_config()

        uvicorn.run(
            "api.app:app",
            host=config['api']['host'],
            port=config['api']['port'],
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("API сервер остановлен")
    except Exception as e:
        logger.error(f"Ошибка в API сервере: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='AI Assistant')
    parser.add_argument('--bot-only', action='store_true', help='Run only Telegram bot')
    parser.add_argument('--api-only', action='store_true', help='Run only API server')
    args = parser.parse_args()

    if args.bot_only:
        logger.info("Режим: только Telegram бот")
        run_telegram_bot()
    elif args.api_only:
        logger.info("Режим: только API сервер")
        run_api_server()
    else:
        logger.info("Режим: Telegram бот + API сервер (multiprocessing)")

        # Запуск в отдельных процессах
        bot_process = Process(target=run_telegram_bot, name="TelegramBot")
        api_process = Process(target=run_api_server, name="APIServer")

        try:
            bot_process.start()
            api_process.start()

            bot_process.join()
            api_process.join()

        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
            bot_process.terminate()
            api_process.terminate()
            bot_process.join()
            api_process.join()
            logger.info("Все процессы остановлены")


if __name__ == "__main__":
    main()
```

### agent/claude_agent.py

```python
"""
Claude AI Agent с Function Calling
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from anthropic import Anthropic

from utils.logger import get_logger
from utils.config import load_config
from agent.tools import TOOLS, get_system_prompt, get_tool_by_name

logger = get_logger(__name__)


class ClaudeAgent:
    """Класс для работы с Claude AI через Function Calling"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация агента

        Args:
            config: Конфигурация (если None, загружается автоматически)
        """
        if config is None:
            config = load_config()

        self.config = config
        self.api_key = config['claude']['api_key']
        self.model = config['claude'].get('model', 'claude-sonnet-4-20250514')
        self.max_tokens = config['claude'].get('max_tokens', 4096)
        self.temperature = config['claude'].get('temperature', 0.7)

        # Инициализация Anthropic клиента
        self.client = Anthropic(api_key=self.api_key)

        logger.info(f"Claude Agent инициализирован (модель: {self.model})")

    async def process_message(
        self,
        message: str,
        user_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Обрабатывает сообщение пользователя через Claude

        Args:
            message: Текст сообщения
            user_id: ID пользователя
            conversation_history: История разговора (опционально)

        Returns:
            Результат обработки с полями:
            - action: "confirm" или "executed"
            - action_type: тип действия
            - confirmation_text: текст для подтверждения (если action="confirm")
            - response_text: текст ответа пользователю
            - confirmation_id: ID подтверждения (если action="confirm")
            - tokens_used: количество использованных токенов
        """
        logger.info(f"Обработка сообщения от {user_id}: {message}")

        try:
            # Подготовить системный промпт с текущей датой/временем
            today = datetime.now().strftime("%Y-%m-%d (%A)")
            current_time = datetime.now().strftime("%H:%M")
            system_prompt = get_system_prompt(today, current_time)

            # Подготовить историю сообщений
            messages = []

            if conversation_history:
                for msg in conversation_history:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            # Добавить текущее сообщение
            messages.append({
                "role": "user",
                "content": message
            })

            # Выполнить запрос к Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                tools=TOOLS,
                messages=messages
            )

            logger.info(f"Получен ответ от Claude (stop_reason: {response.stop_reason})")

            # Подсчитать использованные токены
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            # Обработать ответ
            return await self._process_response(response, user_id, tokens_used)

        except Exception as e:
            logger.error(f"Ошибка при обработке через Claude: {e}", exc_info=True)
            return {
                "action": "executed",
                "action_type": "error",
                "response_text": f"❌ Произошла ошибка: {str(e)}",
                "tokens_used": 0
            }

    async def _process_response(
        self,
        response,
        user_id: str,
        tokens_used: int
    ) -> Dict[str, Any]:
        """
        Обрабатывает ответ от Claude

        Args:
            response: Ответ от Claude API
            user_id: ID пользователя
            tokens_used: Количество использованных токенов

        Returns:
            Результат обработки
        """
        # Если Claude хочет использовать инструменты
        if response.stop_reason == "tool_use":
            return await self._handle_tool_use(response, user_id, tokens_used)

        # Если Claude просто ответил текстом
        elif response.stop_reason == "end_turn":
            # Извлечь текстовый ответ
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content += block.text

            return {
                "action": "executed",
                "action_type": "general",
                "response_text": text_content,
                "tokens_used": tokens_used
            }

        else:
            logger.warning(f"Неожиданный stop_reason: {response.stop_reason}")
            return {
                "action": "executed",
                "action_type": "unknown",
                "response_text": "Получен ответ от ассистента",
                "tokens_used": tokens_used
            }

    async def _handle_tool_use(
        self,
        response,
        user_id: str,
        tokens_used: int
    ) -> Dict[str, Any]:
        """
        Обрабатывает использование инструментов Claude

        Args:
            response: Ответ от Claude с tool_use
            user_id: ID пользователя
            tokens_used: Количество использованных токенов

        Returns:
            Результат с запросом на подтверждение
        """
        # Извлечь все tool_use блоки
        tool_uses = [block for block in response.content if block.type == "tool_use"]

        if not tool_uses:
            return {
                "action": "executed",
                "action_type": "no_tools",
                "response_text": "Не удалось определить действие",
                "tokens_used": tokens_used
            }

        # Пока обрабатываем только первый инструмент
        tool_use = tool_uses[0]
        tool_name = tool_use.name
        tool_input = tool_use.input

        logger.info(f"Claude хочет использовать инструмент: {tool_name}")
        logger.debug(f"Параметры: {tool_input}")

        # Проверить, требует ли действие подтверждения
        requires_confirmation = self._requires_confirmation(tool_name)

        if requires_confirmation:
            # Создать запрос на подтверждение
            confirmation_id = str(uuid.uuid4())
            confirmation_text = self._generate_confirmation_text(tool_name, tool_input)

            return {
                "action": "confirm",
                "action_type": tool_name,
                "confirmation_id": confirmation_id,
                "confirmation_text": confirmation_text,
                "response_text": "",  # Будет заполнено после подтверждения
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tokens_used": tokens_used
            }
        else:
            # Выполнить действие сразу
            result = await self._execute_tool(tool_name, tool_input, user_id)

            return {
                "action": "executed",
                "action_type": tool_name,
                "response_text": result["message"],
                "tokens_used": tokens_used
            }

    def _requires_confirmation(self, tool_name: str) -> bool:
        """
        Проверяет, требует ли инструмент подтверждения

        Args:
            tool_name: Название инструмента

        Returns:
            True если требуется подтверждение
        """
        # Действия, требующие подтверждения
        confirmation_required = [
            "add_calendar_event",
            "add_task",
            "add_shopping_item",
            "create_note"
        ]

        return tool_name in confirmation_required

    def _generate_confirmation_text(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Генерирует текст запроса на подтверждение

        Args:
            tool_name: Название инструмента
            tool_input: Параметры инструмента

        Returns:
            Текст для подтверждения
        """
        if tool_name == "add_calendar_event":
            summary = tool_input.get("summary", "событие")
            start_time = tool_input.get("start_time", "")

            # Преобразовать ISO время в читаемый формат
            try:
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%d %B в %H:%M")
            except:
                formatted_time = start_time

            return f"📅 Правильно ли я понял: добавить событие '{summary}' на {formatted_time}?"

        elif tool_name == "add_task":
            title = tool_input.get("title", "задачу")
            return f"✅ Правильно ли я понял: добавить задачу '{title}'?"

        elif tool_name == "add_shopping_item":
            items = tool_input.get("items", [])
            items_str = ", ".join(items)
            return f"🛒 Правильно ли я понял: добавить в покупки: {items_str}?"

        elif tool_name == "create_note":
            title = tool_input.get("title", "заметку")
            return f"📝 Правильно ли я понял: создать заметку '{title}'?"

        else:
            return f"Правильно ли я понял: выполнить действие {tool_name}?"

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Выполняет инструмент

        Args:
            tool_name: Название инструмента
            tool_input: Параметры
            user_id: ID пользователя

        Returns:
            Результат выполнения с полем "message"
        """
        logger.info(f"Выполнение инструмента: {tool_name}")

        try:
            # Импорты интеграций
            from integrations.google_calendar import get_calendar
            from integrations.google_tasks import get_tasks as get_tasks_client
            from integrations.obsidian import get_vault

            if tool_name == "add_calendar_event":
                # Интеграция с Google Calendar
                calendar = get_calendar()
                result = calendar.add_event(
                    summary=tool_input.get('summary'),
                    start_time=tool_input.get('start_time'),
                    end_time=tool_input.get('end_time'),
                    description=tool_input.get('description'),
                    location=tool_input.get('location')
                )
                return {
                    "success": True,
                    "message": f"✅ Событие '{tool_input.get('summary')}' добавлено в календарь"
                }

            elif tool_name == "get_calendar_events":
                # Интеграция с Google Calendar
                calendar = get_calendar()
                events = calendar.get_events(
                    time_min=tool_input.get('time_min'),
                    time_max=tool_input.get('time_max'),
                    max_results=tool_input.get('max_results', 10)
                )

                if not events:
                    return {
                        "success": True,
                        "message": "📅 События не найдены"
                    }

                # Форматировать события для ответа
                events_text = []
                for event in events:
                    start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                    events_text.append(f"• {event['summary']} ({start.strftime('%d.%m в %H:%M')})")

                return {
                    "success": True,
                    "message": f"📅 Найдено событий: {len(events)}\n" + "\n".join(events_text)
                }

            elif tool_name == "add_task":
                # Интеграция с Google Tasks
                tasks = get_tasks_client()
                result = tasks.add_task(
                    title=tool_input.get('title'),
                    notes=tool_input.get('notes'),
                    due_date=tool_input.get('due_date')
                )
                return {
                    "success": True,
                    "message": f"✅ Задача '{tool_input.get('title')}' добавлена"
                }

            elif tool_name == "add_shopping_item":
                # Интеграция с Google Tasks
                tasks = get_tasks_client()
                items = tool_input.get("items", [])
                result = tasks.add_shopping_items(items)
                return {
                    "success": True,
                    "message": f"🛒 Добавлено в покупки: {', '.join(items)}"
                }

            elif tool_name == "get_tasks":
                # Интеграция с Google Tasks
                tasks_client = get_tasks_client()
                task_list = tool_input.get('task_list', 'tasks')
                show_completed = tool_input.get('show_completed', False)

                if task_list == 'shopping':
                    task_list_items = tasks_client.get_shopping_list(show_completed)
                else:
                    task_list_items = tasks_client.get_tasks(show_completed=show_completed)

                if not task_list_items:
                    return {
                        "success": True,
                        "message": "📋 Задачи не найдены"
                    }

                # Форматировать задачи
                tasks_text = []
                for task in task_list_items:
                    status_icon = "✅" if task['status'] == 'completed' else "⬜"
                    tasks_text.append(f"{status_icon} {task['title']}")

                return {
                    "success": True,
                    "message": f"📋 Найдено задач: {len(task_list_items)}\n" + "\n".join(tasks_text[:10])
                }

            elif tool_name == "create_note":
                # Интеграция с Obsidian
                vault = get_vault()
                result = vault.create_note(
                    title=tool_input.get('title'),
                    content=tool_input.get('content'),
                    tags=tool_input.get('tags')
                )
                return {
                    "success": True,
                    "message": f"📝 Заметка '{tool_input.get('title')}' создана в Obsidian"
                }

            elif tool_name == "search_notes":
                # Интеграция с Obsidian
                vault = get_vault()
                results = vault.search_notes(
                    query=tool_input.get('query'),
                    limit=tool_input.get('limit', 5)
                )

                if not results:
                    return {
                        "success": True,
                        "message": f"🔍 Заметки по запросу '{tool_input.get('query')}' не найдены"
                    }

                # Форматировать результаты
                notes_text = []
                for note in results:
                    notes_text.append(f"• {note['title']}")

                return {
                    "success": True,
                    "message": f"🔍 Найдено заметок: {len(results)}\n" + "\n".join(notes_text)
                }

            else:
                return {
                    "success": False,
                    "message": f"❌ Неизвестный инструмент: {tool_name}"
                }

        except Exception as e:
            logger.error(f"Ошибка при выполнении инструмента {tool_name}: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"❌ Ошибка при выполнении действия: {str(e)}"
            }

    async def execute_confirmed_action(
        self,
        confirmation_data: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Выполняет действие после подтверждения пользователем

        Args:
            confirmation_data: Данные подтверждения (из БД)
            user_id: ID пользователя

        Returns:
            Результат выполнения
        """
        action_data = json.loads(confirmation_data['action_data'])

        tool_name = action_data.get('tool_name')
        tool_input = action_data.get('tool_input')

        if not tool_name or not tool_input:
            return {
                "success": False,
                "message": "❌ Некорректные данные подтверждения"
            }

        # Выполнить инструмент
        result = await self._execute_tool(tool_name, tool_input, user_id)

        return result
```

*[Продолжение в следующей части из-за ограничения длины...]*

---

## Заключение

Этот документ содержит полное описание проекта AI-ассистент v2.1, включая:

- Архитектуру системы
- Все компоненты и их взаимодействие
- Полную структуру файлов
- Схему базы данных
- API Reference
- Конфигурацию
- Инструкции по развёртыванию
- **NEW:** Гибридную LLM архитектуру (Claude + Ollama)
- **NEW:** Систему персистентной памяти

**Статус проекта:** Production Ready ✅

**Основные возможности v1.0:**
- ✅ Голосовой ассистент "Зиночка" с wake word активацией
- ✅ Абстракция LLM провайдеров - легко переключаться между Claude API и Ollama
- ✅ Персистентная память - ассистент изучает паттерны пользователя
- ✅ Улучшенная экономия - Ollama для простых запросов (бесплатно)
- ✅ Лучшее качество - контекстно-зависимые ответы
- ✅ Голосовые подтверждения действий

**Контакты:**
- GitHub: [ссылка на репозиторий]
- Email: support@example.com

---

*Документация обновлена: 2026-01-13*
*Версия: 1.0*
*Статус: Готов к первому запуску и тестированию*
