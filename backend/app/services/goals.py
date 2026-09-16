from __future__ import annotations

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Goal, LifeArea, RoadmapStage, StageTask

DEFAULT_AREAS = [
    ("Карьера и учёба", "#6c8cff"),
    ("Здоровье", "#3ecf8e"),
    ("Отношения", "#ff8fab"),
    ("Финансы", "#ffc14d"),
    ("Творчество", "#c084fc"),
]


def seed_areas(db: Session) -> None:
    if db.query(LifeArea).count():
        return
    for name, color in DEFAULT_AREAS:
        db.add(LifeArea(name=name, color=color, is_custom=False))
    db.commit()


def list_areas(db: Session) -> list[LifeArea]:
    seed_areas(db)
    return db.query(LifeArea).all()


def upsert_area(db: Session, name: str, description: str | None = None, area_id: int | None = None) -> LifeArea:
    if area_id:
        area = db.get(LifeArea, area_id)
        if not area:
            raise ValueError("Сфера не найдена")
        area.name = name
        if description is not None:
            area.description = description
    else:
        area = LifeArea(name=name, description=description, is_custom=True)
        db.add(area)
    db.commit()
    db.refresh(area)
    return area


def create_goal(
    db: Session,
    title: str,
    deadline: date,
    area_id: Optional[int] = None,
    specific: str | None = None,
    measurable: str | None = None,
    achievable: str | None = None,
    relevant: str | None = None,
    success_criteria: str | None = None,
) -> Goal:
    goal = Goal(
        title=title,
        deadline=deadline,
        area_id=area_id,
        specific=specific,
        measurable=measurable,
        achievable=achievable,
        relevant=relevant,
        success_criteria=success_criteria,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def update_goal(db: Session, goal_id: int, **kwargs) -> Goal:
    goal = db.get(Goal, goal_id)
    if not goal:
        raise ValueError("Цель не найдена")
    for key, value in kwargs.items():
        if hasattr(goal, key) and value is not None:
            setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return goal


def replace_roadmap(db: Session, goal_id: int, stages: list[dict]) -> list[RoadmapStage]:
    goal = db.get(Goal, goal_id)
    if not goal:
        raise ValueError("Цель не найдена")
    for stage in goal.stages:
        done_tasks = [t for t in stage.tasks if t.status == "done"]
        if stage.status == "done" or done_tasks:
            stage.preserved = True
            stage.status = "done" if stage.status == "done" else stage.status
            for t in done_tasks:
                t.preserved = True
        else:
            db.delete(stage)
    for idx, item in enumerate(stages):
        stage = RoadmapStage(
            goal_id=goal_id,
            title=item["title"],
            description=item.get("description"),
            brief=item.get("brief"),
            deadline=date.fromisoformat(item["deadline"]) if item.get("deadline") else None,
            order_index=idx,
            status="planned",
        )
        db.add(stage)
        db.flush()
        for task in item.get("tasks") or []:
            db.add(
                StageTask(
                    stage_id=stage.id,
                    title=task["title"],
                    details=task.get("details"),
                    due_date=date.fromisoformat(task["due_date"]) if task.get("due_date") else None,
                )
            )
    db.commit()
    return db.query(RoadmapStage).filter(RoadmapStage.goal_id == goal_id).order_by(RoadmapStage.order_index).all()


def set_task_status(db: Session, task_id: int, status: str) -> StageTask:
    task = db.get(StageTask, task_id)
    if not task:
        raise ValueError("Задача не найдена")
    task.status = status
    task.completed_at = datetime.utcnow() if status == "done" else None
    db.commit()
    db.refresh(task)
    return task


def set_stage_status(db: Session, stage_id: int, status: str) -> RoadmapStage:
    stage = db.get(RoadmapStage, stage_id)
    if not stage:
        raise ValueError("Этап не найден")
    stage.status = status
    stage.completed_at = datetime.utcnow() if status == "done" else None
    db.commit()
    db.refresh(stage)
    return stage


def upsert_stage(db: Session, goal_id: int, data: dict, stage_id: int | None = None) -> RoadmapStage:
    if stage_id:
        stage = db.get(RoadmapStage, stage_id)
        if not stage:
            raise ValueError("Этап не найден")
        for key in ("title", "description", "brief", "status"):
            if data.get(key) is not None:
                setattr(stage, key, data[key])
        if data.get("deadline"):
            stage.deadline = date.fromisoformat(data["deadline"])
    else:
        count = db.query(RoadmapStage).filter(RoadmapStage.goal_id == goal_id).count()
        stage = RoadmapStage(
            goal_id=goal_id,
            title=data["title"],
            description=data.get("description"),
            brief=data.get("brief"),
            deadline=date.fromisoformat(data["deadline"]) if data.get("deadline") else None,
            order_index=count,
        )
        db.add(stage)
    db.commit()
    db.refresh(stage)
    return stage
