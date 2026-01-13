# Техническое задание: Персональный AI-ассистент v2.0
## С голосовой активацией через Tasker + AutoVoice

## Обзор проекта

Создать персонального AI-ассистента с двумя интерфейсами:
1. **Telegram бот** - для использования с компьютера и текстовых команд
2. **REST API + Tasker** - для голосовой активации без открытия приложений

Пользователь может сказать "Привет, Ассистент" и телефон в фоне активируется, записывает команду, выполняет её и озвучивает результат.

## Целевая аудитория

Один пользователь с Android-телефоном.

## Технические требования

### Стек технологий

- **Язык:** Python 3.11+
- **Фреймворки:**
  - `python-telegram-bot` (v20+) для Telegram бота
  - `fastapi` для REST API
  - `anthropic` SDK для Claude API
  - Google API клиенты для Calendar и Tasks
  - `openai` для Whisper API (распознавание речи)
  - `gtts` или Google Cloud TTS для озвучивания
- **Развертывание:** VPS (Ubuntu/Debian)
- **База данных:** SQLite
- **Веб-сервер:** Uvicorn (для FastAPI)
- **Reverse Proxy:** Nginx (для HTTPS)

### Архитектура

```
Пользователь
    ↓
┌───┴───┐
│       │
Telegram    Android + Tasker/AutoVoice
│           │
│           ↓
│       REST API (/voice-command)
│           │
└─────┬─────┘
      ↓
  Claude Agent (общий)
      ↓
  ┌───┴───┬────────┬──────────┐
  ↓       ↓        ↓          ↓
Google  Google  Obsidian   Другие
Calendar Tasks   Sync     (будущее)
```

## Функциональные требования

### 1. Telegram Bot (без изменений)

См. предыдущее ТЗ - всё остаётся как было.

### 2. REST API (НОВОЕ)

#### 2.1 Эндпоинты

**POST /api/v1/voice-command**
```json
Запрос:
- Content-Type: multipart/form-data
- audio: файл (.ogg, .mp3, .wav, .m4a)
- user_id: string (для авторизации)

Ответ:
{
  "status": "success",
  "action": "confirm",  // или "executed"
  "confirmation_text": "Правильно ли я понял: добавить встречу...",
  "response_text": "Встреча добавлена в календарь",
  "audio_url": "https://your-server.com/api/v1/tts/abc123.mp3"
}
```

**POST /api/v1/text-command**
```json
Запрос:
{
  "text": "Запиши на завтра в 15:00 встречу с врачом",
  "user_id": "string",
  "context_id": "optional_conversation_id"
}

Ответ:
{
  "status": "success",
  "action": "confirm",
  "confirmation_text": "...",
  "response_text": "...",
  "audio_url": "..."
}
```

**POST /api/v1/confirm**
```json
Запрос:
{
  "confirmation_id": "abc123",
  "confirmed": true,  // true = да, false = нет
  "user_id": "string"
}

Ответ:
{
  "status": "success",
  "response_text": "✅ Встреча добавлена в календарь",
  "audio_url": "..."
}
```

**GET /api/v1/tts/{filename}**
- Отдаёт аудио-файл с озвученным текстом
- Кэширование: 24 часа

**GET /api/v1/health**
- Проверка работоспособности сервера
- Возвращает: `{"status": "ok", "version": "2.0"}`

#### 2.2 Авторизация

Простая авторизация по токену:
- В `config.yaml` задан `api_token`
- Каждый запрос должен содержать заголовок: `Authorization: Bearer YOUR_API_TOKEN`
- Если токен неверный → 401 Unauthorized

#### 2.3 Обработка голоса

**Whisper API (OpenAI):**
```python
import openai

def transcribe_audio(audio_file_path: str) -> str:
    """Распознаёт речь в текст через Whisper API"""
    with open(audio_file_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe(
            model="whisper-1",
            file=audio_file,
            language="ru"  # Русский язык
        )
    return transcript.text
```

**Стоимость:** ~$0.006 за минуту аудио (очень дешево)

#### 2.4 Text-to-Speech

**Вариант 1: gTTS (бесплатно, простой):**
```python
from gtts import gTTS

def text_to_speech(text: str, output_path: str):
    """Конвертирует текст в аудио"""
    tts = gTTS(text=text, lang='ru', slow=False)
    tts.save(output_path)
```

**Вариант 2: Google Cloud TTS (платно, качественнее):**
- Более естественный голос
- Стоимость: ~$4 за 1 млн символов (очень дешево)

**Рекомендация:** начать с gTTS, потом можно переключить на Google Cloud TTS.

#### 2.5 Кэширование аудио

- Все TTS файлы сохраняются в `data/tts_cache/`
- Имя файла: `md5(text).mp3`
- Если текст уже озвучивался → берём из кэша
- Автоочистка файлов старше 7 дней

### 3. Интеграция Tasker + AutoVoice

#### 3.1 Принцип работы

