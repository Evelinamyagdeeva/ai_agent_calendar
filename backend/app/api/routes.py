from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_agent
from app.db.models import Goal, HabitLog, LifeArea, PendingAction, Reflection
from app.db.session import get_db
from app.integrations import google_calendar as gcal
from app.services import calendar_service, goals, habits, review
from app.services.profile import get_profile, update_profile

router = APIRouter(prefix="/api")


class ChatIn(BaseModel):
    message: str
    channel: str = "web"


class ProfileIn(BaseModel):
    display_name: Optional[str] = None
    timezone: Optional[str] = None
    work_start: Optional[str] = None
    work_end: Optional[str] = None
    work_days: Optional[str] = None
    reflection_weekday: Optional[int] = None
    reflection_time: Optional[str] = None
    onboarding_complete: Optional[bool] = None


class AreaIn(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None


class GoalIn(BaseModel):
    title: str
    deadline: date
    area_id: Optional[int] = None
    specific: Optional[str] = None
    measurable: Optional[str] = None
    achievable: Optional[str] = None
    relevant: Optional[str] = None
    success_criteria: Optional[str] = None


class StageIn(BaseModel):
    title: str
    description: Optional[str] = None
    brief: Optional[str] = None
    deadline: Optional[date] = None
    status: Optional[str] = None


class HabitIn(BaseModel):
    title: str
    cadence: str = "daily"
    area_id: Optional[int] = None
    goal_id: Optional[int] = None
    notes: Optional[str] = None


class HabitLogIn(BaseModel):
    day: date
    done: bool = True
    note: Optional[str] = None


class ReflectionIn(BaseModel):
    week_start: date
    energy: int
    productivity: int
    text: Optional[str] = None


class EventProposeIn(BaseModel):
    title: str
    start: str
    end: str
    description: Optional[str] = None
    area_id: Optional[int] = None
    recurrence: Optional[list] = None


def _area(a: LifeArea) -> dict:
    return {"id": a.id, "name": a.name, "description": a.description, "color": a.color, "is_custom": a.is_custom}


def _goal(g: Goal) -> dict:
    return {
        "id": g.id,
        "area_id": g.area_id,
        "title": g.title,
        "deadline": g.deadline.isoformat(),
        "status": g.status,
        "specific": g.specific,
        "measurable": g.measurable,
        "achievable": g.achievable,
        "relevant": g.relevant,
        "success_criteria": g.success_criteria,
        "stages": [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "brief": s.brief,
                "deadline": s.deadline.isoformat() if s.deadline else None,
                "status": s.status,
                "preserved": s.preserved,
                "order_index": s.order_index,
                "tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "details": t.details,
                        "status": t.status,
                        "due_date": t.due_date.isoformat() if t.due_date else None,
                        "preserved": t.preserved,
                    }
                    for t in s.tasks
                ],
            }
            for s in sorted(g.stages, key=lambda x: x.order_index)
        ],
    }


@router.get("/me")
def me(db: Session = Depends(get_db)):
    p = get_profile(db)
    return {
        "id": p.id,
        "display_name": p.display_name,
        "timezone": p.timezone,
        "work_start": p.work_start,
        "work_end": p.work_end,
        "work_days": p.work_days,
        "onboarding_complete": p.onboarding_complete,
        "reflection_weekday": p.reflection_weekday,
        "reflection_time": p.reflection_time,
        "google_connected": gcal.is_connected(),
        "telegram_chat_id": p.telegram_chat_id,
    }


@router.put("/me")
def save_me(body: ProfileIn, db: Session = Depends(get_db)):
    p = update_profile(db, **body.model_dump(exclude_unset=True))
    return {"ok": True, "timezone": p.timezone}


@router.post("/google/connect")
def google_connect(db: Session = Depends(get_db)):
    try:
        gcal.start_oauth()
        update_profile(db, google_connected=True)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.get("/areas")
def areas(db: Session = Depends(get_db)):
    return [_area(a) for a in goals.list_areas(db)]


@router.post("/areas")
def create_area(body: AreaIn, db: Session = Depends(get_db)):
    return _area(goals.upsert_area(db, body.name, body.description, body.id))


@router.get("/goals")
def list_goals(db: Session = Depends(get_db)):
    rows = db.query(Goal).order_by(Goal.id.desc()).all()
    return [_goal(g) for g in rows]


@router.post("/goals")
def add_goal(body: GoalIn, db: Session = Depends(get_db)):
    g = goals.create_goal(db, **body.model_dump())
    return _goal(g)


@router.post("/goals/{goal_id}/stages")
def add_stage(goal_id: int, body: StageIn, db: Session = Depends(get_db)):
    return {"id": goals.upsert_stage(db, goal_id, body.model_dump()).id}


@router.patch("/stages/{stage_id}")
def patch_stage(stage_id: int, status: str, db: Session = Depends(get_db)):
    return {"id": goals.set_stage_status(db, stage_id, status).id, "status": status}


