# Настройка Tasker для голосовой активации

Пошаговая инструкция по настройке Tasker на Android для голосового управления AI-ассистентом.

## Предварительные требования

- Android устройство (версия 7.0+)
- Установленный Tasker (Google Play / F-Droid)
- Развернутый API с HTTPS
- Bearer token для API авторизации

## Шаг 1: Установка Tasker

```
1. Скачать Tasker:
   - Google Play: https://play.google.com/store/apps/details?id=net.dinglisch.android.taskerm
   - F-Droid: https://f-droid.org/packages/net.dinglisch.android.taskerm

2. Установить и предоставить необходимые разрешения:
   - Доступ к микрофону
   - Доступ к хранилищу
   - Доступность (Accessibility) - для перехвата кнопок
   - Автозапуск
```

## Шаг 2: Импорт профиля

### Метод 1: Импорт XML файла

```
1. Скопировать файл AI_Assistant.prj.xml на устройство
   - Через USB в папку Tasker/projects/
   - Или через облако (Google Drive, Telegram)

2. В Tasker:
   - Главный экран → три точки (меню) → Data → Restore
   - Выбрать AI_Assistant.prj.xml
   - Нажать "Restore"
```

### Метод 2: Ручное создание

Если импорт не работает, можно создать профиль вручную (инструкция ниже).

## Шаг 3: Настройка переменных

После импорта необходимо настроить переменные:

```
1. В Tasker → Tasks → Voice Command
2. Найти действия с переменными (Action 1-3)
3. Изменить значения:

%API_URL:
   https://your-domain.com/api/v1/voice-command

%API_TOKEN:
   your-bearer-token-from-config

%USER_ID:
   your-telegram-user-id
```

**Как получить User ID:**
```
1. Открыть Telegram
2. Отправить команду /start боту @userinfobot
3. Скопировать Id
```

**Как получить Bearer Token:**
```
1. Открыть config.yaml на сервере
2. Найти секцию api.auth.bearer_token
3. Скопировать токен
```

## Шаг 4: Настройка триггера

По умолчанию профиль активируется **длинным нажатием кнопки питания**.

### Изменить на другую кнопку:

```
1. Tasker → Profiles → AI Assistant - Voice
2. Долгое нажатие на Event → Edit
3. Выбрать другое событие:

   - Headset Button (кнопка на наушниках)
   - Shake (встряхивание)
   - Proximity Sensor (датчик приближения)
   - Volume Button (кнопка громкости)
```

### Настроить голосовую фразу:

```
1. Создать новый профиль
2. Event → Voice → Voice Command
3. Spoken Text: "окей ассистент" (или другая фраза)
4. Привязать Task: Voice Command
```

## Шаг 5: Тестирование

### Тест голосовой команды:

```
1. Выйти из Tasker
2. Долго нажать кнопку питания
3. Должна появиться вибрация
4. Голосовое сообщение: "Слушаю"
5. Произнести команду (5 секунд)
6. Вибрация - конец записи
7. Ожидание ответа (2-5 секунд)
8. Воспроизведение голосового ответа
```

### Тест текстовой команды:

```
1. Tasker → Tasks → Text Command
2. Нажать ▶ (Play)
3. Ввести текст команды
4. Нажать OK
5. Получить Toast с ответом
```

## Шаг 6: Настройка подтверждений

Если AI запрашивает подтверждение действия:

```
1. После голосового ответа появится диалог
2. Текст подтверждения из API
3. Кнопки: "Да" / "Нет"
4. При нажатии "Да" - действие выполняется
5. Голосовое подтверждение результата
```

## Troubleshooting

### Проблема: "Слушаю" не произносится

**Решение:**
```
1. Настройки → Приложения → Tasker
2. Разрешения → Микрофон → Разрешить
3. Настройки → Text-to-Speech
4. Установить русский голос (Google TTS)
```

### Проблема: Ошибка записи голоса

**Решение:**
```
1. Tasker → Preferences → Misc
2. Включить "Use New Recorder"
3. Если не помогло, отключить обратно
```

### Проблема: Нет ответа от API

**Проверить:**
```
1. Интернет соединение (WiFi/Mobile Data)
2. Правильность API_URL (https://)
3. Валидность Bearer Token
4. Tasker → Run Log - посмотреть ошибку HTTP

Частые ошибки:
- 401 Unauthorized → неверный token
- 404 Not Found → неверный URL
- 500 Internal Server Error → проблема на сервере
```

### Проблема: Аудио не воспроизводится

**Решение:**
```
1. Проверить что API возвращает audio_url
2. Tasker → Run Log → найти HTTP response
3. Убедиться что файл скачивается
4. Проверить разрешение на хранилище
```

## Создание профиля вручную

Если импорт XML не работает:

### Создать Task "Voice Command":

