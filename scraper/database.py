"""
Capa de conexión a PostgreSQL — Scraper
Crea el engine y la SessionLocal para las operaciones de escritura.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

log = logging.getLogger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # verifica la conexión antes de usarla
    pool_size=3,
    max_overflow=0,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_session():
    """Contexto de sesión para usar con 'with'."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()