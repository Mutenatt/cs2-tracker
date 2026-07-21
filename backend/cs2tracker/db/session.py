"""Engine y sesión de SQLAlchemy."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from cs2tracker.config import settings
from cs2tracker.db.models import Base

_engine: Engine | None = None
_Session: sessionmaker[Session] | None = None


def get_engine(db_url: str | None = None) -> Engine:
    global _engine, _Session
    if _engine is None or db_url is not None:
        _engine = create_engine(db_url or settings.db_url, future=True)
        _Session = sessionmaker(bind=_engine, future=True)
    return _engine


def init_db(db_url: str | None = None) -> Engine:
    """Crea las tablas si no existen. (Producción: usar Alembic.)"""
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    return engine


@contextmanager
def get_session() -> Iterator[Session]:
    if _Session is None:
        get_engine()
    assert _Session is not None
    session = _Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