```
1. AutoVoice слушает в фоне
2. Пользователь говорит: "Привет, Ассистент"
3. AutoVoice распознаёт → активирует Tasker профиль
4. Tasker включает микрофон, записывает команду
5. Tasker отправляет аудио на REST API
6. Получает ответ (текст + аудио URL)
7. Если нужно подтверждение → показывает диалог
8. Если подтверждено → отправляет /confirm
9. Озвучивает итоговый ответ через TTS
```

#### 3.2 Готовый Tasker профиль (для импорта)

Создать XML файл профиля Tasker: `tasker_profile_ai_assistant.xml`

**Профиль содержит:**

1. **Профиль "AI Assistant Hotword"**
   - Trigger: AutoVoice Recognized
   - Hotword: "привет ассистент"
   - Task: "Record and Send Command"

2. **Task "Record and Send Command"**
   ```
   A1: Say [ Text:Слушаю ]
   A2: Record Audio [ File:voice_command.m4a Duration:10 ]
   A3: HTTP Request [
       Method: POST
       URL: https://YOUR_SERVER/api/v1/voice-command
       Headers: Authorization: Bearer YOUR_TOKEN
       File: voice_command.m4a
       Output: %response
   ]
   A4: Parse JSON [ %response → %action, %confirmation_text, %audio_url ]
   A5: If [ %action = "confirm" ]
       A6: Show Dialog [ %confirmation_text, Buttons: Да|Нет ]
       A7: If [ %button = "Да" ]
           A8: HTTP POST /api/v1/confirm
           A9: Parse response → %final_response, %final_audio_url
       A10: End If
   A11: Else
       A12: Set %final_response = %response_text
       A13: Set %final_audio_url = %audio_url
   A14: End If
   A15: Download Audio [ %final_audio_url → response.mp3 ]
   A16: Play Audio [ response.mp3 ]
   ```

3. **Профиль "AI Assistant Widget"**
   - Trigger: Widget Tap
   - Task: "Record and Send Command" (тот же)

4. **Профиль "AI Assistant Headphones"**
   - Trigger: Long Press Media Button
   - Task: "Record and Send Command"

### 4. Структура проекта (ОБНОВЛЁННАЯ)

```
ai-assistant/
├── README.md
├── requirements.txt
├── .env.example
├── config.yaml.example
├── main.py                    # Точка входа (Telegram + API)
├── bot/
│   ├── __init__.py
│   ├── telegram_bot.py
│   ├── voice_handler.py
│   └── message_handler.py
├── api/                       # ← НОВОЕ
│   ├── __init__.py
│   ├── app.py                 # FastAPI приложение
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── voice.py           # /voice-command
│   │   ├── text.py            # /text-command
│   │   ├── confirm.py         # /confirm
│   │   └── tts.py             # /tts/{filename}
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── auth.py            # Авторизация по токену
│   └── models.py              # Pydantic модели для запросов/ответов
├── agent/
│   ├── __init__.py
│   ├── claude_agent.py
│   └── tools.py
├── integrations/
│   ├── __init__.py
│   ├── google_calendar.py
│   ├── google_tasks.py
│   ├── obsidian.py
│   ├── whisper.py             # ← НОВОЕ: Whisper API
│   └── tts.py                 # ← НОВОЕ: Text-to-Speech
├── utils/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── logger.py
│   └── cache.py               # ← НОВОЕ: Кэширование TTS
├── credentials/
│   └── .gitkeep
├── data/
│   ├── assistant.db
│   └── tts_cache/             # ← НОВОЕ: Кэш аудио-файлов
├── tasker/                    # ← НОВОЕ
│   ├── tasker_profile.xml     # Готовый профиль для импорта
│   └── setup_guide.md         # Инструкция по настройке
├── nginx/                     # ← НОВОЕ
│   └── ai_assistant.conf      # Конфиг Nginx для HTTPS
└── docs/
    ├── setup.md
    ├── deployment.md
    ├── usage.md
    └── tasker_setup.md        # ← НОВОЕ: Настройка Tasker
```

### 5. Реализация REST API

#### 5.1 api/app.py

```python
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.middleware.auth import verify_token
from api.routes import voice, text, confirm, tts
from utils.logger import setup_logger

logger = setup_logger()

app = FastAPI(
    title="AI Assistant API",
    version="2.0",
    description="REST API для персонального AI-ассистента"
)

# CORS (если нужно для веб-интерфейса в будущем)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутов
app.include_router(voice.router, prefix="/api/v1", tags=["voice"])
app.include_router(text.router, prefix="/api/v1", tags=["text"])
app.include_router(confirm.router, prefix="/api/v1", tags=["confirm"])
app.include_router(tts.router, prefix="/api/v1", tags=["tts"])

@app.get("/api/v1/health")
async def health_check():
    """Проверка работоспособности"""
    return {"status": "ok", "version": "2.0"}

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
```

#### 5.2 api/routes/voice.py

