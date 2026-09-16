from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.services import calendar_service, goals, habits, review
from app.services.profile import get_profile, update_profile


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def execute_tool(db: Session, name: str, args: dict) -> str:
    profile = get_profile(db)
    try:
        if name == "update_profile":
            update_profile(db, **args)
            return "Профиль обновлён"
        if name == "upsert_area":
            area = goals.upsert_area(db, args["name"], args.get("description"), args.get("area_id"))
            return json.dumps({"id": area.id, "name": area.name})
        if name == "create_goal":
            goal = goals.create_goal(
                db,
                title=args["title"],
                deadline=date.fromisoformat(args["deadline"]),
                area_id=args.get("area_id"),
                specific=args.get("specific"),
                measurable=args.get("measurable"),
                achievable=args.get("achievable"),
                relevant=args.get("relevant"),
                success_criteria=args.get("success_criteria"),
            )
            return json.dumps({"id": goal.id, "title": goal.title})
        if name == "replace_roadmap":
            stages = goals.replace_roadmap(db, args["goal_id"], args["stages"])
            return json.dumps([{"id": s.id, "title": s.title} for s in stages])
        if name == "find_free_slots":
            days = int(args.get("days") or 7)
            duration = int(args.get("duration_min") or 60)
            tz = calendar_service.tzinfo(profile)
            now = datetime.now(tz)
            slots = calendar_service.free_slots(profile, now, now + timedelta(days=days), duration)
            return json.dumps(slots)
        if name == "check_conflicts":
            start, end = _dt(args["start"]), _dt(args["end"])
            hits = calendar_service.conflicts(profile, start, end)
            duration = max(int((end - start).total_seconds() / 60), 30)
            alts = calendar_service.alternatives(profile, start, duration)
            return json.dumps({"conflicts": hits, "alternatives": alts})
        if name == "propose_calendar_event":
            payload = dict(args)
            payload["timezone"] = profile.timezone
            start, end = _dt(payload["start"]), _dt(payload["end"])
            payload["conflicts"] = calendar_service.conflicts(profile, start, end)
            duration = max(int((end - start).total_seconds() / 60), 30)
            payload["alternatives"] = calendar_service.alternatives(profile, start, duration)
            action = calendar_service.propose_event(db, payload)
            return json.dumps(
                {
                    "pending_id": action.id,
                    "preview": action.preview,
                    "conflicts": payload["conflicts"],
                    "alternatives": payload["alternatives"],
                    "needs_approval": True,
                }
            )
        if name == "create_habit":
            habit = habits.create_habit(
                db,
                title=args["title"],
                cadence=args.get("cadence") or "daily",
                area_id=args.get("area_id"),
                goal_id=args.get("goal_id"),
                notes=args.get("notes"),
                suggested=bool(args.get("suggested")),
            )
            return json.dumps({"id": habit.id, "title": habit.title})
        if name == "log_habit":
            log = habits.log_habit(
                db,
                args["habit_id"],
                date.fromisoformat(args["day"]),
                args.get("done", True),
                args.get("note"),
            )
            return json.dumps({"id": log.id, "done": log.done})
        if name == "save_reflection":
            item = habits.add_reflection(
                db,
                date.fromisoformat(args["week_start"]),
                int(args["energy"]),
                int(args["productivity"]),
                args.get("text"),
            )
            return json.dumps({"id": item.id})
        if name == "save_weekly_review":
            item = habits.save_review(
                db,
                date.fromisoformat(args["week_start"]),
                args["content"],
                args.get("pace_notes"),
            )
            return json.dumps({"id": item.id})
        if name == "remember":
            item = habits.remember(db, args["content"], args.get("kind") or "fact")
            return json.dumps({"id": item.id})
        return f"Неизвестный tool: {name}"
    except Exception as exc:
        return f"Ошибка tool {name}: {exc}"
