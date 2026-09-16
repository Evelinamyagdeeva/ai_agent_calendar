from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import ConversationMessage, ConversationSession


def get_or_create_session(db: Session, channel: str = "web") -> ConversationSession:
    session = (
        db.query(ConversationSession)
        .filter(ConversationSession.channel == channel)
        .order_by(ConversationSession.id.desc())
        .first()
    )
    if not session:
        session = ConversationSession(channel=channel)
        db.add(session)
        db.commit()
        db.refresh(session)
    return session


def add_message(db: Session, session: ConversationSession, role: str, content: str) -> None:
    db.add(ConversationMessage(session_id=session.id, role=role, content=content))
    db.commit()


def recent_messages(db: Session, session: ConversationSession, limit: int = 20) -> list[dict]:
    rows = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.session_id == session.id)
        .order_by(ConversationMessage.id.desc())
        .limit(limit)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in reversed(rows)]


def update_summary(db: Session, session: ConversationSession, summary: str) -> None:
    session.summary = summary
    db.commit()
