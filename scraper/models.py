"""
Modelos SQLAlchemy — Monitor Económico MX Evolved
Espejo de las tablas definidas en init.sql.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Indicador(Base):
    """
    Snapshot diario de los 4 indicadores económicos.
    Una fila por día — constraint UNIQUE en fecha.
    """
    __tablename__ = "indicadores"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True)
    fecha:       Mapped[date]          = mapped_column(Date, nullable=False, unique=True)
    tipo_cambio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    tiie_28:     Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    cetes_28:    Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    inpc_anual:  Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    creado_en:   Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Indicador fecha={self.fecha} tipo_cambio={self.tipo_cambio}>"


class Historico(Base):
    """
    Serie de tiempo por indicador.
    Una fila por (fecha, serie_id) — permite consultas
    filtradas por serie para Power BI en V2.
    """
    __tablename__ = "historico"

    id:        Mapped[int]            = mapped_column(Integer, primary_key=True)
    fecha:     Mapped[date]           = mapped_column(Date, nullable=False)
    serie_id:  Mapped[str]            = mapped_column(String(20), nullable=False)
    nombre:    Mapped[str]            = mapped_column(String(100), nullable=False)
    valor:     Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    fuente:    Mapped[str]            = mapped_column(String(20), nullable=False)
    creado_en: Mapped[datetime]       = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Historico {self.serie_id} fecha={self.fecha} valor={self.valor}>"