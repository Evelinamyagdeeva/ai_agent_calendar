from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class UserProfile(Base):
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), default="Я")
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    work_start: Mapped[str] = mapped_column(String(8), default="09:00")
    work_end: Mapped[str] = mapped_column(String(8), default="18:00")
    work_days: Mapped[str] = mapped_column(String(32), default="1,2,3,4,5")
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    reflection_weekday: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reflection_time: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    google_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LifeArea(Base):
    __tablename__ = "life_areas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(16), default="#7c6cff")
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    goals: Mapped[list["Goal"]] = relationship(back_populates="area")
    habits: Mapped[list["Habit"]] = relationship(back_populates="area")


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    area_id: Mapped[Optional[int]] = mapped_column(ForeignKey("life_areas.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    specific: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    measurable: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    achievable: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relevant: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deadline: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), default="active")
    success_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    area: Mapped[Optional[LifeArea]] = relationship(back_populates="goals")
    stages: Mapped[list["RoadmapStage"]] = relationship(back_populates="goal", cascade="all, delete-orphan")


class RoadmapStage(Base):
    __tablename__ = "roadmap_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"))
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    brief: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="planned")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    preserved: Mapped[bool] = mapped_column(Boolean, default=False)

    goal: Mapped[Goal] = relationship(back_populates="stages")
    tasks: Mapped[list["StageTask"]] = relationship(back_populates="stage", cascade="all, delete-orphan")


class StageTask(Base):
    __tablename__ = "stage_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stage_id: Mapped[int] = mapped_column(ForeignKey("roadmap_stages.id"))
    title: Mapped[str] = mapped_column(String(240))
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="todo")
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    preserved: Mapped[bool] = mapped_column(Boolean, default=False)

    stage: Mapped[RoadmapStage] = relationship(back_populates="tasks")


class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    area_id: Mapped[Optional[int]] = mapped_column(ForeignKey("life_areas.id"), nullable=True)
    goal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("goals.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    cadence: Mapped[str] = mapped_column(String(120), default="daily")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    suggested: Mapped[bool] = mapped_column(Boolean, default=False)

    area: Mapped[Optional[LifeArea]] = relationship(back_populates="habits")
    logs: Mapped[list["HabitLog"]] = relationship(back_populates="habit", cascade="all, delete-orphan")


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id"))
    day: Mapped[date] = mapped_column(Date)
    done: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    habit: Mapped[Habit] = relationship(back_populates="logs")


class Reflection(Base):
    __tablename__ = "reflections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_start: Mapped[date] = mapped_column(Date)
    energy: Mapped[int] = mapped_column(Integer)
    productivity: Mapped[int] = mapped_column(Integer)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), default="fact")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(32), default="web")
    active_role: Mapped[str] = mapped_column(String(32), default="orchestrator")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("conversation_sessions.id"))
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[ConversationSession] = relationship(back_populates="messages")


class PendingAction(Base):
    __tablename__ = "pending_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), default="calendar_event")
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    preview: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CalendarLink(Base):
    __tablename__ = "calendar_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    google_event_id: Mapped[str] = mapped_column(String(128), unique=True)
    title: Mapped[str] = mapped_column(String(240))
    area_id: Mapped[Optional[int]] = mapped_column(ForeignKey("life_areas.id"), nullable=True)
    goal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("goals.id"), nullable=True)
    habit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("habits.id"), nullable=True)


class WeeklyReview(Base):
    __tablename__ = "weekly_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_start: Mapped[date] = mapped_column(Date)
    content: Mapped[str] = mapped_column(Text)
    pace_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
