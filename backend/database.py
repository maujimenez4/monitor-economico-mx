"""
Capa de conexión a PostgreSQL — Backend FastAPI
Usa el patrón de dependency injection de FastAPI:
cada endpoint recibe una sesión limpia y se cierra al terminar.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,      # más conexiones que el scraper: múltiples requests simultáneos
    max_overflow=10,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """
    Dependency de FastAPI. Uso en endpoints:

        @app.get("/algo")
        def mi_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()