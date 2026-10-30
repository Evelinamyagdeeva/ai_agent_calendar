from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.db.models import CalendarLink, PendingAction, UserProfile
from app.integrations import google_calendar as gcal


def get_profile(db: Session) -> UserProfile:
    profile = db.query(UserProfile).first()
    if not profile:
        profile = UserProfile()
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def update_profile(db: Session, **kwargs) -> UserProfile:
    profile = get_profile(db)
    for key, value in kwargs.items():
        if not hasattr(profile, key):
            continue
        if value is None and key not in {"reflection_weekday", "reflection_time"}:
            continue
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


def tzinfo(profile: UserProfile) -> ZoneInfo:
    try:
        return ZoneInfo(profile.timezone)
    except Exception:
        return ZoneInfo("Europe/Moscow")


def parse_hhmm(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))


def work_windows(profile: UserProfile, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    tz = tzinfo(profile)
    days = {int(x) for x in profile.work_days.split(",") if x}
    windows = []
    day = start.astimezone(tz).date()
    last = end.astimezone(tz).date()
    ws, we = parse_hhmm(profile.work_start), parse_hhmm(profile.work_end)
    while day <= last:
        if day.isoweekday() in days:
            a = datetime.combine(day, ws, tzinfo=tz)
            b = datetime.combine(day, we, tzinfo=tz)
            windows.append((max(a, start.astimezone(tz)), min(b, end.astimezone(tz))))
        day += timedelta(days=1)
    return [(a, b) for a, b in windows if b > a]


def _parse_dt(value: str, tz: ZoneInfo) -> datetime:
    raw = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if raw.tzinfo is None:
        return raw.replace(tzinfo=tz)
    return raw.astimezone(tz)


def busy_slots(profile: UserProfile, start: datetime, end: datetime) -> list[dict]:
    if not gcal.is_connected():
        return []
    try:
        events = gcal.list_events(start, end)
    except Exception:
        return []
    tz = tzinfo(profile)
    busy = []
    for ev in events:
        if not ev.get("start") or not ev.get("end"):
            continue
        busy.append(
            {
                **ev,
                "start_dt": _parse_dt(ev["start"], tz) if "T" in ev["start"] else datetime.combine(
                    date.fromisoformat(ev["start"]), time(0, 0), tzinfo=tz
                ),
                "end_dt": _parse_dt(ev["end"], tz) if "T" in str(ev["end"]) else datetime.combine(
                    date.fromisoformat(ev["end"]), time(23, 59), tzinfo=tz
                ),
            }
        )
    return busy


def free_slots(profile: UserProfile, start: datetime, end: datetime, duration_min: int = 60) -> list[dict]:
    duration = timedelta(minutes=duration_min)
    busy = busy_slots(profile, start, end)
    free = []
    for win_start, win_end in work_windows(profile, start, end):
        cursor = win_start
        day_busy = sorted(
            [b for b in busy if b["start_dt"] < win_end and b["end_dt"] > win_start],
            key=lambda x: x["start_dt"],
        )
        for b in day_busy:
            gap_end = min(b["start_dt"], win_end)
            if gap_end - cursor >= duration:
                free.append({"start": cursor.isoformat(), "end": gap_end.isoformat()})
            cursor = max(cursor, b["end_dt"])
        if win_end - cursor >= duration:
            free.append({"start": cursor.isoformat(), "end": win_end.isoformat()})
    return free[:20]


def conflicts(profile: UserProfile, start: datetime, end: datetime) -> list[dict]:
    hits = []
    for b in busy_slots(profile, start - timedelta(hours=12), end + timedelta(hours=12)):
        if b["start_dt"] < end and b["end_dt"] > start:
            hits.append({"title": b["title"], "start": b["start"], "end": b["end"]})
    return hits


def alternatives(profile: UserProfile, start: datetime, duration_min: int) -> list[dict]:
    horizon_end = start + timedelta(days=7)
    alts = []
    for slot in free_slots(profile, start, horizon_end, duration_min):
        slot_start = datetime.fromisoformat(slot["start"])
        if slot_start >= start:
            alts.append(
                {
                    "start": slot_start.isoformat(),
                    "end": (slot_start + timedelta(minutes=duration_min)).isoformat(),
                }
            )
        if len(alts) >= 3:
            break
    return alts


def propose_event(db: Session, payload: dict) -> PendingAction:
    preview = (
        f"{payload.get('title')} | {payload.get('start')} — {payload.get('end')}"
        f"{' (повтор)' if payload.get('recurrence') else ''}"
    )
    action = PendingAction(kind="calendar_event", payload=payload, preview=preview, status="pending")
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def apply_pending(db: Session, action_id: int) -> dict:
    action = db.get(PendingAction, action_id)
    if not action or action.status != "pending":
        raise ValueError("Нет ожидающего действия")
    created = gcal.create_event(action.payload)
    action.status = "approved"
    db.add(
        CalendarLink(
            google_event_id=created["id"],
            title=created.get("title") or action.payload.get("title") or "",
            area_id=action.payload.get("area_id"),
            goal_id=action.payload.get("goal_id"),
            habit_id=action.payload.get("habit_id"),
        )
    )
    db.commit()
    return created


def reject_pending(db: Session, action_id: int) -> None:
    action = db.get(PendingAction, action_id)
    if action:
        action.status = "rejected"
        db.commit()
