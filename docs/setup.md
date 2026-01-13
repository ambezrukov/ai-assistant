# Руководство по начальной настройке

Пошаговое руководство для первого запуска AI-ассистента на локальной машине (разработка/тестирование).

## Быстрый старт

Минимальная настройка для тестирования за 10 минут.

### 1. Установка зависимостей

```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/ai-assistant.git
cd ai-assistant

# Создать виртуальное окружение
python3.11 -m venv venv

# Активировать (Linux/Mac)
source venv/bin/activate

# Или активировать (Windows)
venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

### 2. Конфигурация

```bash
# Скопировать примеры
cp config.yaml.example config.yaml
cp .env.example .env

# Редактировать конфигурацию
nano config.yaml  # или любой редактор
nano .env
```

**Минимально необходимые настройки:**

В `config.yaml`:
```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"  # От @BotFather

claude:
  api_key: "YOUR_CLAUDE_API_KEY"  # От Anthropic Console

openai:
  api_key: "YOUR_OPENAI_API_KEY"  # Для Whisper
```

В `.env`:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
CLAUDE_API_KEY=your_claude_api_key
OPENAI_API_KEY=your_openai_api_key
API_BEARER_TOKEN=random_token_for_api
```

### 3. Инициализация БД

```bash
python -c "import asyncio; from utils.database import Database; asyncio.run(Database().init_db())"
```

### 4. Запуск

```bash
# Запустить всё (Telegram бот + API)
python main.py

# Или запустить только бота
python main.py --bot-only

# Или запустить только API
python main.py --api-only
```

Готово! Бот работает в Telegram, API доступен на http://localhost:8000

---

## Детальная настройка

### Получение Telegram Bot Token

