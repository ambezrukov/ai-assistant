# Развёртывание AI-ассистента v2.1 на production сервере

Полная инструкция по установке и настройке на Ubuntu/Debian сервере.

**Новое в v2.1:**
- ✅ Поддержка локального Ollama (опционально)
- ✅ Персистентная память пользователя
- ✅ Гибридная LLM архитектура

## Системные требования

- Ubuntu 22.04 LTS или Debian 12+
- Минимум 2 GB RAM
- 20 GB свободного места на диске
- Python 3.11+
- Доменное имя с SSL сертификатом
- Стабильное интернет-соединение

## Шаг 1: Подготовка сервера

### Обновление системы

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3.11 python3.11-venv python3.11-dev \
    build-essential nginx certbot python3-certbot-nginx \
    supervisor sqlite3 ffmpeg
```

### Создание пользователя

```bash
# Создать отдельного пользователя для безопасности
sudo useradd -m -s /bin/bash ai-assistant
sudo usermod -aG sudo ai-assistant

# Переключиться на нового пользователя
sudo su - ai-assistant
```

## Шаг 2: Установка проекта

### Клонирование репозитория

```bash
# Создать директорию
sudo mkdir -p /opt/ai-assistant
sudo chown ai-assistant:ai-assistant /opt/ai-assistant

# Клонировать (или загрузить архив)
cd /opt/ai-assistant
git clone https://github.com/yourusername/ai-assistant.git .

# Или распаковать архив
# scp ai-assistant.tar.gz user@server:/tmp/
# tar -xzf /tmp/ai-assistant.tar.gz -C /opt/ai-assistant
```

### Создание виртуального окружения

```bash
cd /opt/ai-assistant

# Создать venv
python3.11 -m venv venv

# Активировать
source venv/bin/activate

# Обновить pip
pip install --upgrade pip setuptools wheel

# Установить зависимости
pip install -r requirements.txt
```

## Шаг 3: Настройка конфигурации

### Копирование примеров конфигурации

```bash
cp config.yaml.example config.yaml
cp .env.example .env
```

### Настройка config.yaml

```bash
nano config.yaml
```

**Важные секции для изменения:**

```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"  # От @BotFather

api:
  host: "127.0.0.1"
  port: 8000
  auth:
    bearer_token: "GENERATE_RANDOM_TOKEN_HERE"  # openssl rand -hex 32

claude:
  api_key: "YOUR_CLAUDE_API_KEY"  # От Anthropic
  model: "claude-sonnet-4-20250514"

openai:
  api_key: "YOUR_OPENAI_API_KEY"  # Для Whisper

google:
  calendar:
    credentials_file: "/opt/ai-assistant/credentials/google_calendar_credentials.json"
    token_file: "/opt/ai-assistant/data/google_calendar_token.json"
  tasks:
    credentials_file: "/opt/ai-assistant/credentials/google_tasks_credentials.json"
    token_file: "/opt/ai-assistant/data/google_tasks_token.json"

obsidian:
  vault_path: "/opt/ai-assistant/obsidian_vault"
  method: "filesystem"

database:
  path: "/opt/ai-assistant/data/ai_assistant.db"

logging:
  level: "INFO"
  file: "/opt/ai-assistant/logs/app.log"
```

### Настройка .env

```bash
nano .env
```

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
CLAUDE_API_KEY=your_claude_api_key
OPENAI_API_KEY=your_openai_api_key
API_BEARER_TOKEN=your_random_token
```

## Шаг 4: Настройка Google APIs

### Создание OAuth 2.0 credentials

1. **Google Cloud Console:**
   - Перейти: https://console.cloud.google.com
   - Создать новый проект "AI Assistant"

2. **Включить API:**
   ```
   - Google Calendar API
   - Google Tasks API
   ```

3. **Создать OAuth 2.0 Client ID:**
   ```
   - APIs & Services → Credentials
   - Create Credentials → OAuth client ID
   - Application type: Desktop app
   - Скачать JSON файл
   ```

4. **Сохранить credentials:**
   ```bash
   mkdir -p /opt/ai-assistant/credentials

   # Загрузить файлы на сервер
   scp google_credentials.json user@server:/opt/ai-assistant/credentials/

   # Переименовать
   mv credentials/google_credentials.json credentials/google_calendar_credentials.json
   cp credentials/google_calendar_credentials.json credentials/google_tasks_credentials.json
   ```

5. **Первая авторизация:**
   ```bash
   # Запустить временно для OAuth flow
   cd /opt/ai-assistant
   source venv/bin/activate
   python -c "from integrations.google_calendar import get_calendar; get_calendar()"

   # Откроется браузер для авторизации
   # После авторизации token будет сохранён в data/
   ```

## Шаг 5: Создание директорий и БД

```bash
# Создать необходимые директории
mkdir -p /opt/ai-assistant/{logs,data,cache,credentials,obsidian_vault}

# Инициализировать БД
cd /opt/ai-assistant
source venv/bin/activate
python -c "import asyncio; from utils.database import Database; asyncio.run(Database().init_db())"

# Установить права
chown -R ai-assistant:ai-assistant /opt/ai-assistant
chmod 700 /opt/ai-assistant/credentials
chmod 600 /opt/ai-assistant/credentials/*
chmod 600 /opt/ai-assistant/.env
chmod 600 /opt/ai-assistant/config.yaml
```

