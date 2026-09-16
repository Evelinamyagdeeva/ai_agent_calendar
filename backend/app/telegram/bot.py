from __future__ import annotations

from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.agents.orchestrator import run_agent
from app.config import settings
from app.db.session import SessionLocal
from app.services import calendar_service
from app.services.profile import get_profile, update_profile, tzinfo

_last_reflection_date = None
scheduler = None


def _kb_pending(ids):
    if not ids:
        return None
    rows = []
    for i in ids:
        rows.append(
            [
                InlineKeyboardButton(text="Да, поставь #%s" % i, callback_data="ok:%s" % i),
                InlineKeyboardButton(text="Нет", callback_data="no:%s" % i),
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def setup_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message) -> None:
        db = SessionLocal()
        try:
            update_profile(db, telegram_chat_id=str(message.chat.id))
            await message.answer(
                "Привет. Я агент развития: цели, roadmap, календарь, привычки и рефлексия. "
                "Напиши, чем заняться — или «ногти до учёбы завтра»."
            )
        finally:
            db.close()

    @dp.message(F.text)
    async def chat(message: Message) -> None:
        db = SessionLocal()
        try:
            update_profile(db, telegram_chat_id=str(message.chat.id))
            result = run_agent(db, message.text or "", "telegram")
            await message.answer(result["reply"][:4000], reply_markup=_kb_pending(result.get("pending_ids") or []))
        except Exception as exc:
            await message.answer("Ошибка: %s" % exc)
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("ok:"))
    async def approve(cb: CallbackQuery) -> None:
        action_id = int(cb.data.split(":")[1])
        db = SessionLocal()
        try:
            created = calendar_service.apply_pending(db, action_id)
            await cb.message.answer("Поставила в календарь: %s" % created.get("title"))
        except Exception as exc:
            await cb.message.answer(str(exc))
        finally:
            db.close()
            await cb.answer()

    @dp.callback_query(F.data.startswith("no:"))
    async def reject(cb: CallbackQuery) -> None:
        action_id = int(cb.data.split(":")[1])
        db = SessionLocal()
        try:
            calendar_service.reject_pending(db, action_id)
            await cb.message.answer("Ок, не ставлю.")
        finally:
            db.close()
            await cb.answer()

    return dp


async def reflection_job() -> None:
    global _last_reflection_date
    db = SessionLocal()
    try:
        profile = get_profile(db)
        if not profile.telegram_chat_id or profile.reflection_weekday is None or not profile.reflection_time:
            return
        now = datetime.now(tzinfo(profile))
        hh, mm = profile.reflection_time.split(":")
        if now.isoweekday() != profile.reflection_weekday:
            return
        if now.hour != int(hh) or now.minute != int(mm):
            return
        if _last_reflection_date == now.date():
            return
        _last_reflection_date = now.date()
        bot = Bot(settings.telegram_bot_token)
        try:
            await bot.send_message(
                profile.telegram_chat_id,
                "Время рефлексии. Оцени энергию и продуктивность 1–10 и коротко напиши, что вышло и что нет.",
            )
        finally:
            await bot.session.close()
    finally:
        db.close()


async def run_bot() -> None:
    global scheduler
    if not settings.telegram_bot_token:
        return
    bot = Bot(settings.telegram_bot_token)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(reflection_job, "interval", minutes=1, id="reflection", replace_existing=True)
    scheduler.start()
    await setup_dispatcher().start_polling(bot)