```python
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from api.middleware.auth import verify_token
from integrations.whisper import transcribe_audio
from integrations.tts import text_to_speech
from agent.claude_agent import ClaudeAgent
from utils.cache import get_or_create_tts
import uuid
import os

router = APIRouter()

@router.post("/voice-command")
async def voice_command(
    audio: UploadFile = File(...),
    user_id: str = Depends(verify_token)
):
    """
    Обрабатывает голосовую команду
    
    1. Сохраняет аудио во временный файл
    2. Распознаёт через Whisper
    3. Обрабатывает через Claude Agent
    4. Генерирует TTS ответ
    5. Возвращает результат
    """
    
    # Сохранить временный файл
    temp_path = f"/tmp/{uuid.uuid4()}.{audio.filename.split('.')[-1]}"
    with open(temp_path, "wb") as f:
        f.write(await audio.read())
    
    try:
        # 1. Распознать речь
        text = transcribe_audio(temp_path)
        logger.info(f"Распознано: {text}")
        
        # 2. Обработать через Claude
        agent = ClaudeAgent()
        result = await agent.process_message(text, user_id=user_id)
        
        # 3. Сгенерировать TTS
        if result["action"] == "confirm":
            tts_text = result["confirmation_text"]
        else:
            tts_text = result["response_text"]
        
        audio_url = get_or_create_tts(tts_text)
        
        # 4. Вернуть результат
        return {
            "status": "success",
            "action": result["action"],
            "confirmation_text": result.get("confirmation_text"),
            "response_text": result.get("response_text"),
            "audio_url": audio_url,
            "confirmation_id": result.get("confirmation_id")
        }
        
    except Exception as e:
        logger.error(f"Ошибка обработки команды: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Удалить временный файл
        if os.path.exists(temp_path):
            os.remove(temp_path)
```

#### 5.3 api/middleware/auth.py

```python
from fastapi import Header, HTTPException
from utils.config import load_config

config = load_config()

async def verify_token(authorization: str = Header(...)):
    """
    Проверяет Bearer токен
    
    Формат: Authorization: Bearer YOUR_TOKEN
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    
    if token != config["api"]["token"]:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token  # Можно вернуть user_id, если нужно
```

#### 5.4 integrations/whisper.py

```python
import openai
from utils.config import load_config

config = load_config()
openai.api_key = config["openai"]["api_key"]

def transcribe_audio(audio_file_path: str) -> str:
    """
    Распознаёт речь в текст через Whisper API
    
    Args:
        audio_file_path: Путь к аудио-файлу
        
    Returns:
        Распознанный текст
    """
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language="ru"  # Русский язык
            )
        return transcript.text.strip()
    
    except Exception as e:
        logger.error(f"Ошибка Whisper API: {e}")
        raise
```

#### 5.5 integrations/tts.py

```python
from gtts import gTTS
import hashlib
import os
from utils.logger import setup_logger

logger = setup_logger()

TTS_CACHE_DIR = "data/tts_cache"

def text_to_speech(text: str, output_path: str) -> str:
    """
    Конвертирует текст в аудио (русский язык)
    
    Args:
        text: Текст для озвучивания
        output_path: Путь для сохранения MP3
        
    Returns:
        Путь к сохранённому файлу
    """
    try:
        tts = gTTS(text=text, lang='ru', slow=False)
        tts.save(output_path)
        logger.info(f"TTS сгенерирован: {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Ошибка TTS: {e}")
        raise

def get_tts_filename(text: str) -> str:
    """Генерирует имя файла на основе хэша текста"""
    text_hash = hashlib.md5(text.encode()).hexdigest()
    return f"{text_hash}.mp3"
```

#### 5.6 utils/cache.py

```python
import os
from integrations.tts import text_to_speech, get_tts_filename, TTS_CACHE_DIR

def get_or_create_tts(text: str) -> str:
    """
    Получает URL озвученного текста (из кэша или создаёт новый)
    
    Args:
        text: Текст для озвучивания
        
    Returns:
        URL для скачивания аудио
    """
    # Создать папку кэша, если не существует
    os.makedirs(TTS_CACHE_DIR, exist_ok=True)
    
    # Получить имя файла
    filename = get_tts_filename(text)
    file_path = os.path.join(TTS_CACHE_DIR, filename)
    
    # Если файл не существует → создать
    if not os.path.exists(file_path):
        text_to_speech(text, file_path)
    
    # Вернуть URL
    return f"https://YOUR_SERVER/api/v1/tts/{filename}"

def cleanup_old_tts_files(days: int = 7):
    """Удаляет TTS файлы старше N дней"""
    import time
    
    current_time = time.time()
    
    for filename in os.listdir(TTS_CACHE_DIR):
        file_path = os.path.join(TTS_CACHE_DIR, filename)
        file_age = current_time - os.path.getmtime(file_path)
        
        # Если файл старше N дней → удалить
        if file_age > (days * 86400):
            os.remove(file_path)
            logger.info(f"Удалён старый TTS файл: {filename}")
```

#### 5.7 api/routes/tts.py

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from integrations.tts import TTS_CACHE_DIR

router = APIRouter()

