from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import Goal, HabitLog, Reflection, StageTask, WeeklyReview
from app.services import calendar_service
from app.services.goals import list_areas
from app.services.profile import get_profile, tzinfo


def week_bounds(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def goal_pace(db: Session, goal: Goal) -> dict:
    stages = goal.stages
    total = max(len(stages), 1)
    done = len([s for s in stages if s.status == "done"])
    today = date.today()
    remaining_days = (goal.deadline - today).days
    ratio = done / total
    expected = 0.0
    created = goal.created_at.date() if goal.created_at else today
    span = max((goal.deadline - created).days, 1)
    elapsed = max((today - created).days, 0)
    expected = min(elapsed / span, 1.0)
    on_track = ratio + 0.05 >= expected
    return {
        "goal_id": goal.id,
        "title": goal.title,
        "deadline": goal.deadline.isoformat(),
        "stages_done": done,
        "stages_total": total,
        "progress": round(ratio, 2),
        "expected": round(expected, 2),
        "remaining_days": remaining_days,
        "on_track": on_track,
        "forecast": "успеешь в текущем темпе" if on_track and remaining_days >= 0 else "темп отстаёт или дедлайн близко",
    }


def collect_week_facts(db: Session, week_start: date | None = None) -> dict:
    profile = get_profile(db)
    tz = tzinfo(profile)
    today = datetime.now(tz).date()
    start, end = week_bounds(week_start or today)
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=tz)
    end_dt = datetime.combine(end, datetime.max.time(), tzinfo=tz)
    events = []
    try:
        events = calendar_service.busy_slots(profile, start_dt, end_dt)
    except Exception:
        events = []
    areas = {a.id: a.name for a in list_areas(db)}
    hours_by_area: dict[str, float] = {}
    for ev in events:
        hours = (ev["end_dt"] - ev["start_dt"]).total_seconds() / 3600
        hours_by_area["календарь"] = hours_by_area.get("календарь", 0) + hours
    tasks_done = (
        db.query(StageTask)
        .filter(StageTask.status == "done", StageTask.completed_at.is_not(None))
        .all()
    )
    week_tasks = [t for t in tasks_done if t.completed_at and start <= t.completed_at.date() <= end]
    reflections = db.query(Reflection).filter(Reflection.week_start == start).all()
    logs = db.query(HabitLog).filter(HabitLog.day >= start, HabitLog.day <= end).all()
    paces = [goal_pace(db, g) for g in db.query(Goal).filter(Goal.status == "active").all()]
    return {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "event_count": len(events),
        "hours_logged": round(sum(hours_by_area.values()), 1),
        "hours_by_bucket": {k: round(v, 1) for k, v in hours_by_area.items()},
        "tasks_done": [{"id": t.id, "title": t.title} for t in week_tasks],
        "habit_checks": len([x for x in logs if x.done]),
        "reflections": [
            {"energy": r.energy, "productivity": r.productivity, "text": r.text} for r in reflections
        ],
        "goal_pace": paces,
        "areas": areas,
    }


def latest_reviews(db: Session, limit: int = 4) -> list[WeeklyReview]:
    return db.query(WeeklyReview).order_by(WeeklyReview.created_at.desc()).limit(limit).all()
