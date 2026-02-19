# Parakeet V3 MP3 Transcriber (Desktop MVP)

Desktop-приложение на Python для транскрибации аудио в текст с помощью модели NVIDIA Parakeet V3 (`nvidia/parakeet-tdt-0.6b-v3`).

## Что умеет

- Выбор `mp3/wav/flac` файла через GUI (`tkinter`)
- Транскрибация в текст через NeMo + Parakeet V3
- Потоковая обработка чанками (низкое потребление RAM)
- Автовыбор устройства: `CUDA` -> `MPS` (Apple GPU) -> `CPU`
- Сохранение результата в `.txt`

## Требования

- Python `3.10+` (я использовал пайтон 3.11)
- `ffmpeg` в `PATH` (обязательно)

## Запуск с нуля на macOS

1. Откройте Terminal и перейдите в папку проекта:

```bash
cd /путь/к/analizatorMAIN
```

2. Установите `ffmpeg` (если еще не установлен):

```bash
brew install ffmpeg
```

3. Создайте и активируйте виртуальное окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

4. Обновите `pip` и установите зависимости:

```bash
python -m pip install -U pip
python -m pip install -r requirements.txt
```

5. Запустите приложение:

```bash
python app.py
```

## Запуск с нуля на Windows

1. Откройте `PowerShell` и перейдите в папку проекта:

```powershell
cd C:\путь\к\analizatorMAIN
```

2. Установите `ffmpeg` (это все доп программы winget, choco которые нужно заранее установить чтобы можно было ставить зависимости через них):

```powershell
winget install Gyan.FFmpeg
```

или

```powershell
choco install ffmpeg
```

3. Создайте и активируйте виртуальное окружение:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
```

4. Установите зависимости:

```powershell
python -m pip install -U pip
python -m pip install -r requirements.txt
```

5. Запустите приложение:

```powershell
python app.py
```

## Повторный запуск

macOS:

```bash
cd /путь/к/analizatorMAIN
source .venv/bin/activate
python app.py
```

Windows (PowerShell):

```powershell
cd C:\path\to\analizatorMAIN
.venv\Scripts\Activate.ps1
python app.py
```

## Частые проблемы

- Ошибка `ffmpeg not found`:
  - проверьте `ffmpeg -version`
  - перезапустите терминал после установки ffmpeg
- Ошибка `object.__init__() takes exactly one argument`:
  - обычно это конфликт глобальных пакетов
  - решение: удалить `.venv`, создать заново и переустановить зависимости
- Первый запуск долгий:
  - модель скачивается с Hugging Face, это нормально