1. Открыть Telegram и найти [@BotFather](https://t.me/BotFather)
2. Отправить команду `/newbot`
3. Ввести название бота (например: `My AI Assistant`)
4. Ввести username бота (например: `my_ai_assistant_bot`)
5. Скопировать токен вида: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

**Настроить команды бота:**
```
/setcommands

start - Начать работу с ботом
help - Показать справку
stats - Статистика использования
cancel - Отменить текущее действие
```

### Получение Claude API Key

1. Зарегистрироваться на [Anthropic Console](https://console.anthropic.com)
2. Перейти в Settings → API Keys
3. Create Key → Скопировать ключ
4. Пополнить баланс (минимум $5)

**Примерные затраты:**
- 1000 запросов ≈ $2-5 (зависит от длины сообщений)
- Claude Sonnet 4: $3 / 1M input tokens, $15 / 1M output tokens

### Получение OpenAI API Key

1. Зарегистрироваться на [OpenAI Platform](https://platform.openai.com)
2. Account → API Keys → Create new secret key
3. Скопировать ключ
4. Пополнить баланс (минимум $5)

**Примерные затраты:**
- Whisper API: $0.006 / минута аудио
- 100 голосовых сообщений (по 5 сек) ≈ $0.05

### Настройка Google Calendar API

**Создание проекта:**

1. Перейти в [Google Cloud Console](https://console.cloud.google.com)
2. Создать новый проект "AI Assistant"
3. Включить APIs:
   - Google Calendar API
   - Google Tasks API

**Создание OAuth 2.0 credentials:**

1. APIs & Services → Credentials
2. Create Credentials → OAuth client ID
3. Configure Consent Screen:
   - User Type: External
   - App name: AI Assistant
   - Support email: ваш email
   - Scopes: calendar, tasks
4. Application type: Desktop app
5. Download JSON → сохранить как `credentials/google_calendar_credentials.json`

**Первая авторизация:**

```bash
# Запустить скрипт авторизации
python -c "from integrations.google_calendar import get_calendar; get_calendar()"

# Откроется браузер
# Выбрать Google аккаунт
# Разрешить доступ
# Токен сохранится в data/google_calendar_token.json
```

Повторить для Google Tasks:
```bash
python -c "from integrations.google_tasks import get_tasks; get_tasks()"
```

### Настройка Obsidian

**Вариант 1: Filesystem (рекомендуется)**

```yaml
# config.yaml
obsidian:
  vault_path: "/path/to/your/obsidian/vault"
  notes_folder: "Notes"
  method: "filesystem"
```

**Вариант 2: Локальное хранилище**

```bash
# Создать отдельное хранилище
mkdir obsidian_vault
```

```yaml
# config.yaml
obsidian:
  vault_path: "./obsidian_vault"
  notes_folder: "AI Notes"
  method: "filesystem"
```

### Настройка API (опционально)

Если планируется использовать API для Tasker:

```yaml
# config.yaml
api:
  host: "0.0.0.0"  # Слушать на всех интерфейсах
  port: 8000
  auth:
    enabled: true
    bearer_token: "your-random-secure-token"  # Сгенерировать: openssl rand -hex 32

  cors:
    enabled: true
    origins:
      - "http://localhost"
      - "https://your-domain.com"
```

**Генерация Bearer Token:**

```bash
# Linux/Mac
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"

# Результат (пример):
# a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

## Структура проекта

После настройки структура должна выглядеть так:

```
ai-assistant/
├── config.yaml              ✓ Ваша конфигурация
├── .env                     ✓ Ваши секреты
├── venv/                    ✓ Виртуальное окружение
├── credentials/             ✓ Google credentials
│   ├── google_calendar_credentials.json
│   └── google_tasks_credentials.json
├── data/                    ✓ Автоматически создаётся
│   ├── ai_assistant.db
│   ├── google_calendar_token.json
│   └── google_tasks_token.json
├── logs/                    ✓ Автоматически создаётся
│   └── app.log
├── cache/                   ✓ Автоматически создаётся
│   └── *.mp3 (TTS файлы)
└── obsidian_vault/          ✓ Опционально
```

## Проверка настройки

### Тест БД

```bash
python -c "
from utils.database import Database
import asyncio

async def test():
    db = Database()
    await db.init_db()
    print('✓ Database OK')

asyncio.run(test())
"
```

### Тест Google Calendar

```bash
python -c "
from integrations.google_calendar import get_calendar
calendar = get_calendar()
print('✓ Google Calendar OK')
"
```

### Тест Claude AI

```bash
python -c "
from agent.claude_agent import ClaudeAgent
import asyncio

async def test():
    agent = ClaudeAgent()
    result = await agent.process_message('Привет', 'test_user')
    print(f'✓ Claude AI OK: {result[\"response_text\"][:50]}...')

asyncio.run(test())
"
```

### Тест API

```bash
# В отдельном терминале запустить API
python main.py --api-only

# В другом терминале
curl http://localhost:8000/api/v1/health

# Должен вернуть: {"status":"ok"}
```

## Настройка окружения разработки

### VS Code

Создать `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

### PyCharm

1. File → Settings → Project → Python Interpreter
2. Add Interpreter → Existing environment
3. Выбрать `venv/bin/python`

### Переменные окружения

Для разработки создать `.env.local`:

```env
# Переопределить некоторые настройки для dev
LOG_LEVEL=DEBUG
API_HOST=localhost
```

Загрузить при запуске:
```bash
export $(cat .env.local | xargs) && python main.py
```

## Troubleshooting

### Ошибка импорта модулей

```bash
# Проверить виртуальное окружение
which python
# Должен показать: /path/to/ai-assistant/venv/bin/python

# Переустановить зависимости
pip install --upgrade -r requirements.txt
```

### Ошибка БД

```bash
# Удалить и пересоздать БД
rm data/ai_assistant.db
python -c "import asyncio; from utils.database import Database; asyncio.run(Database().init_db())"
```

### Google OAuth не работает

```bash
# Проверить credentials
cat credentials/google_calendar_credentials.json

# Удалить старые токены
rm data/google_*.json

# Повторить авторизацию
python -c "from integrations.google_calendar import get_calendar; get_calendar()"
```

### Telegram бот не отвечает

1. **Проверить токен:**
   ```bash
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
   ```

2. **Проверить логи:**
   ```bash
   tail -f logs/app.log
   ```

3. **Проверить webhook:**
   ```bash
   # Удалить webhook если есть
   curl https://api.telegram.org/bot<YOUR_TOKEN>/deleteWebhook
   ```

### API возвращает 401

Проверить Bearer Token:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/health
```

## Следующие шаги

После успешной настройки:

1. Протестировать бота в Telegram
2. Попробовать разные команды
3. Настроить Tasker (см. `docs/tasker_setup.md`)
4. При необходимости развернуть на сервере (см. `docs/deployment.md`)
5. Ознакомиться с использованием (см. `docs/usage.md`)

## Полезные команды

```bash
# Очистить кэш
rm -rf cache/*.mp3

# Очистить логи
echo "" > logs/app.log

# Обновить зависимости
pip install --upgrade -r requirements.txt

# Проверить конфигурацию
python -c "from utils.config import load_config; import yaml; print(yaml.dump(load_config(), default_flow_style=False))"

# Запустить в debug режиме
LOG_LEVEL=DEBUG python main.py
```

## Поддержка

- Документация: `docs/`
- GitHub Issues: https://github.com/yourusername/ai-assistant/issues
- Telegram: @your_support_channel
