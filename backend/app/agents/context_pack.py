from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import Goal, Insight, PendingAction, Reflection
from app.integrations import google_calendar as gcal
from app.services import calendar_service, goals, habits, review
from app.services.profile import get_profile


def serialize(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if hasattr(obj, "__dict__") and hasattr(obj, "id"):
        data = {}
        for k, v in obj.__dict__.items():
            if k.startswith("_"):
                continue
            data[k] = serialize(v)
        return data
    if isinstance(obj, list):
        return [serialize(x) for x in obj]
    return obj


def build_context_pack(db: Session) -> dict:
    profile = get_profile(db)
    tz = calendar_service.tzinfo(profile)
    now = datetime.now(tz)
    events = []
    try:
        if gcal.is_connected():
            events = gcal.list_events(now, now + timedelta(days=14))
    except Exception as exc:
        events = [{"error": str(exc)}]
    pending = (
        db.query(PendingAction)
        .filter(PendingAction.status == "pending")
        .order_by(PendingAction.id.desc())
        .limit(5)
        .all()
    )
    insights = db.query(Insight).order_by(Insight.id.desc()).limit(12).all()
    reflections = db.query(Reflection).order_by(Reflection.id.desc()).limit(4).all()
    goal_rows = db.query(Goal).filter(Goal.status == "active").all()
    goals_payload = []
    for g in goal_rows:
        goals_payload.append(
            {
                "id": g.id,
                "title": g.title,
                "deadline": g.deadline.isoformat(),
                "area_id": g.area_id,
                "specific": g.specific,
                "measurable": g.measurable,
                "status": g.status,
                "stages": [
                    {
                        "id": s.id,
                        "title": s.title,
                        "status": s.status,
                        "deadline": s.deadline.isoformat() if s.deadline else None,
                        "preserved": s.preserved,
                        "brief": s.brief,
                        "tasks": [
                            {
                                "id": t.id,
                                "title": t.title,
                                "status": t.status,
                                "preserved": t.preserved,
                            }
                            for t in s.tasks
                        ],
                    }
                    for s in g.stages
                ],
                "pace": review.goal_pace(db, g),
            }
        )
    return {
        "now": now.isoformat(),
        "profile": {
            "display_name": profile.display_name,
            "timezone": profile.timezone,
            "work_start": profile.work_start,
            "work_end": profile.work_end,
            "work_days": profile.work_days,
            "onboarding_complete": profile.onboarding_complete,
            "reflection_weekday": profile.reflection_weekday,
            "reflection_time": profile.reflection_time,
            "google_connected": gcal.is_connected(),
        },
        "areas": [{"id": a.id, "name": a.name, "description": a.description} for a in goals.list_areas(db)],
        "goals": goals_payload,
        "habits": [
            {"id": h.id, "title": h.title, "cadence": h.cadence, "suggested": h.suggested}
            for h in habits.list_habits(db)
        ],
        "upcoming_events": events[:40],
        "insights": [{"kind": i.kind, "content": i.content} for i in insights],
        "reflections": [
            {"energy": r.energy, "productivity": r.productivity, "text": r.text, "week_start": r.week_start.isoformat()}
            for r in reflections
        ],
        "pending": [{"id": p.id, "preview": p.preview, "payload": p.payload} for p in pending],
        "week_facts": review.collect_week_facts(db),
    }