@router.get("/tts/{filename}")
async def get_tts_file(filename: str):
    """
    Отдаёт аудио-файл с озвученным текстом
    
    Args:
        filename: Имя файла (md5_hash.mp3)
    """
    file_path = os.path.join(TTS_CACHE_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "public, max-age=86400"  # Кэш на 24 часа
        }
    )
```

### 6. Конфигурация (ОБНОВЛЁННАЯ)

#### 6.1 config.yaml

```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"
  allowed_users: [123456789]

api:  # ← НОВОЕ
  token: "YOUR_API_TOKEN_GENERATE_RANDOM"  # Для авторизации Tasker
  host: "0.0.0.0"
  port: 8000
  base_url: "https://your-server.com"  # Для генерации URL

claude:
  api_key: "YOUR_CLAUDE_API_KEY"
  model: "claude-sonnet-4-20250514"

openai:  # ← НОВОЕ
  api_key: "YOUR_OPENAI_API_KEY"  # Для Whisper

google:
  calendar:
    credentials_file: "credentials/google_calendar_credentials.json"
    token_file: "credentials/google_calendar_token.json"
  tasks:
    credentials_file: "credentials/google_tasks_credentials.json"
    token_file: "credentials/google_tasks_token.json"
    task_list_id: "YOUR_TASK_LIST_ID"
    shopping_list_id: "YOUR_SHOPPING_LIST_ID"

obsidian:
  method: "filesystem"
  vault_path: "/path/to/obsidian/vault"

tts:  # ← НОВОЕ
  provider: "gtts"  # или "google_cloud"
  cache_dir: "data/tts_cache"
  cache_days: 7  # Хранить файлы 7 дней

database:
  path: "data/assistant.db"

logging:
  level: "INFO"
  file: "logs/assistant.log"
```

#### 6.2 .env

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# API
API_TOKEN=generate_random_token_here

# Claude
CLAUDE_API_KEY=your_claude_api_key

# OpenAI (для Whisper)
OPENAI_API_KEY=your_openai_api_key

# Google Cloud (опционально, для TTS)
GOOGLE_APPLICATION_CREDENTIALS=credentials/google_cloud.json
```

### 7. Запуск обоих сервисов

#### 7.1 main.py (ОБНОВЛЁННЫЙ)

```python
import asyncio
import multiprocessing
from bot.telegram_bot import TelegramBot
from api.app import app
from utils.config import load_config
from utils.logger import setup_logger
import uvicorn

logger = setup_logger()

def run_telegram_bot():
    """Запускает Telegram бота"""
    config = load_config()
    bot = TelegramBot(config)
    asyncio.run(bot.start())

def run_api_server():
    """Запускает REST API сервер"""
    config = load_config()
    uvicorn.run(
        "api.app:app",
        host=config["api"]["host"],
        port=config["api"]["port"],
        reload=False,
        log_level="info"
    )

def main():
    """Запускает оба сервиса параллельно"""
    
    # Создать процессы
    telegram_process = multiprocessing.Process(target=run_telegram_bot)
    api_process = multiprocessing.Process(target=run_api_server)
    
    # Запустить
    telegram_process.start()
    api_process.start()
    
    logger.info("🚀 Telegram Bot и REST API запущены")
    
    # Ждать завершения
    telegram_process.join()
    api_process.join()

if __name__ == "__main__":
    main()
```

### 8. Nginx конфигурация (для HTTPS)

#### 8.1 nginx/ai_assistant.conf

```nginx
server {
    listen 80;
    server_name your-server.com;
    
    # Редирект на HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-server.com;
    
    # SSL сертификаты (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-server.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-server.com/privkey.pem;
    
    # Проксирование на FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Увеличить таймауты для Whisper
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
    
    # Максимальный размер загружаемого файла (для аудио)
    client_max_body_size 10M;
}
```

### 9. Инструкция по настройке Tasker (docs/tasker_setup.md)

