"""
Módulo 2 — Procesamiento de datos
Monitor Económico MX

Recibe el dict de extraccion.py y devuelve dos DataFrames:
  - df_resumen:  una fila por indicador con valor actual y variaciones
  - df_historico: serie diaria del tipo de cambio (últimos 30 días)

Uso:
  Importado: from procesamiento import procesar_datos
             df_resumen, df_historico = procesar_datos(datos_crudos)
"""

import os
import pandas as pd
import requests
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

BANXICO_TOKEN = os.getenv("BANXICO_TOKEN")
BANXICO_BASE  = "https://www.banxico.org.mx/SieAPIRest/service/v1/series"


# ── Helpers ────────────────────────────────────────────────────────────────

def _variacion_pct(valor_actual: float, valor_anterior: float) -> float | None:
    """Calcula variación porcentual entre dos valores. Devuelve None si no aplica."""
    if valor_anterior is None or valor_anterior == 0 or valor_actual is None:
        return None
    return round((valor_actual - valor_anterior) / valor_anterior * 100, 4)


def _serie_historica_banxico(id_serie: str, dias: int = 35) -> pd.DataFrame:
    """
    Descarga una serie histórica de Banxico para los últimos N días.
    Devuelve un DataFrame con columnas: fecha (datetime), valor (float).
    """
    fin    = date.today()
    inicio = fin - timedelta(days=dias)
    url    = (
        f"{BANXICO_BASE}/{id_serie}/datos"
        f"/{inicio.strftime('%Y-%m-%d')}/{fin.strftime('%Y-%m-%d')}"
    )
    headers = {"Bmx-Token": BANXICO_TOKEN}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        datos = resp.json()
        observaciones = datos["bmx"]["series"][0]["datos"]

        registros = []
        for obs in observaciones:
            valor_raw = obs.get("dato", "").strip()
            if valor_raw not in ("", "N/E", "NA"):
                registros.append({
                    "fecha": pd.to_datetime(obs["fecha"], dayfirst=True),
                    "valor": float(valor_raw),
                })

        return pd.DataFrame(registros).sort_values("fecha").reset_index(drop=True)

    except Exception:
        return pd.DataFrame(columns=["fecha", "valor"])


# ── Procesamiento principal ────────────────────────────────────────────────

def _calcular_variaciones(serie: pd.DataFrame, valor_actual: float) -> dict:
    """
    Dado un DataFrame histórico y el valor de hoy, calcula:
      - var_diaria:   vs. el día hábil anterior
      - var_semanal:  vs. hace ~5 días hábiles
      - var_mensual:  vs. hace ~21 días hábiles

    Devuelve un dict con las tres variaciones (pueden ser None).
    """
    if serie.empty or valor_actual is None:
        return {"var_diaria": None, "var_semanal": None, "var_mensual": None}

    valores = serie["valor"].tolist()

    # El último dato de la serie puede ser el de hoy mismo;
    # usamos posiciones relativas desde el final
    n = len(valores)

    valor_ayer     = valores[-2] if n >= 2  else None
    valor_semana   = valores[-6] if n >= 6  else None
    valor_mes      = valores[-22] if n >= 22 else None

    return {
        "var_diaria":   _variacion_pct(valor_actual, valor_ayer),
        "var_semanal":  _variacion_pct(valor_actual, valor_semana),
        "var_mensual":  _variacion_pct(valor_actual, valor_mes),
    }


