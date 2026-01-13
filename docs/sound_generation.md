# Создание звуков для голосового ассистента "Зиночка"

## Необходимые звуковые файлы

Для полноценной работы голосового ассистента требуются следующие звуки:

1. **listening.mp3** - звук активации (когда ассистент начинает слушать)
2. **thinking.mp3** - звук обработки запроса (опционально)
3. **done.mp3** - звук завершения задачи (опционально)
4. **error.mp3** - звук ошибки (опционально)

---

## Способ 1: Генерация через Text-to-Speech (TTS)

Самый простой способ - использовать TTS для создания коротких аудио файлов.

### 1.1. Использование Google TTS (онлайн)

**Инструмент**: Google Cloud Text-to-Speech

1. Перейдите на https://cloud.google.com/text-to-speech
2. Нажмите "Try it now"
3. Введите текст для озвучки
4. Выберите язык: **Russian (ru-RU)**
5. Выберите голос: **ru-RU-Wavenet-C** (женский, приятный)
6. Нажмите "Speak it"
7. Скачайте MP3

**Тексты для генерации**:
- **listening.mp3**: "Слушаю вас"
- **thinking.mp3**: "Обрабатываю"
- **done.mp3**: "Готово"
- **error.mp3**: "Ошибка"

### 1.2. Использование Python + gTTS (локально)

Создайте скрипт для генерации звуков:

```python
#!/usr/bin/env python3
# generate_sounds.py

from gtts import gTTS
import os

# Путь для сохранения
output_dir = "/sdcard/Tasker/sounds/"
os.makedirs(output_dir, exist_ok=True)

# Тексты для озвучки
sounds = {
    "listening.mp3": "Слушаю вас",
    "thinking.mp3": "Обрабатываю",
    "done.mp3": "Готово",
    "error.mp3": "Ошибка"
}

# Генерация
for filename, text in sounds.items():
    tts = gTTS(text=text, lang='ru', slow=False)
    tts.save(os.path.join(output_dir, filename))
    print(f"✓ Создан: {filename}")

print("\nВсе звуки созданы!")
```

**Запуск**:
```bash
pip install gtts
python generate_sounds.py
```

---

## Способ 2: Использование готовых звуков

Если вы хотите использовать приятные звуковые эффекты вместо голоса:

### 2.1. Бесплатные библиотеки звуков

**Рекомендуемые сайты**:
- https://freesound.org/ - огромная коллекция бесплатных звуков
- https://pixabay.com/sound-effects/ - качественные звуковые эффекты
- https://mixkit.co/free-sound-effects/ - современные звуки

**Поисковые запросы**:
- "notification sound"
- "beep"
- "chime"
- "ding"
- "error sound"

### 2.2. Рекомендуемые звуки

**listening.mp3** (звук активации):
- Короткий приятный "beep" (0.5-1 секунда)
- Восходящий тон
- Не раздражающий

**thinking.mp3** (обработка):
- Мягкий гул или пульсация (1-2 секунды)
- Можно пропустить - не обязателен

**done.mp3** (готово):
- Два коротких "beep" (0.5 секунды)
- Подтверждающий тон

**error.mp3** (ошибка):
- Нисходящий тон (0.5 секунды)
- Должен быть отличим от остальных

---

## Способ 3: Создание через Audacity

Если хотите создать уникальные звуки самостоятельно:

### 3.1. Установка Audacity

1. Скачайте: https://www.audacityteam.org/
2. Установите программу
3. Установите LAME MP3 encoder для экспорта в MP3

### 3.2. Создание простого "beep"

1. Откройте Audacity
2. **Generate** → **Tone**
3. Настройки:
   - Waveform: **Sine**
   - Frequency: **800 Hz** (приятная частота)
   - Amplitude: **0.8**
   - Duration: **0.5 seconds**
4. Нажмите **OK**
5. Примените эффект **Fade Out**: **Effect** → **Fade Out**
6. Экспортируйте: **File** → **Export** → **Export as MP3**

### 3.3. Создание "восходящего тона"

1. **Generate** → **Chirp**
2. Настройки:
   - Start Frequency: **400 Hz**
   - End Frequency: **800 Hz**
   - Duration: **0.5 seconds**
   - Waveform: **Sine**
3. Примените **Fade In** и **Fade Out**
4. Экспортируйте как **listening.mp3**

---

## Способ 4: Использование AI TTS (продвинутый)

Для максимально естественного звучания можно использовать AI-генераторы голоса.

### 4.1. ElevenLabs (онлайн)

**Ссылка**: https://elevenlabs.io/

**Преимущества**:
- Очень естественный голос
- Поддержка русского языка
- Бесплатный тариф: 10,000 символов/месяц

**Инструкция**:
1. Зарегистрируйтесь на ElevenLabs
2. Выберите русский голос (например, "Rachel" с русским акцентом)
3. Введите текст: "Слушаю вас"
4. Нажмите **Generate**
5. Скачайте MP3
6. Повторите для остальных фраз

