from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.db.models import Habit, HabitLog, Insight, Reflection, WeeklyReview


def list_habits(db: Session) -> list[Habit]:
    return db.query(Habit).filter(Habit.active.is_(True)).all()


def create_habit(db: Session, title: str, cadence: str = "daily", **kwargs) -> Habit:
    habit = Habit(title=title, cadence=cadence, **kwargs)
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit


def log_habit(db: Session, habit_id: int, day: date, done: bool = True, note: str | None = None) -> HabitLog:
    existing = db.query(HabitLog).filter(HabitLog.habit_id == habit_id, HabitLog.day == day).first()
    if existing:
        existing.done = done
        existing.note = note
        db.commit()
        db.refresh(existing)
        return existing
    log = HabitLog(habit_id=habit_id, day=day, done=done, note=note)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def add_reflection(db: Session, week_start: date, energy: int, productivity: int, text: str | None) -> Reflection:
    item = Reflection(week_start=week_start, energy=energy, productivity=productivity, text=text)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remember(db: Session, content: str, kind: str = "fact") -> Insight:
    insight = Insight(kind=kind, content=content)
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight


def save_review(db: Session, week_start: date, content: str, pace_notes: str | None) -> WeeklyReview:
    review = WeeklyReview(week_start=week_start, content=content, pace_notes=pace_notes)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
