# AI Personal Development Agent

Локальный агент: Telegram + веб, Google Calendar, цели SMART, roadmap, привычки и недельные обзоры.
Данные лежат только на этой машине (SQLite в `data/`).

## Что нужно

1. Ключ [Polza](https://polza.ai) — уже в `.env`.
2. Токен Telegram-бота от [@BotFather](https://t.me/BotFather).
3. Google Cloud OAuth **Desktop app**:
   - APIs: Google Calendar API
   - scopes: `calendar.readonly`, `calendar.events`
   - скачай `credentials.json` в корень репозитория **или** пропиши `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`

Скопируй `.env_example` → `.env` и заполни пустые поля.

```
POLZA_AI_BASE_URL=https://polza.ai/api/v1
POLZA_AI_MODEL_NAME=deepseek/deepseek-v4.1-flash
```

## Запуск

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
./backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Веб и API: http://127.0.0.1:8000  

Опционально Vite (если установлен Node): `cd frontend && npm install && npm run dev` → http://127.0.0.1:5173  

В настройках веб-приложения нажми «Подключить Google Calendar» — откроется браузер OAuth. После этого бот и веб читают занятость и предлагают слоты; запись в календарь только после подтверждения.

Telegram поднимается вместе с FastAPI, если задан `TELEGRAM_BOT_TOKEN` (long polling).

## Как пользоваться

- Онбординг и свободные фразы — в чате агента или в Telegram.
- Сферы, цели, этапы можно править вручную на страницах «Карта» и «Цели».
- Привычки отмечаются каждый день.
- Время рефлексии задаётся в настройках; бот напомнит в выбранный день и час.
