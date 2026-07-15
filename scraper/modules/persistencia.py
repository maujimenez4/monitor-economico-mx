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

    df_historico viene de procesamiento.py con columnas:
        fecha | usd_fix | var_diaria | max_mes | min_mes

    Solo contiene la serie del tipo de cambio (SF43718 / usd_fix).
    Se guarda con serie_id="SF43718" para mantener consistencia con
    la tabla historico y facilitar las consultas de V2 (Power BI).
    """
    if df_historico.empty:
        log.warning("DataFrame histórico vacío, no se guardó nada")
        return 0

    meta = SERIES_META["SF43718"]
    filas_procesadas = 0

    for _, row in df_historico.iterrows():
        valor = row.get("usd_fix")
        stmt = (
            insert(Historico)
            .values(
                fecha=row["fecha"],
                serie_id="SF43718",
                nombre=meta["nombre"],
                valor=float(valor) if pd.notna(valor) else None,
                fuente=meta["fuente"],
            )
            .on_conflict_do_nothing()
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
        # df_resumen tiene columnas: indicador, valor, fuente, error, ...
        # con valores en 'indicador': usd_fix, tiie_28d, cetes_28d, inpc_anual
        def _valor(indicador: str) -> Optional[float]:
            if df_resumen.empty:
                return None
            fila = df_resumen[df_resumen["indicador"] == indicador]
            if fila.empty or fila["error"].values[0] is not None:
                return None
            v = fila["valor"].values[0]
            return float(v) if pd.notna(v) else None

        guardar_indicador_diario(
            session=session,
            fecha=date.today(),
            tipo_cambio=_valor("usd_fix"),
            tiie_28=_valor("tiie_28d"),
            cetes_28=_valor("cetes_28d"),
            inpc_anual=_valor("inpc_anual"),
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