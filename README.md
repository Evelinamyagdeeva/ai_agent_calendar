# AI Personal Development Agent

Локальный персональный агент развития: **Telegram + веб**, SMART-цели, roadmap, привычки, рефлексия и Google Calendar.

Данные остаются на твоей машине (SQLite в `data/`). Секреты (`.env`, токены Google, база) в git не попадают.

Репозиторий: https://github.com/Evelinamyagdeeva/ai_agent_calendar

## Что умеет

- Онбординг: сферы жизни и SMART-цели (дедлайн обязателен).
- Roadmap по цели: этапы, задачи, ТЗ; правки вручную в вебе или через агента. Выполненное не теряется при пересборке плана.
- Календарь: читает занятость в Google; предлагает слот; пишет событие только после «да».
- Свободные фразы вроде «ногти до учёбы завтра» — уточнение, конфликты и альтернативы.
- Привычки, рефлексия 1–10 и недельный обзор.

## Что нужно заранее

1. Python 3.9+ (на Mac часто стоит 3.9 из Xcode).
2. Ключ [Polza](https://polza.ai) (`POLZA_AI_API_KEY`). Модель по умолчанию: `deepseek/deepseek-v4.1-flash`. Сайт Polza должен открываться в браузере; иначе бот не достучится до LLM (VPN/фильтр).
3. Токен Telegram-бота от [@BotFather](https://t.me/BotFather) — без него веб работает, бот нет.
4. Google Calendar (по желанию): OAuth **Desktop app**, включённый **Google Calendar API**, testers = твой Gmail.

Скопируй `.env_example` → `.env` и заполни пустые поля. **Не коммить `.env`.**

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
Проверка: http://127.0.0.1:8000/health  

Остановка: в терминале **Ctrl+C**. Если порт занят: `lsof -i :8000` и `kill <PID>`.

Telegram поднимается вместе с FastAPI, если задан `TELEGRAM_BOT_TOKEN` (long polling). В логе будет строка вида `Telegram polling as @имя_бота`. Напиши боту `/start`.

Опционально Vite (нужен Node): `cd frontend && npm install && npm run dev` → http://127.0.0.1:5173  
Без Node UI отдаётся из `frontend/dist` на порту 8000.

## Google Calendar

1. [Google Cloud Console](https://console.cloud.google.com/) — личный **проект**, организацию создавать не нужно.
2. Включи [Google Calendar API](https://console.developers.google.com/apis/api/calendar-json.googleapis.com/overview).
3. OAuth: тип пользователей **External**, статус **Testing**. В **Test users** добавь свой Gmail.
4. Credentials → OAuth client ID → **Desktop app**.
5. Положи JSON в корень как `credentials.json` **или** пропиши `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` в `.env`.
6. Запусти сервер → Настройки → **Подключить Google Calendar**.

Scopes: `calendar.readonly`, `calendar.events`.  
Запись в календарь только после подтверждения в вебе или в Telegram.

Если ошибка 403 `access_denied` — email не в Test users.  
Если API disabled — Calendar API ещё не включён в этом проекте.

## Как пользоваться

- Чат агента в вебе или в Telegram: цели, слоты, привычки.
- «Карта» и «Цели» — ручное редактирование сфер, roadmap и задач.
- «Неделя» — события Google, черновики слотов, обзор.
- Привычки отмечаются каждый день.
- В настройках: часовой пояс, рабочие часы, день и время рефлексии.

## Структура

```
backend/app/     FastAPI, агенты, SQLite, Google, Telegram
frontend/        React-исходники (Vite) + dist для запуска без Node
data/            локальная БД и google_token.json (не в git)
```

## Если что-то не работает

| Симптом | Что проверить |
|---|---|
| Internal Server Error на сайте | Лог uvicorn; неделя больше не должна падать из-за Google |
| Бот молчит | Сервер запущен, токен в `.env`, в логе есть `Telegram polling as @...`, `/start` |
| Таймаут Polza | https://polza.ai в браузере; VPN; ключ в `.env` |
| Google не подключается | Desktop OAuth, Test users, Calendar API Enable |