```markdown
# Настройка Tasker + AutoVoice для AI-ассистента

## Шаг 1: Установка приложений

1. Купите и установите **Tasker** ($3.49) из Google Play
2. Купите и установите **AutoVoice** ($2.99) из Google Play

## Шаг 2: Настройка AutoVoice

### 2.1 Первый запуск

1. Откройте AutoVoice
2. Разрешите доступ к микрофону
3. Включите "Continuous" режим (постоянное прослушивание)

### 2.2 Создание Hotword

1. В AutoVoice → вкладка "Continuous"
2. Нажмите "+" для добавления команды
3. Введите: **привет ассистент**
4. Выберите язык: **Russian**
5. Нажмите "Save"

### 2.3 Тестирование

1. Скажите: "Привет, Ассистент"
2. AutoVoice должен показать уведомление о распознавании

## Шаг 3: Импорт готового профиля в Tasker

### 3.1 Скачать профиль

Файл `tasker_profile_ai_assistant.xml` находится в папке `tasker/`

### 3.2 Импортировать

1. Откройте Tasker
2. Нажмите на иконку "дом" (внизу слева)
3. Нажмите "⋮" (три точки)
4. Выберите "Import" → "Import Project"
5. Выберите файл `tasker_profile_ai_assistant.xml`

### 3.3 Настроить URL и токен

1. В Tasker откройте Task "Record and Send Command"
2. Найдите действие "HTTP Request"
3. Замените:
   - `YOUR_SERVER` → адрес вашего сервера (например, `assistant.example.com`)
   - `YOUR_TOKEN` → ваш API токен из `config.yaml`

```
Пример:
URL: https://assistant.example.com/api/v1/voice-command
Headers: Authorization: Bearer abc123xyz456
```

## Шаг 4: Тестирование

### 4.1 Базовый тест

1. Скажите: **"Привет, Ассистент"**
2. Должен прозвучать звук подтверждения
3. Скажите команду: **"Что у меня завтра?"**
4. Дождитесь ответа

### 4.2 Тест с подтверждением

1. Скажите: **"Привет, Ассистент"**
2. Скажите: **"Запиши на завтра в 15:00 встречу с врачом"**
3. Появится диалог: "Правильно ли я понял..."
4. Нажмите "Да"
5. Услышите: "Встреча добавлена в календарь"

## Шаг 5: Настройка разрешений Android

### 5.1 Отключить оптимизацию батареи

Для стабильной работы в фоне:

1. Настройки → Батарея → Оптимизация батареи
2. Найдите: Tasker, AutoVoice
3. Отключите оптимизацию для обоих приложений

### 5.2 Разрешить работу в фоне

1. Настройки → Приложения → Tasker
2. Разрешения → включите "Микрофон", "Запись аудио"
3. Также для AutoVoice

### 5.3 Автозапуск

1. Настройки → Приложения → Tasker → Автозапуск: ВКЛ
2. То же для AutoVoice

## Шаг 6: Создание виджета (опционально)

Для быстрого доступа с главного экрана:

1. Долгий тап на главном экране
2. Виджеты → Tasker → Task Shortcut
3. Выберите Task: "Record and Send Command"
4. Выберите иконку (например, микрофон)
5. Разместите на главном экране

Теперь можно тапнуть по виджету → сразу записать команду.

## Шаг 7: Активация через кнопку наушников (опционально)

Для использования с Bluetooth наушниками:

1. В Tasker создайте новый профиль
2. Event → Hardware → Button → Media Button
3. Выберите: Long Press
4. Привяжите к Task: "Record and Send Command"

Теперь долгое нажатие на кнопку наушников активирует ассистента.

## Траблшутинг

### Проблема: AutoVoice не распознаёт hotword

**Решение:**
1. Убедитесь, что "Continuous" включен
2. Проверьте настройки микрофона в Android
3. Попробуйте записать hotword заново

### Проблема: Tasker не отправляет запрос

**Решение:**
1. Проверьте URL и токен в HTTP Request
2. Убедитесь, что сервер доступен (откройте в браузере)
3. Проверьте логи Tasker: Run Log

### Проблема: Батарея быстро садится

**Решение:**
1. В AutoVoice → Settings → уменьшите частоту прослушивания
2. Используйте режим "Screen On Only" (только при включенном экране)

### Проблема: Не работает с заблокированным экраном

**Решение:**
1. Настройки → Безопасность → Smart Lock → добавьте доверенные устройства
2. Или отключите блокировку экрана (небезопасно)

## Дополнительные настройки

### Изменить кодовую фразу

1. AutoVoice → Continuous → найдите команду
2. Измените на любую фразу (например, "Окей, Ассистент")

### Настроить голос подтверждения

1. В Task найдите действие "Say"
2. Измените текст и настройки голоса

### Добавить вибрацию при активации

1. В Task после "Say" добавьте действие "Vibrate"
2. Установите длительность (например, 200ms)

---

## Готово! 🎉

Теперь ваш AI-ассистент активируется голосом в фоне.

**Примеры команд:**
- "Привет, Ассистент" → "Запиши на завтра в 15:00 встречу"
- "Привет, Ассистент" → "Что у меня на этой неделе?"
- "Привет, Ассистент" → "Добавь в покупки молоко и хлеб"
```

### 10. Готовый Tasker профиль (XML)

Файл: `tasker/tasker_profile_ai_assistant.xml`