### 4.2. Yandex SpeechKit (API)

**Ссылка**: https://cloud.yandex.ru/services/speechkit

**Преимущества**:
- Отличное качество русского языка
- Несколько женских голосов
- Бесплатный тариф: 1 млн символов/месяц

**Python скрипт**:
```python
#!/usr/bin/env python3
# generate_sounds_yandex.py

import requests
import os

# Ваш API ключ Yandex Cloud
API_KEY = "ваш_api_ключ"
FOLDER_ID = "ваш_folder_id"

# URL API
url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"

# Параметры
def generate_sound(text, filename):
    headers = {
        "Authorization": f"Api-Key {API_KEY}"
    }
    data = {
        "text": text,
        "lang": "ru-RU",
        "voice": "alena",  # Приятный женский голос
        "format": "mp3",
        "speed": "1.0",
        "emotion": "neutral"
    }

    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"✓ Создан: {filename}")
    else:
        print(f"✗ Ошибка при создании {filename}: {response.text}")

# Генерация звуков
sounds = {
    "listening.mp3": "Слушаю вас",
    "thinking.mp3": "Обрабатываю",
    "done.mp3": "Готово",
    "error.mp3": "Ошибка"
}

output_dir = "/sdcard/Tasker/sounds/"
os.makedirs(output_dir, exist_ok=True)

for filename, text in sounds.items():
    generate_sound(text, os.path.join(output_dir, filename))

print("\nВсе звуки созданы!")
```

---

## Размещение звуков на устройстве

### На Android устройстве

1. Подключите смартфон к компьютеру через USB
2. Включите режим передачи файлов (MTP)
3. Создайте папку: `/sdcard/Tasker/sounds/`
4. Скопируйте все MP3 файлы в эту папку

### Альтернатива: через ADB

```bash
# Создать папку
adb shell mkdir -p /sdcard/Tasker/sounds/

# Загрузить файлы
adb push listening.mp3 /sdcard/Tasker/sounds/
adb push thinking.mp3 /sdcard/Tasker/sounds/
adb push done.mp3 /sdcard/Tasker/sounds/
adb push error.mp3 /sdcard/Tasker/sounds/
```

### Альтернатива: скачать на устройство

1. Загрузите звуки в Google Drive или Dropbox
2. Откройте на смартфоне и скачайте
3. Переместите файлы в `/sdcard/Tasker/sounds/` через любой файловый менеджер

---

## Проверка звуков в Tasker

1. Откройте **Tasker**
2. Создайте новый Task для тестирования
3. Добавьте действие: **Media** → **Music Play**
4. Укажите путь: `/sdcard/Tasker/sounds/listening.mp3`
5. Запустите Task
6. Убедитесь, что звук воспроизводится

---

## Рекомендации по качеству звуков

### Технические параметры

```
Формат: MP3
Битрейт: 128 kbps (достаточно для коротких звуков)
Частота дискретизации: 44100 Hz
Каналы: Mono (для экономии места) или Stereo
Длительность:
  - listening.mp3: 0.5-2 секунды
  - thinking.mp3: 1-3 секунды (опционально)
  - done.mp3: 0.5-1 секунда
  - error.mp3: 0.5-1 секунда
```

### Громкость

- Звуки должны быть достаточно громкими, но не оглушающими
- Рекомендуемая амплитуда: 70-80% от максимума
- При экспорте из Audacity используйте **Normalize** эффект

### Тон

- **listening.mp3**: восходящий тон (вопросительная интонация)
- **done.mp3**: нисходящий тон (утвердительная интонация)
- **error.mp3**: резкий нисходящий тон

---

## Быстрый старт: готовые звуки

Если вы хотите начать использовать ассистента прямо сейчас, можно временно:

1. **Пропустить создание звуков** - в Tasker просто закомментируйте действия "Play Sound"
2. **Использовать системные звуки Android**:
   ```
   /system/media/audio/notifications/pixiedust.ogg
   /system/media/audio/notifications/Tethys.ogg
   ```
3. **Создать простые звуки через gTTS** (5 минут):
   ```bash
   pip install gtts
   python -c "from gtts import gTTS; gTTS('Слушаю вас', lang='ru').save('listening.mp3')"
   ```

---

## Резюме

Вы можете выбрать любой из способов:

✅ **Самый простой**: Python + gTTS (5 минут)
✅ **Самый качественный**: AI TTS (ElevenLabs, Yandex SpeechKit)
✅ **Самый гибкий**: Audacity (создать уникальные звуки)
✅ **Самый быстрый**: Готовые звуки с freesound.org

После создания звуков:
1. Скопируйте их в `/sdcard/Tasker/sounds/`
2. Убедитесь, что пути в Tasker правильные
3. Протестируйте воспроизведение

---

## Дальнейшие шаги

- Настройте wake word (см. `docs/wake_word_setup.md`)
- Импортируйте Tasker проект (см. `tasker/Zinocha_Voice_Assistant.prj.xml`)
- Протестируйте полный цикл работы ассистента