@router.patch("/tasks/{task_id}")
def patch_task(task_id: int, status: str, db: Session = Depends(get_db)):
    return {"id": goals.set_task_status(db, task_id, status).id, "status": status}


@router.get("/habits")
def list_habits(db: Session = Depends(get_db)):
    today = date.today()
    out = []
    for h in habits.list_habits(db):
        log = db.query(HabitLog).filter(HabitLog.habit_id == h.id, HabitLog.day == today).first()
        out.append(
            {
                "id": h.id,
                "title": h.title,
                "cadence": h.cadence,
                "notes": h.notes,
                "today_done": bool(log and log.done),
            }
        )
    return out


@router.post("/habits")
def add_habit(body: HabitIn, db: Session = Depends(get_db)):
    h = habits.create_habit(db, **body.model_dump())
    return {"id": h.id}


@router.post("/habits/{habit_id}/log")
def habit_log(habit_id: int, body: HabitLogIn, db: Session = Depends(get_db)):
    return {"id": habits.log_habit(db, habit_id, body.day, body.done, body.note).id}


@router.get("/reflections")
def reflections(db: Session = Depends(get_db)):
    rows = db.query(Reflection).order_by(Reflection.id.desc()).limit(12).all()
    return [
        {
            "id": r.id,
            "week_start": r.week_start.isoformat(),
            "energy": r.energy,
            "productivity": r.productivity,
            "text": r.text,
        }
        for r in rows
    ]


@router.post("/reflections")
def add_reflection(body: ReflectionIn, db: Session = Depends(get_db)):
    r = habits.add_reflection(db, body.week_start, body.energy, body.productivity, body.text)
    return {"id": r.id}


@router.get("/week")
def week(db: Session = Depends(get_db)):
    profile = get_profile(db)
    tz = calendar_service.tzinfo(profile)
    now = datetime.now(tz)
    start = now - timedelta(days=now.weekday())
    end = start + timedelta(days=7)
    events = []
    try:
        if gcal.is_connected():
            events = gcal.list_events(start, end)
    except Exception as exc:
        events = [{"title": f"Ошибка календаря: {exc}", "start": None, "end": None}]
    pending = db.query(PendingAction).filter(PendingAction.status == "pending").all()
    free = []
    try:
        if gcal.is_connected():
            free = calendar_service.free_slots(profile, now, now + timedelta(days=7), 60)
    except Exception as exc:
        events.append({"title": f"Ошибка свободных слотов: {exc}", "start": None, "end": None})
    return {
        "facts": review.collect_week_facts(db),
        "events": events,
        "free": free,
        "pending": [{"id": p.id, "preview": p.preview, "payload": p.payload} for p in pending],
        "reviews": [
            {"id": r.id, "week_start": r.week_start.isoformat(), "content": r.content, "pace_notes": r.pace_notes}
            for r in review.latest_reviews(db)
        ],
    }


@router.post("/calendar/propose")
def propose(body: EventProposeIn, db: Session = Depends(get_db)):
    profile = get_profile(db)
    payload = body.model_dump()
    payload["timezone"] = profile.timezone
    start, end = datetime.fromisoformat(body.start), datetime.fromisoformat(body.end)
    payload["conflicts"] = calendar_service.conflicts(profile, start, end)
    payload["alternatives"] = calendar_service.alternatives(
        profile, start, max(int((end - start).total_seconds() / 60), 30)
    )
    action = calendar_service.propose_event(db, payload)
    return {"id": action.id, "preview": action.preview, "conflicts": payload["conflicts"], "alternatives": payload["alternatives"]}


@router.post("/pending/{action_id}/approve")
def approve(action_id: int, db: Session = Depends(get_db)):
    try:
        return calendar_service.apply_pending(db, action_id)
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/pending/{action_id}/reject")
def reject(action_id: int, db: Session = Depends(get_db)):
    calendar_service.reject_pending(db, action_id)
    return {"ok": True}


@router.post("/chat")
def chat(body: ChatIn, db: Session = Depends(get_db)):
    if not body.message.strip():
        raise HTTPException(400, "Пустое сообщение")
    try:
        return run_agent(db, body.message, body.channel)
    except Exception as exc:
        return {"reply": "Ошибка агента: %s" % exc, "pending_ids": []}


@router.post("/review/generate")
def generate_review(db: Session = Depends(get_db)):
    facts = review.collect_week_facts(db)
    try:
        result = run_agent(
            db,
            "Собери недельный обзор по текущим фактам недели, сохрани его через save_weekly_review, "
            "отметь сильные стороны и просевшие сферы, дай советы по балансу и темпу целей.",
            "web",
        )
    except Exception as exc:
        result = {"reply": "Не удалось собрать обзор: %s" % exc, "pending_ids": []}
    return {"facts": facts, **result}