```xml
<TaskerData sr="" dvi="1" tv="6.2.22">
    <Profile sr="prof1" ve="2">
        <cdate>1704729600000</cdate>
        <edate>1704729600000</edate>
        <flags>8</flags>
        <id>1</id>
        <mid0>2</mid0>
        <name>AI Assistant Hotword</name>
        <Event sr="con0" ve="2">
            <code>1519899750</code>
            <pri>0</pri>
            <Bundle sr="arg0">
                <Vals sr="val">
                    <com.joaomgcd.autovoice.intent.IntentReceiveCommand-com.twofortyfouram.locale.intent.extra.BLURB>привет ассистент</com.joaomgcd.autovoice.intent.IntentReceiveCommand-com.twofortyfouram.locale.intent.extra.BLURB>
                </Vals>
            </Bundle>
        </Event>
    </Profile>
    
    <Task sr="task2">
        <cdate>1704729600000</cdate>
        <edate>1704729600000</edate>
        <id>2</id>
        <name>Record and Send Command</name>
        
        <!-- A1: Say "Слушаю" -->
        <Action sr="act0" ve="7">
            <code>547</code>
            <Str sr="arg0" ve="3">Слушаю</Str>
            <Int sr="arg1" val="5"/>
        </Action>
        
        <!-- A2: Record Audio -->
        <Action sr="act1" ve="7">
            <code>362</code>
            <Str sr="arg0" ve="3">voice_command.m4a</Str>
            <Int sr="arg1" val="0"/>
            <Int sr="arg2" val="10"/>
        </Action>
        
        <!-- A3: HTTP Request -->
        <Action sr="act2" ve="7">
            <code>339</code>
            <Bundle sr="arg0">
                <Vals sr="val">
                    <net.dinglisch.android.tasker.EXTRA_HTTP_URL>https://YOUR_SERVER/api/v1/voice-command</net.dinglisch.android.tasker.EXTRA_HTTP_URL>
                    <net.dinglisch.android.tasker.EXTRA_HTTP_METHOD>POST</net.dinglisch.android.tasker.EXTRA_HTTP_METHOD>
                    <net.dinglisch.android.tasker.EXTRA_HTTP_HEADERS>Authorization: Bearer YOUR_TOKEN</net.dinglisch.android.tasker.EXTRA_HTTP_HEADERS>
                    <net.dinglisch.android.tasker.EXTRA_HTTP_FILE>voice_command.m4a</net.dinglisch.android.tasker.EXTRA_HTTP_FILE>
                </Vals>
            </Bundle>
            <Str sr="arg1" ve="3">%response</Str>
        </Action>
        
        <!-- A4: JavaScriptlet - Parse JSON -->
        <Action sr="act3" ve="7">
            <code>378</code>
            <Str sr="arg0" ve="3">
                var data = JSON.parse(%response);
                setGlobal("action", data.action);
                setGlobal("confirmation_text", data.confirmation_text || "");
                setGlobal("response_text", data.response_text || "");
                setGlobal("audio_url", data.audio_url);
                setGlobal("confirmation_id", data.confirmation_id || "");
            </Str>
        </Action>
        
        <!-- A5: If action = "confirm" -->
        <Action sr="act4" ve="7">
            <code>37</code>
            <ConditionList sr="if">
                <Condition sr="c0" ve="3">
                    <lhs>%global("action")</lhs>
                    <op>2</op>
                    <rhs>confirm</rhs>
                </Condition>
            </ConditionList>
        </Action>
        
        <!-- A6: Show Dialog -->
        <Action sr="act5" ve="7">
            <code>524</code>
            <Str sr="arg0" ve="3">%global("confirmation_text")</Str>
            <Str sr="arg1" ve="3">Да|Нет</Str>
        </Action>
        
        <!-- A7: If button = "Да" -->
        <Action sr="act6" ve="7">
            <code>37</code>
            <ConditionList sr="if">
                <Condition sr="c0" ve="3">
                    <lhs>%global("button")</lhs>
                    <op>2</op>
                    <rhs>Да</rhs>
                </Condition>
            </ConditionList>
        </Action>
        
        <!-- A8: HTTP POST /confirm -->
        <Action sr="act7" ve="7">
            <code>339</code>
            <Bundle sr="arg0">
                <Vals sr="val">
                    <net.dinglisch.android.tasker.EXTRA_HTTP_URL>https://YOUR_SERVER/api/v1/confirm</net.dinglisch.android.tasker.EXTRA_HTTP_URL>
                    <net.dinglisch.android.tasker.EXTRA_HTTP_METHOD>POST</net.dinglisch.android.tasker.EXTRA_HTTP_METHOD>
                    <net.dinglisch.android.tasker.EXTRA_HTTP_HEADERS>Authorization: Bearer YOUR_TOKEN
Content-Type: application/json</net.dinglisch.android.tasker.EXTRA_HTTP_HEADERS>
                    <net.dinglisch.android.tasker.EXTRA_HTTP_DATA>{"confirmation_id":"%global(confirmation_id)","confirmed":true}</net.dinglisch.android.tasker.EXTRA_HTTP_DATA>
                </Vals>
            </Bundle>
            <Str sr="arg1" ve="3">%final_response</Str>
        </Action>
        
        <!-- A9: Parse final response -->
        <Action sr="act8" ve="7">
            <code>378</code>
            <Str sr="arg0" ve="3">
                var data = JSON.parse(%final_response);
                setGlobal("final_text", data.response_text);
                setGlobal("final_audio_url", data.audio_url);
            </Str>
        </Action>
        
        <!-- A10: End If (button check) -->
        <Action sr="act9" ve="7">
            <code>43</code>
        </Action>
        
        <!-- A11: Else -->
        <Action sr="act10" ve="7">
            <code>43</code>
        </Action>
        
        <!-- A12: Set final text from first response -->
        <Action sr="act11" ve="7">
            <code>547</code>
            <Str sr="arg0" ve="3">%global("final_text") = %global("response_text")</Str>
        </Action>
        
        <!-- A13: Set final audio URL -->
        <Action sr="act12" ve="7">
            <code>547</code>
            <Str sr="arg0" ve="3">%global("final_audio_url") = %global("audio_url")</Str>
        </Action>
        
        <!-- A14: End If (action check) -->
        <Action sr="act13" ve="7">
            <code>43</code>
        </Action>
        
        <!-- A15: Download Audio -->
        <Action sr="act14" ve="7">
            <code>339</code>
            <Bundle sr="arg0">
                <Vals sr="val">
                    <net.dinglisch.android.tasker.EXTRA_HTTP_URL>%global("final_audio_url")</net.dinglisch.android.tasker.EXTRA_HTTP_URL>
                    <net.dinglisch.android.tasker.EXTRA_HTTP_METHOD>GET</net.dinglisch.android.tasker.EXTRA_HTTP_METHOD>
                    <net.dinglisch.android.tasker.EXTRA_HTTP_OUTPUT_FILE>response.mp3</net.dinglisch.android.tasker.EXTRA_HTTP_OUTPUT_FILE>
                </Vals>
            </Bundle>
        </Action>
        
        <!-- A16: Play Audio -->
        <Action sr="act15" ve="7">
            <code>300</code>
            <Str sr="arg0" ve="3">response.mp3</Str>
        </Action>
    </Task>
</TaskerData>
```

