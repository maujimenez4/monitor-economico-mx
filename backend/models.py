"""
Modelos SQLAlchemy — Backend FastAPI
Espejo de las tablas de PostgreSQL, lado de lectura.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Indicador(Base):
    __tablename__ = "indicadores"

    id:          Mapped[int]               = mapped_column(Integer, primary_key=True)
    fecha:       Mapped[date]              = mapped_column(Date, nullable=False, unique=True)
    tipo_cambio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    tiie_28:     Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    cetes_28:    Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    inpc_anual:  Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    creado_en:   Mapped[datetime]          = mapped_column(DateTime, server_default=func.now())


class Historico(Base):
    __tablename__ = "historico"

    id:        Mapped[int]               = mapped_column(Integer, primary_key=True)
    fecha:     Mapped[date]              = mapped_column(Date, nullable=False)
    serie_id:  Mapped[str]              = mapped_column(String(20), nullable=False)
    nombre:    Mapped[str]              = mapped_column(String(100), nullable=False)
    valor:     Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    fuente:    Mapped[str]              = mapped_column(String(20), nullable=False)
    creado_en: Mapped[datetime]          = mapped_column(DateTime, server_default=func.now())


class Suscriptor(Base):
    __tablename__ = "suscriptores"

    id:                Mapped[int]      = mapped_column(Integer, primary_key=True)
    nombre:            Mapped[str]      = mapped_column(String(100), nullable=False)
    correo:            Mapped[str]      = mapped_column(String(150), nullable=False, unique=True)
    fecha_suscripcion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    activo:            Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)