## Шаг 6: Настройка systemd сервисов

### Копирование сервисов

```bash
sudo cp systemd/ai-assistant-bot.service /etc/systemd/system/
sudo cp systemd/ai-assistant-api.service /etc/systemd/system/

# Перезагрузить systemd
sudo systemctl daemon-reload
```

### Включение и запуск

```bash
# Включить автозапуск
sudo systemctl enable ai-assistant-bot
sudo systemctl enable ai-assistant-api

# Запустить сервисы
sudo systemctl start ai-assistant-bot
sudo systemctl start ai-assistant-api

# Проверить статус
sudo systemctl status ai-assistant-bot
sudo systemctl status ai-assistant-api
```

### Логи сервисов

```bash
# Создать директорию для логов
sudo mkdir -p /var/log/ai-assistant
sudo chown ai-assistant:ai-assistant /var/log/ai-assistant

# Просмотр логов
sudo journalctl -u ai-assistant-bot -f
sudo journalctl -u ai-assistant-api -f

# Логи приложения
tail -f /opt/ai-assistant/logs/app.log
```

## Шаг 7: Настройка Nginx

### Копирование конфигурации

```bash
sudo cp nginx/ai_assistant.conf /etc/nginx/sites-available/ai_assistant

# Изменить your-domain.com на ваш домен
sudo nano /etc/nginx/sites-available/ai_assistant
```

### Получение SSL сертификата

```bash
# Создать временную конфигурацию (только HTTP)
sudo nano /etc/nginx/sites-available/ai_assistant

# Включить сайт
sudo ln -s /etc/nginx/sites-available/ai_assistant /etc/nginx/sites-enabled/

# Проверить конфигурацию
sudo nginx -t

# Перезапустить Nginx
sudo systemctl restart nginx

# Получить сертификат Let's Encrypt
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Применить полную конфигурацию
sudo cp nginx/ai_assistant.conf /etc/nginx/sites-available/ai_assistant
sudo systemctl reload nginx
```

Подробнее см. `nginx/setup_https.md`

## Шаг 8: Проверка работоспособности

### Проверка API

```bash
# Health check
curl https://your-domain.com/api/v1/health

# Должен вернуть:
# {"status":"ok"}

# Тест текстовой команды
curl -X POST https://your-domain.com/api/v1/text-command \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Привет","user_id":"test_user"}'
```

### Проверка Telegram бота

```bash
# В Telegram отправить боту:
/start

# Должен ответить приветствием
```

### Проверка логов

```bash
# API логи
tail -f /var/log/ai-assistant/api.log

# Bot логи
tail -f /var/log/ai-assistant/bot.log

# Приложение
tail -f /opt/ai-assistant/logs/app.log

# Nginx
tail -f /var/log/nginx/ai_assistant_access.log
tail -f /var/log/nginx/ai_assistant_error.log
```

## Шаг 9: Установка Ollama (опционально)

Если хотите использовать локальную LLM для экономии на API запросах:

### Установка Ollama

```bash
# Скачать и установить
curl -fsSL https://ollama.com/install.sh | sh

# Проверить установку
ollama --version
```

### Скачивание модели

```bash
# Рекомендуемая модель: Qwen 2.5 7B
ollama pull qwen2.5:7b

# Альтернативы:
# ollama pull llama3.2:3b  # Легче (1.6GB)
# ollama pull mistral:7b   # Хорошая производительность

# Проверить список моделей
ollama list
```

### Настройка в конфиге

Отредактируйте `config.yaml`:

```yaml
ollama:
  enabled: true  # Включить Ollama
  url: "http://localhost:11434"
  model: "qwen2.5:7b"
```

### Перезапуск сервисов

```bash
sudo systemctl restart ai-assistant-bot
sudo systemctl restart ai-assistant-api
```

### Проверка работы

```bash
# Проверить, что Ollama запущен
systemctl status ollama

# Проверить API
curl http://localhost:11434/api/tags

# В логах должно появиться
sudo journalctl -u ai-assistant-bot -n 20 | grep Ollama
# Вывод: "Ollama провайдер инициализирован"
```

**Преимущества:**
- 🆓 Экономия на Claude API (до 70% запросов через Ollama)
- ⚡ Более быстрые ответы на простые запросы
- 🔒 Приватность (данные не уходят в облако)

**Системные требования для Ollama:**
- Модель 7B: 4 vCPU, 8GB RAM
- Модель 3B: 2 vCPU, 4GB RAM
- Диск: +5GB для модели

---

## Шаг 10: Настройка мониторинга

### Logrotate для логов

```bash
sudo nano /etc/logrotate.d/ai-assistant
```

```
/var/log/ai-assistant/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ai-assistant ai-assistant
    sharedscripts
    postrotate
        systemctl reload ai-assistant-bot
        systemctl reload ai-assistant-api
    endscript
}
```

### Мониторинг ресурсов