### 11. Requirements.txt (ОБНОВЛЁННЫЙ)

```txt
# Telegram Bot
python-telegram-bot==20.7
telegram==0.0.1

# REST API
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# Claude API
anthropic==0.18.1

# OpenAI (Whisper)
openai==1.12.0

# Google APIs
google-auth==2.27.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
google-api-python-client==2.115.0

# Text-to-Speech
gTTS==2.5.0

# Utilities
pyyaml==6.0.1
python-dotenv==1.0.0
aiofiles==23.2.1
pydantic==2.5.3

# Database
aiosqlite==0.19.0

# Logging
python-json-logger==2.0.7
```

### 12. Этапы разработки (ОБНОВЛЁННЫЕ)

#### Этап 1: Базовая инфраструктура ✓
- [x] Структура проекта
- [x] Конфигурация
- [x] Логирование

#### Этап 2: Telegram Bot ✓
- [x] Базовый бот
- [x] Обработка команд

#### Этап 3: Claude интеграция ✓
- [x] Claude API
- [x] Function Calling

#### Этап 4: REST API (НОВОЕ) ⭐
- [ ] FastAPI приложение
- [ ] Роуты: /voice-command, /text-command, /confirm, /tts
- [ ] Middleware авторизации
- [ ] Обработка аудио-файлов

#### Этап 5: Whisper + TTS (НОВОЕ) ⭐
- [ ] Интеграция Whisper API
- [ ] Интеграция gTTS
- [ ] Кэширование TTS файлов
- [ ] Очистка старых файлов

#### Этап 6: Google Calendar ✓
- [ ] OAuth
- [ ] add_event, get_events

#### Этап 7: Google Tasks ✓
- [ ] OAuth
- [ ] Создание списков
- [ ] add_task, get_tasks

#### Этап 8: Obsidian ✓
- [ ] Filesystem метод
- [ ] create_note
- [ ] Обработка контента

#### Этап 9: Диалоговый flow ✓
- [ ] Система подтверждения
- [ ] Обработка ответов

#### Этап 10: Nginx + HTTPS (НОВОЕ) ⭐
- [ ] Конфиг Nginx
- [ ] Let's Encrypt сертификат
- [ ] Проксирование на FastAPI

#### Этап 11: Tasker профиль (НОВОЕ) ⭐
- [ ] XML профиль для импорта
- [ ] Инструкция по настройке
- [ ] Виджет
- [ ] Активация через наушники

#### Этап 12: Тестирование ✓
- [ ] Юнит-тесты
- [ ] Интеграционные тесты
- [ ] Тест Tasker интеграции

#### Этап 13: Документация ✓
- [ ] README.md
- [ ] setup.md
- [ ] deployment.md
- [ ] tasker_setup.md (новое)

#### Этап 14: Развертывание ✓
- [ ] Инструкция VPS
- [ ] Systemd service (2 сервиса)
- [ ] Финальное тестирование

### 13. Развертывание на VPS (ОБНОВЛЁННОЕ)

#### 13.1 Systemd services

**Файл: /etc/systemd/system/ai-assistant-telegram.service**

```ini
[Unit]
Description=AI Assistant Telegram Bot
After=network.target

[Service]
Type=simple
User=username
WorkingDirectory=/home/username/ai-assistant
ExecStart=/home/username/ai-assistant/venv/bin/python -c "from main import run_telegram_bot; run_telegram_bot()"
Restart=always

[Install]
WantedBy=multi-user.target
```

**Файл: /etc/systemd/system/ai-assistant-api.service**

