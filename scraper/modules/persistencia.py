"""
Módulo de persistencia — Monitor Económico MX Evolved
Responsabilidad única: tomar los DataFrames ya procesados
y escribirlos en PostgreSQL usando upsert (INSERT ... ON CONFLICT).
"""

import logging
from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from models import Indicador, Historico

log = logging.getLogger(__name__)

# Mapeo serie_id → nombre legible (mismo orden que extraccion.py original)
SERIES_META = {
    "SF43718": {"nombre": "Tipo de cambio USD/MXN (FIX)", "fuente": "banxico"},
    "SF60648": {"nombre": "TIIE a 28 días",                "fuente": "banxico"},
    "SF60633": {"nombre": "CETES a 28 días",               "fuente": "banxico"},
    "628229":  {"nombre": "Inflación INPC anual",           "fuente": "inegi"},
}


def guardar_indicador_diario(
    session: Session,
    fecha: date,
    tipo_cambio: Optional[float],
    tiie_28: Optional[float],
    cetes_28: Optional[float],
    inpc_anual: Optional[float],
) -> None:
    """
    Inserta o actualiza el snapshot diario en la tabla indicadores.
    Usa ON CONFLICT (fecha) DO UPDATE para ser idempotente:
    si el scraper corre dos veces el mismo día, no duplica filas.
    """
    stmt = (
        insert(Indicador)
        .values(
            fecha=fecha,
            tipo_cambio=tipo_cambio,
            tiie_28=tiie_28,
            cetes_28=cetes_28,
            inpc_anual=inpc_anual,
        )
        .on_conflict_do_update(
            index_elements=["fecha"],
            set_={
                "tipo_cambio": tipo_cambio,
                "tiie_28":     tiie_28,
                "cetes_28":    cetes_28,
                "inpc_anual":  inpc_anual,
            },
        )
    )
    session.execute(stmt)
    log.info(f"Indicador diario guardado — fecha: {fecha}")


def guardar_historico(session: Session, df_historico: pd.DataFrame) -> int:
    """
    Inserta las filas del DataFrame histórico en la tabla historico.
    Espera un DataFrame con columnas: fecha, serie_id, valor.
    Devuelve el número de filas procesadas.

    El DataFrame viene de procesamiento.py original — que genera
    el histórico de 30 días del tipo de cambio. Aquí lo expandimos
    para guardar todas las series disponibles.
    """
    if df_historico.empty:
        log.warning("DataFrame histórico vacío, no se guardó nada")
        return 0

    filas_procesadas = 0

    for _, row in df_historico.iterrows():
        serie_id = str(row.get("serie_id", "SF43718"))
        meta = SERIES_META.get(serie_id, {
            "nombre": serie_id,
            "fuente": "desconocido",
        })

        stmt = (
            insert(Historico)
            .values(
                fecha=row["fecha"],
                serie_id=serie_id,
                nombre=meta["nombre"],
                valor=row.get("valor") if pd.notna(row.get("valor")) else None,
                fuente=meta["fuente"],
            )
            .on_conflict_do_nothing()  # si ya existe (fecha, serie_id), omitir
        )
        session.execute(stmt)
        filas_procesadas += 1

    log.info(f"Histórico guardado — {filas_procesadas} filas procesadas")
    return filas_procesadas


def guardar_todo(
    session: Session,
    datos: dict,
    df_resumen: pd.DataFrame,
    df_historico: pd.DataFrame,
) -> dict:
    """
    Función orquestadora de persistencia.
    Llama a las dos funciones anteriores y devuelve un resumen
    del resultado para el log del pipeline.

    datos: dict devuelto por extraccion.obtener_datos()
    df_resumen, df_historico: devueltos por procesamiento.procesar_datos()
    """
    resultado = {"indicador_guardado": False, "filas_historico": 0, "errores": []}

    try:
        # Extraer valores actuales del df_resumen
        # El resumen tiene una fila por indicador con columna 'valor_actual'
        def _valor(serie_id: str) -> Optional[float]:
            if df_resumen.empty:
                return None
            fila = df_resumen[df_resumen["serie_id"] == serie_id]
            if fila.empty:
                return None
            v = fila["valor_actual"].values[0]
            return float(v) if pd.notna(v) else None

        guardar_indicador_diario(
            session=session,
            fecha=date.today(),
            tipo_cambio=_valor("SF43718"),
            tiie_28=_valor("SF60648"),
            cetes_28=_valor("SF60633"),
            inpc_anual=_valor("628229"),
        )
        resultado["indicador_guardado"] = True

    except Exception as e:
        log.error(f"Error al guardar indicador diario: {e}")
        resultado["errores"].append(str(e))

    try:
        n = guardar_historico(session, df_historico)
        resultado["filas_historico"] = n
    except Exception as e:
        log.error(f"Error al guardar histórico: {e}")
        resultado["errores"].append(str(e))

    return resultado