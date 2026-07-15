"""
Módulo — Suscriptores
Monitor Económico MX — Evolved

Migrado de SQLite (suscriptores.db) a PostgreSQL.
La lógica de negocio es idéntica a la versión original —
solo cambia la capa de acceso a datos: sqlite3 → SQLAlchemy.

Uso:
    from modules.suscriptores import (
        agregar_suscriptor,
        obtener_suscriptores_activos,
        desactivar_suscriptor,
    )
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models import Suscriptor

log = logging.getLogger(__name__)


def agregar_suscriptor(session: Session, nombre: str, correo: str) -> dict:
    """
    Agrega un suscriptor nuevo o reactiva uno dado de baja.

    Retorna:
        { "ok": True,  "mensaje": "..." }
        { "ok": False, "mensaje": "..." }
    """
    correo = correo.strip().lower()
    nombre = nombre.strip()

    if not correo or "@" not in correo:
        return {"ok": False, "mensaje": "Correo no válido"}

    if not nombre:
        return {"ok": False, "mensaje": "El nombre es obligatorio"}

    # ¿Ya existe este correo?
    existente = session.query(Suscriptor).filter_by(correo=correo).first()

    if existente:
        if existente.activo:
            return {"ok": False, "mensaje": "Este correo ya está suscrito"}
        # Reactivar suscripción dada de baja
        existente.activo = True
        existente.nombre = nombre
        existente.fecha_suscripcion = datetime.now()
        session.flush()
        log.info(f"Suscriptor reactivado: {correo}")
        return {"ok": True, "mensaje": f"¡Bienvenido de vuelta {nombre}! Tu suscripción fue reactivada."}

    # Suscriptor nuevo
    nuevo = Suscriptor(nombre=nombre, correo=correo)
    session.add(nuevo)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        return {"ok": False, "mensaje": "Este correo ya está suscrito"}

    log.info(f"Suscriptor agregado: {correo}")
    return {"ok": True, "mensaje": f"¡Listo {nombre}! Te suscribiste correctamente."}


def obtener_suscriptores_activos(session: Session) -> list[dict]:
    """
    Devuelve todos los suscriptores activos como lista de dicts.
    Lo usa correo.py para saber a quiénes enviar el reporte.
    """
    suscriptores = (
        session.query(Suscriptor)
        .filter_by(activo=True)
        .order_by(Suscriptor.fecha_suscripcion)
        .all()
    )
    return [
        {
            "id":                s.id,
            "nombre":            s.nombre,
            "correo":            s.correo,
            "fecha_suscripcion": s.fecha_suscripcion.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for s in suscriptores
    ]


def desactivar_suscriptor(session: Session, correo: str) -> dict:
    """
    Da de baja a un suscriptor (soft delete).
    """
    correo = correo.strip().lower()
    suscriptor = (
        session.query(Suscriptor)
        .filter_by(correo=correo, activo=True)
        .first()
    )

    if not suscriptor:
        return {"ok": False, "mensaje": "Correo no encontrado o ya dado de baja"}

    suscriptor.activo = False
    session.flush()
    log.info(f"Suscriptor desactivado: {correo}")
    return {"ok": True, "mensaje": "Suscripción cancelada correctamente"}


def listar_todos(session: Session, incluir_inactivos: bool = False) -> list[dict]:
    """
    Lista todos los suscriptores. Útil para admin/debug.
    """
    query = session.query(Suscriptor)
    if not incluir_inactivos:
        query = query.filter_by(activo=True)

    return [
        {
            "id":     s.id,
            "nombre": s.nombre,
            "correo": s.correo,
            "activo": s.activo,
            "fecha":  s.fecha_suscripcion.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for s in query.order_by(Suscriptor.fecha_suscripcion).all()
    ]