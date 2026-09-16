from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import ROOT, settings


class Base(DeclarativeBase):
    pass


db_url = settings.database_url
if db_url.startswith("sqlite:///./"):
    db_path = ROOT / db_url.replace("sqlite:///./", "")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{db_path}"

connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
engine = create_engine(db_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.db import models  # noqa: F401

    Path(ROOT / "data").mkdir(exist_ok=True)
    Base.metadata.create_all(bind=engine)