```ini
[Unit]
Description=AI Assistant REST API
After=network.target

[Service]
Type=simple
User=username
WorkingDirectory=/home/username/ai-assistant
ExecStart=/home/username/ai-assistant/venv/bin/python -c "from main import run_api_server; run_api_server()"
Restart=always

[Install]
WantedBy=multi-user.target
```

**Команды:**

```bash
# Запустить оба сервиса
sudo systemctl start ai-assistant-telegram
sudo systemctl start ai-assistant-api

# Включить автозапуск
sudo systemctl enable ai-assistant-telegram
sudo systemctl enable ai-assistant-api

# Проверить статус
sudo systemctl status ai-assistant-telegram
sudo systemctl status ai-assistant-api

# Просмотр логов
sudo journalctl -u ai-assistant-telegram -f
sudo journalctl -u ai-assistant-api -f
```

#### 13.2 Установка Let's Encrypt

```bash
# Установить Certbot
sudo apt install certbot python3-certbot-nginx

# Получить сертификат
sudo certbot --nginx -d your-server.com

# Автообновление (добавится в cron автоматически)
sudo certbot renew --dry-run
```

### 14. Примеры использования

#### 14.1 Через Tasker (голосом)

```
Пользователь: "Привет, Ассистент"
[звук подтверждения]

Пользователь: "Запиши на завтра в 15:00 встречу с врачом"
[пауза 2 сек]

Телефон: "Правильно ли я понял: добавить встречу с врачом 
          на 9 января в 15:00?"

Пользователь: "Да"

Телефон: "Встреча добавлена в календарь"
```

#### 14.2 Через виджет

```
[Тап по виджету на главном экране]
[Микрофон активируется]

Пользователь: "Что у меня завтра?"

Телефон: "У вас завтра 2 события: встреча с врачом в 15:00
          и ужин с друзьями в 19:00"
```

#### 14.3 Через кнопку наушников

```
[Долгое нажатие кнопки на Bluetooth наушниках]
[Звук в наушниках: бип]

Пользователь: "Добавь в покупки молоко, хлеб, яйца"

Голос в наушниках: "Добавлено 3 товара в список покупок"
```

### 15. Стоимость работы системы

**Ежемесячно:**

- VPS (1GB RAM): $5/мес
- Claude API: ~$3-5/мес (при 100-200 запросов/день)
- OpenAI Whisper: ~$1-2/мес (при 30-60 мин аудио/день)
- gTTS: бесплатно
- **Итого: ~$10-12/мес**

**Разово:**

- Tasker: $3.49
- AutoVoice: $2.99
- **Итого: $6.48**

### 16. Чек-лист для Claude Code

- [ ] Структура проекта создана (с новыми папками api/, tasker/, nginx/)
- [ ] requirements.txt заполнен (добавлены fastapi, openai, gtts)
- [ ] Telegram бот работает ✓
- [ ] **REST API создан (FastAPI)**
- [ ] **Whisper API интегрирован**
- [ ] **gTTS интегрирован**
- [ ] **Кэширование TTS работает**
- [ ] Claude API с Function Calling ✓
- [ ] Google Calendar ✓
- [ ] Google Tasks ✓
- [ ] Obsidian ✓
- [ ] Диалоговый flow ✓
- [ ] **Nginx конфиг создан**
- [ ] **Tasker XML профиль создан**
- [ ] **Инструкция по Tasker написана**
- [ ] Systemd services (2 шт) созданы
- [ ] Документация полная
- [ ] Проект готов к развертыванию

---

## Итого: что получится

### Способы использования:

1. **Telegram бот** - универсальный доступ с любого устройства
2. **Голосовая активация** - "Привет, Ассистент" в фоне (Tasker + AutoVoice)
3. **Виджет** - тап на главном экране → микрофон
4. **Кнопка наушников** - долгое нажатие → команда

### Функции:

- ✅ Google Calendar (добавление/просмотр событий)
- ✅ Google Tasks (задачи + покупки)
- ✅ Obsidian (создание заметок)
- ✅ Голосовое управление (Whisper API)
- ✅ Голосовые ответы (TTS)
- ✅ Работа в фоне без открытия приложений
- ✅ Понимание естественного языка (Claude)
- ✅ Система подтверждения действий
- ✅ Кроссплатформенность (Telegram везде, Tasker на Android)

### Расширяемость:

- Легко добавить новые функции (email, покупки онлайн, бронирование и т.д.)
- Модульная архитектура
- REST API позволяет подключить любые клиенты

---

**Примечание для Claude Code:**

Это полное ТЗ v2.0 с голосовой активацией. Весь функционал из первой версии сохранён и дополнен REST API, Whisper, TTS и Tasker интеграцией. 

Обязательно создай:
1. Все новые файлы (api/, tasker/, nginx/)
2. Готовый XML профиль для Tasker (полностью рабочий)
3. Подробную инструкцию по настройке Tasker со скриншотами (в markdown)
4. Конфиги Nginx с Let's Encrypt
5. Два systemd service файла

Код должен быть production-ready и хорошо задокументирован.