```bash
# Установить htop
sudo apt install htop

# Мониторить использование
htop

# Проверить использование диска
df -h
du -sh /opt/ai-assistant/*
```

### Настройка алертов

```bash
# Установить Monit
sudo apt install monit

sudo nano /etc/monit/conf.d/ai-assistant
```

```
check process ai-assistant-bot with pidfile /var/run/ai-assistant-bot.pid
    start program = "/bin/systemctl start ai-assistant-bot"
    stop program = "/bin/systemctl stop ai-assistant-bot"
    if failed host 127.0.0.1 port 8000 then restart
    if 5 restarts within 5 cycles then alert

check process ai-assistant-api with pidfile /var/run/ai-assistant-api.pid
    start program = "/bin/systemctl start ai-assistant-api"
    stop program = "/bin/systemctl stop ai-assistant-api"
    if cpu > 80% for 5 cycles then alert
    if memory > 80% then alert
```

## Шаг 11: Резервное копирование

### Скрипт бэкапа

```bash
sudo nano /opt/ai-assistant/backup.sh
```

```bash
#!/bin/bash

BACKUP_DIR="/opt/backups/ai-assistant"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Бэкап БД
cp /opt/ai-assistant/data/ai_assistant.db $BACKUP_DIR/db_$DATE.db

# Бэкап конфигурации
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    /opt/ai-assistant/config.yaml \
    /opt/ai-assistant/.env \
    /opt/ai-assistant/credentials/

# Бэкап Obsidian vault
tar -czf $BACKUP_DIR/obsidian_$DATE.tar.gz \
    /opt/ai-assistant/obsidian_vault/

# Удалить старые бэкапы (старше 30 дней)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.db" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
chmod +x /opt/ai-assistant/backup.sh

# Настроить cron
crontab -e
```

```
# Бэкап каждый день в 3:00
0 3 * * * /opt/ai-assistant/backup.sh >> /var/log/ai-assistant/backup.log 2>&1
```

## Шаг 12: Обновление приложения

### Процедура обновления

```bash
# Остановить сервисы
sudo systemctl stop ai-assistant-bot
sudo systemctl stop ai-assistant-api

# Создать бэкап
/opt/ai-assistant/backup.sh

# Обновить код
cd /opt/ai-assistant
git pull origin main

# Обновить зависимости
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Применить миграции БД (если есть)
# python migrate.py

# Запустить сервисы
sudo systemctl start ai-assistant-bot
sudo systemctl start ai-assistant-api

# Проверить статус
sudo systemctl status ai-assistant-bot
sudo systemctl status ai-assistant-api
```

## Безопасность

### Firewall (UFW)

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### Fail2ban

```bash
sudo apt install fail2ban

sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/ai_assistant_error.log
```

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Автоматические обновления безопасности

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

## Troubleshooting

### Сервис не запускается

```bash
# Проверить логи
sudo journalctl -u ai-assistant-bot -n 50
sudo journalctl -u ai-assistant-api -n 50

# Проверить права
ls -la /opt/ai-assistant

# Проверить Python
cd /opt/ai-assistant
source venv/bin/activate
python -c "import anthropic; print('OK')"
```

### Ошибки базы данных

```bash
# Проверить БД
sqlite3 /opt/ai-assistant/data/ai_assistant.db
sqlite> .tables
sqlite> .quit

# Пересоздать БД
cd /opt/ai-assistant
source venv/bin/activate
python -c "import asyncio; from utils.database import Database; asyncio.run(Database().init_db())"
```

### Проблемы с Google OAuth

```bash
# Удалить старые токены
rm /opt/ai-assistant/data/google_*.json

# Повторить авторизацию
python -c "from integrations.google_calendar import get_calendar; get_calendar()"
```

### Высокое использование ресурсов

```bash
# Проверить процессы
ps aux | grep python

# Убить зависшие процессы
sudo pkill -f "python.*main.py"

# Перезапустить сервисы
sudo systemctl restart ai-assistant-bot
sudo systemctl restart ai-assistant-api
```

## Полезные команды

```bash
# Перезапуск всех сервисов
sudo systemctl restart ai-assistant-bot ai-assistant-api nginx

# Просмотр логов в реальном времени
sudo journalctl -u ai-assistant-bot -u ai-assistant-api -f

# Проверка использования портов
sudo netstat -tulpn | grep 8000

# Очистка кэша TTS
rm -rf /opt/ai-assistant/cache/*.mp3

# Тест конфигурации
cd /opt/ai-assistant
source venv/bin/activate
python -c "from utils.config import load_config; print(load_config())"
```

## Следующие шаги

После успешного развёртывания:

1. Настроить Tasker на Android (см. `docs/tasker_setup.md`)
2. Ознакомиться с использованием (см. `docs/usage.md`)
3. Настроить мониторинг и алерты
4. Протестировать все функции
5. Создать регулярные бэкапы

## Поддержка

При возникновении проблем:

1. Проверить логи: `tail -f /opt/ai-assistant/logs/app.log`
2. Проверить статус сервисов: `systemctl status ai-assistant-*`
3. Проверить Nginx: `sudo nginx -t`
4. Создать issue на GitHub