```
1. Tasks → + → Voice Command

2. Добавить действия:

Action 1: Variable Set
   Name: %API_URL
   To: https://your-domain.com/api/v1/voice-command

Action 2: Variable Set
   Name: %API_TOKEN
   To: your-bearer-token

Action 3: Variable Set
   Name: %USER_ID
   To: your-telegram-id

Action 4: Vibrate
   Time: 200

Action 5: Say
   Text: Слушаю
   Engine: Google TTS
   Language: ru

Action 6: Record Audio
   File: voice_command.m4a
   Duration: 5
   Source: Microphone

Action 7: Vibrate
   Time: 100

Action 8: HTTP Request
   Method: POST
   URL: %API_URL
   Headers: Authorization: Bearer %API_TOKEN
   Body Type: Multipart
   Files: audio=voice_command.m4a
   Fields: user_id=%USER_ID
   Output: %http_response

Action 9: Variable Search Replace
   Variable: %http_response
   Search: "message":"([^"]+)"
   Store Matches In: %response_text

Action 10: Variable Search Replace
   Variable: %http_response
   Search: "audio_url":"([^"]+)"
   Store Matches In: %audio_url

Action 11: If %audio_url matches https://

Action 12: HTTP Request
   Method: GET
   URL: %audio_url
   Output File: response_audio.mp3

Action 13: Media Control
   Cmd: Play
   File: response_audio.mp3

Action 14: End If

Action 15: Delete File
   File: voice_command.m4a

Action 16: Delete File
   File: response_audio.mp3
```

### Создать Profile:

```
1. Profiles → + → Event → Hardware → Long Press

2. Key: Power Button

3. Task: Voice Command

4. Включить профиль (зеленый переключатель)
```

## Дополнительные настройки

### Отключить встроенного Google Assistant:

```
1. Настройки → Приложения → Google
2. Поиск и голосовой помощник
3. Отключить "Voice Match"
4. Или изменить активацию с кнопки питания
```

### Настроить автозапуск Tasker:

```
1. Настройки → Приложения → Tasker
2. Батарея → Без ограничений
3. Автозапуск → Включить
```

### Настроить приоритет уведомлений:

```
1. Tasker → Preferences → Monitor → Notification Priority
2. Выбрать: High
3. Это предотвратит завершение Tasker системой
```

## Расширенные сценарии

### Сценарий 1: Команда с экрана блокировки

```
Profile: Screen Off → Voice Command
Event: Display Off
Task: Voice Command (с разблокировкой экрана)
```

### Сценарий 2: Автоматические напоминания

```
Profile: Morning Reminder
Time: 09:00
Task: Text Command ("что у меня сегодня в календаре?")
```

### Сценарий 3: Команда по геолокации

```
Profile: Arrived Home
Location: Дом (радиус 100м)
Task: Text Command ("добавить покупки: молоко хлеб яйца")
```

### Сценарий 4: Интеграция с другими приложениями

```
Profile: WhatsApp Message Received
Event: Notification → WhatsApp
Task: Voice Command → Parse response → Reply
```

## Безопасность

### Рекомендации:

1. **Не делиться Bearer Token:**
   - Token дает полный доступ к API
   - Хранить только на устройстве

2. **Использовать HTTPS:**
   - Никогда не использовать http://
   - Данные шифруются SSL/TLS

3. **Ограничить доступ:**
   - Настроить блокировку Tasker паролем
   - Settings → UI → Set Password

4. **Регулярно менять токен:**
   - Раз в 3-6 месяцев обновлять token
   - Обновить в Tasker и config.yaml

## Оптимизация

### Уменьшить задержку:

```
1. Voice Command → Action 6 (Record Audio)
2. Уменьшить Duration до 3 секунд
3. Для коротких команд достаточно
```

### Увеличить качество записи:

```
1. Voice Command → Action 6
2. Format: AAC
3. Sample Rate: 44100
4. Bitrate: 128
```

### Кэшировать ответы:

```
Добавить после Action 13:
Action: Write File
   File: last_response.txt
   Text: %response_text
   Append: No
```

## Полезные ссылки

- [Tasker Wiki](https://tasker.joaoapps.com/userguide/en/)
- [Reddit r/Tasker](https://www.reddit.com/r/tasker/)
- [TaskerNet - готовые профили](https://taskernet.com/)
- [AutoApps Plugins](https://joaoapps.com/)

## Поддержка

При возникновении проблем:

1. **Проверить Run Log:**
   - Tasker → три точки → Run Log
   - Найти ошибки (красным)

2. **Включить Debug Mode:**
   - Tasker → Preferences → Misc → Beginner Mode (выключить)
   - Покажет больше деталей

3. **Экспортировать профиль:**
   - Long press на Profile → Export → Description to Clipboard
   - Отправить в поддержку для диагностики

4. **Логи API:**
   - На сервере: `tail -f logs/app.log`
   - Поможет найти проблемы на стороне API