def _construir_df_resumen(datos: dict, variaciones: dict) -> pd.DataFrame:
    """
    Construye el DataFrame de resumen con una fila por indicador.

    Columnas:
        indicador, descripcion, valor, unidad, fecha_dato,
        var_diaria, var_semanal, var_mensual, fuente, error
    """
    # Metadata de cada indicador para que el Excel sea legible
    META = {
        "usd_fix": {
            "descripcion": "Tipo de cambio USD/MXN (FIX)",
            "unidad":      "Pesos por dólar",
            "fuente":      "Banxico",
        },
        "tiie_28d": {
            "descripcion": "TIIE a 28 días",
            "unidad":      "% anual",
            "fuente":      "Banxico",
        },
        "cetes_28d": {
            "descripcion": "CETES a 28 días",
            "unidad":      "% anual",
            "fuente":      "Banxico",
        },
        "inpc_anual": {
            "descripcion": "Inflación INPC (variación anual)",
            "unidad":      "%",
            "fuente":      "INEGI",
        },
    }

    filas = []
    for clave, meta in META.items():
        dato  = datos.get(clave, {})
        var   = variaciones.get(clave, {})

        filas.append({
            "indicador":   clave,
            "descripcion": meta["descripcion"],
            "valor":       dato.get("valor"),
            "unidad":      meta["unidad"],
            "fecha_dato":  dato.get("fecha"),
            "var_diaria":  var.get("var_diaria"),
            "var_semanal": var.get("var_semanal"),
            "var_mensual": var.get("var_mensual"),
            "fuente":      meta["fuente"],
            "error":       dato.get("error"),
        })

    return pd.DataFrame(filas)


def _construir_df_historico(serie_usd: pd.DataFrame) -> pd.DataFrame:
    """
    Construye el DataFrame histórico del tipo de cambio (últimos 30 días).

    Columnas:
        fecha, usd_fix, var_diaria, max_mes, min_mes
    """
    if serie_usd.empty:
        return pd.DataFrame()

    df = serie_usd.copy().tail(30)
    df = df.rename(columns={"valor": "usd_fix"})

    # Variación diaria fila a fila
    df["var_diaria"] = df["usd_fix"].pct_change() * 100
    df["var_diaria"] = df["var_diaria"].round(4)

    # Máximo y mínimo del mes (de los últimos 30 días disponibles)
    df["max_mes"] = df["usd_fix"].max()
    df["min_mes"] = df["usd_fix"].min()

    df = df.reset_index(drop=True)
    return df


# ── Función principal ──────────────────────────────────────────────────────

def procesar_datos(datos: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Recibe el dict de extraccion.obtener_datos() y devuelve dos DataFrames.

    Parámetros:
        datos: dict con claves usd_fix, tiie_28d, cetes_28d, inpc_anual

    Retorna:
        (df_resumen, df_historico)
        df_resumen:   una fila por indicador con valor y variaciones
        df_historico: serie diaria USD/MXN últimos 30 días
    """
    print("Iniciando procesamiento de datos...")

    # ── Histórico USD (necesario para calcular variaciones de tipo de cambio)
    print("  Descargando serie histórica USD/MXN...")
    serie_usd = _serie_historica_banxico("SF43718", dias=35)
    print(f"  Serie obtenida: {len(serie_usd)} observaciones")

    # ── Calcular variaciones para cada indicador
    print("  Calculando variaciones...")
    variaciones = {}

    # USD — usa la serie histórica completa
    valor_usd = datos.get("usd_fix", {}).get("valor")
    variaciones["usd_fix"] = _calcular_variaciones(serie_usd, valor_usd)

    # TIIE, CETES e INPC — solo tenemos el dato más reciente de extraccion.py
    # Para variaciones necesitaríamos series históricas propias;
    # por ahora marcamos como None (se pueden ampliar en iteraciones futuras)
    for clave in ("tiie_28d", "cetes_28d", "inpc_anual"):
        variaciones[clave] = {"var_diaria": None, "var_semanal": None, "var_mensual": None}

    # ── Construir DataFrames
    df_resumen   = _construir_df_resumen(datos, variaciones)
    df_historico = _construir_df_historico(serie_usd)

    print(f"  df_resumen:   {len(df_resumen)} indicadores")
    print(f"  df_historico: {len(df_historico)} días")
    print("Procesamiento completado.")

    return df_resumen, df_historico


# ── Ejecución directa ──────────────────────────────────────────────────────

if __name__ == "__main__":
    # Importa extraccion desde la misma carpeta modules/
    import sys, os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from extraccion import obtener_datos

    datos_crudos = obtener_datos()
    df_resumen, df_historico = procesar_datos(datos_crudos)

    print("\n── df_resumen ─────────────────────────────────")
    print(df_resumen.to_string(index=False))

    print("\n── df_historico (últimas 5 filas) ─────────────")
    print(df_historico.tail().to_string(index=False))