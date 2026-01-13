# Настройка Nginx + HTTPS (Let's Encrypt)

Пошаговая инструкция по развертыванию API с HTTPS сертификатом.

## Предварительные требования

- VPS/сервер с Ubuntu/Debian
- Доменное имя, указывающее на IP сервера
- Установленный Python 3.11+
- Работающее приложение на порту 8000

## Шаг 1: Установка Nginx

```bash
# Обновить пакеты
sudo apt update
sudo apt upgrade -y

# Установить Nginx
sudo apt install nginx -y

# Проверить статус
sudo systemctl status nginx
```

## Шаг 2: Установка Certbot

Certbot - утилита для автоматического получения SSL сертификатов от Let's Encrypt.

```bash
# Установить Certbot и плагин для Nginx
sudo apt install certbot python3-certbot-nginx -y
```

## Шаг 3: Настройка DNS

Убедитесь, что ваш домен указывает на IP сервера:

```bash
# Проверить A-запись
nslookup your-domain.com

# Должен вернуть IP вашего сервера
```

**Важно:** DNS изменения могут занять до 24 часов для распространения.

## Шаг 4: Настройка Nginx (без SSL)

Сначала настроим базовую конфигурацию без SSL:

```bash
# Скопировать конфигурацию
sudo cp nginx/ai_assistant.conf /etc/nginx/sites-available/ai_assistant

# Заменить your-domain.com на ваш домен
sudo nano /etc/nginx/sites-available/ai_assistant
# Изменить: server_name your-domain.com www.your-domain.com;
```

Создать упрощенную конфигурацию для первого запуска:

```bash
sudo nano /etc/nginx/sites-available/ai_assistant
```

**Временная конфигурация (для получения сертификата):**

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Создать симлинк
sudo ln -s /etc/nginx/sites-available/ai_assistant /etc/nginx/sites-enabled/

# Удалить дефолтную конфигурацию (опционально)
sudo rm /etc/nginx/sites-enabled/default

# Проверить конфигурацию
sudo nginx -t

# Перезапустить Nginx
sudo systemctl restart nginx
```

## Шаг 5: Получение SSL сертификата

```bash
# Запустить Certbot для автоматической настройки
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Ответить на вопросы:
# Email: your-email@example.com
# Agree to Terms of Service: Yes (A)
# Share email: No (N)
# Redirect HTTP to HTTPS: Yes (2)
```

Certbot автоматически:
- Получит сертификат
- Модифицирует конфигурацию Nginx
- Настроит автоматическое обновление

## Шаг 6: Применить полную конфигурацию

После получения сертификата, заменить конфигурацию на полную версию:

```bash
# Восстановить полную конфигурацию
sudo cp nginx/ai_assistant.conf /etc/nginx/sites-available/ai_assistant

# Изменить your-domain.com на ваш домен
sudo nano /etc/nginx/sites-available/ai_assistant

# Проверить конфигурацию
sudo nginx -t

# Перезапустить
sudo systemctl restart nginx
```

## Шаг 7: Проверка работы

```bash
# Проверить HTTP -> HTTPS редирект
curl -I http://your-domain.com
# Должен вернуть: HTTP/1.1 301 Moved Permanently

# Проверить HTTPS
curl https://your-domain.com/api/v1/health
# Должен вернуть: {"status": "ok"}

# Проверить SSL сертификат
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

## Шаг 8: Автоматическое обновление сертификата

Certbot автоматически настраивает cron job для обновления:

```bash
# Проверить таймер обновления
sudo systemctl status certbot.timer

# Протестировать обновление (dry run)
sudo certbot renew --dry-run
```

Сертификаты Let's Encrypt действительны 90 дней. Certbot обновит их автоматически за 30 дней до истечения.

## Шаг 9: Настройка Firewall

```bash
# Если используется ufw
sudo ufw allow 'Nginx Full'
sudo ufw delete allow 'Nginx HTTP'

# Проверить правила
sudo ufw status
```

## Шаг 10: Мониторинг логов

```bash
# Логи Nginx
sudo tail -f /var/log/nginx/ai_assistant_access.log
sudo tail -f /var/log/nginx/ai_assistant_error.log

# Логи приложения
tail -f logs/app.log
```

## Troubleshooting

### Ошибка: "Connection refused"

```bash
# Проверить, что приложение запущено
ps aux | grep python
netstat -tulpn | grep 8000

# Перезапустить приложение
sudo systemctl restart ai-assistant-api
```

### Ошибка: "502 Bad Gateway"

```bash
# Проверить статус приложения
sudo systemctl status ai-assistant-api

# Проверить логи
sudo journalctl -u ai-assistant-api -n 50
```

### Ошибка: Certbot не может получить сертификат

```bash
# Убедиться, что порт 80 открыт
sudo netstat -tulpn | grep :80

# Проверить DNS
dig your-domain.com +short

# Проверить, что Nginx работает
sudo systemctl status nginx
```

### Проблемы с обновлением сертификата

```bash
# Вручную обновить сертификат
sudo certbot renew --force-renewal

# Проверить логи Certbot
sudo cat /var/log/letsencrypt/letsencrypt.log
```

## Безопасность

### Rate Limiting

Конфигурация включает защиту от DDoS:
- Voice endpoints: 5 req/s
- Text endpoints: 10 req/s

### Рекомендации

1. **Включить fail2ban:**
```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

2. **Настроить автоматические обновления:**
```bash
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

3. **Изменить SSH порт:**
```bash
sudo nano /etc/ssh/sshd_config
# Port 2222
sudo systemctl restart sshd
```

4. **Использовать SSH ключи:**
```bash
# На локальной машине
ssh-keygen -t ed25519 -C "your-email@example.com"
ssh-copy-id -p 2222 user@your-domain.com
```

## Полезные команды

```bash
# Перезапустить Nginx
sudo systemctl restart nginx

# Проверить конфигурацию
sudo nginx -t

# Обновить сертификат вручную
sudo certbot renew

# Проверить статус SSL
sudo certbot certificates

# Отозвать сертификат (при необходимости)
sudo certbot revoke --cert-path /etc/letsencrypt/live/your-domain.com/cert.pem
```

## Мониторинг SSL сертификата

Настроить уведомления об истечении сертификата:

1. **SSL Labs Test:**
   - Проверить: https://www.ssllabs.com/ssltest/analyze.html?d=your-domain.com

2. **Использовать сервисы мониторинга:**
   - https://uptimerobot.com
   - https://www.statuscake.com

## Резервное копирование

```bash
# Создать бэкап конфигурации
sudo tar -czf nginx-backup-$(date +%Y%m%d).tar.gz \
    /etc/nginx/sites-available/ai_assistant \
    /etc/letsencrypt/

# Восстановить из бэкапа
sudo tar -xzf nginx-backup-20250108.tar.gz -C /
```

## Ссылки

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Certbot Documentation](https://certbot.eff.org/docs/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
