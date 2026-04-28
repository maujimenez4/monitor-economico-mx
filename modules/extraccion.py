"""
Módulo 1 — Extracción de datos
Monitor Económico MX

Fuentes:
  - Banxico SIE API: tipo de cambio FIX, TIIE 28d, CETES 28d
  - INEGI API: inflación INPC

Uso:
  Directo:   python extraccion.py
  Importado: from extraccion import obtener_datos
             datos = obtener_datos()
"""

import os
import requests
from datetime import date, timedelta
import os
import requests
from datetime import date, timedelta
from dotenv import load_dotenv  # ← agregar

load_dotenv()                   # ← agregar esta línea antes de los getenv


# ── Configuración de series ────────────────────────────────────────────────

BANXICO_TOKEN = os.getenv("BANXICO_TOKEN", "TU_TOKEN_AQUI")
INEGI_TOKEN   = os.getenv("INEGI_TOKEN",   "TU_TOKEN_AQUI")

BANXICO_BASE  = "https://www.banxico.org.mx/SieAPIRest/service/v1/series"
INEGI_BASE    = "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR"

# Catálogo de series Banxico
SERIES_BANXICO = {
    "usd_fix":   "SF43718",   # Tipo de cambio pesos/dólar FIX
    "tiie_28d":  "SF60648",   # TIIE a 28 días
    "cetes_28d": "SF60633",   # CETES a 28 días (colocación primaria)
}

# Indicador INEGI para inflación (INPC variación anual)
INEGI_INDICADOR = "910406"


# ── Helpers ────────────────────────────────────────────────────────────────

def _rango_reciente(dias: int = 7) -> tuple[str, str]:
    """Devuelve (fecha_inicio, fecha_fin) en formato YYYY-MM-DD."""
    hoy    = date.today()
    inicio = hoy - timedelta(days=dias)
    return inicio.strftime("%Y-%m-%d"), hoy.strftime("%Y-%m-%d")


def _extraer_ultimo_valor(serie: list[dict]) -> dict:
    """
    De una lista de observaciones Banxico, extrae el dato más reciente
    ignorando registros con valor 'N/E' o vacíos.
    """
    for obs in reversed(serie):
        valor = obs.get("dato", "").strip()
        if valor not in ("", "N/E", "NA"):
            return {
                "valor": float(valor),
                "fecha": obs.get("fecha", ""),
            }
    return {"valor": None, "fecha": None}


# ── Banxico ────────────────────────────────────────────────────────────────

def obtener_serie_banxico(clave: str, id_serie: str) -> dict:
    """
    Consulta una serie de Banxico y devuelve su último dato disponible.

    Retorna:
        {
            "clave":  "usd_fix",
            "serie":  "SF43718",
            "valor":  17.35,
            "fecha":  "2026-04-18",
            "error":  None          # o str con el mensaje si falló
        }
    """
    inicio, fin = _rango_reciente(dias=10)
    url = f"{BANXICO_BASE}/{id_serie}/datos/{inicio}/{fin}"

    headers = {"Bmx-Token": BANXICO_TOKEN}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        datos = resp.json()
        serie = datos["bmx"]["series"][0]["datos"]
        ultimo = _extraer_ultimo_valor(serie)

        return {
            "clave":  clave,
            "serie":  id_serie,
            "valor":  ultimo["valor"],
            "fecha":  ultimo["fecha"],
            "error":  None,
        }

    except requests.exceptions.Timeout:
        return {"clave": clave, "serie": id_serie, "valor": None, "fecha": None,
                "error": "Timeout al conectar con Banxico"}
    except requests.exceptions.HTTPError as e:
        return {"clave": clave, "serie": id_serie, "valor": None, "fecha": None,
                "error": f"HTTP {resp.status_code}: {e}"}
    except (KeyError, IndexError, ValueError) as e:
        return {"clave": clave, "serie": id_serie, "valor": None, "fecha": None,
                "error": f"Error al parsear respuesta Banxico: {e}"}
    except Exception as e:
        return {"clave": clave, "serie": id_serie, "valor": None, "fecha": None,
                "error": f"Error inesperado Banxico: {e}"}


# ── INEGI ──────────────────────────────────────────────────────────────────

def obtener_inpc_inegi() -> dict:
    """
    Consulta el indicador de inflación INPC (variación anual) del INEGI.

    Retorna:
        {
            "clave":  "inpc_anual",
            "valor":  4.23,
            "fecha":  "2026-03",
            "error":  None
        }
    """
    url = (
        f"{INEGI_BASE}/{INEGI_INDICADOR}"
        f"/es/0700/false/BIE/2.0/{INEGI_TOKEN}?type=json"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()

        datos = resp.json()

        # La respuesta INEGI anida: Series > OBSERVATIONS > lista de obs
        observaciones = (
            datos["Series"][0]["OBSERVATIONS"]
        )

        # Tomar el último valor no nulo
        for obs in reversed(observaciones):
            valor_raw = obs.get("OBS_VALUE", "").strip()
            if valor_raw:
                return {
                    "clave":  "inpc_anual",
                    "valor":  float(valor_raw),
                    "fecha":  obs.get("TIME_PERIOD", ""),
                    "error":  None,
                }

        return {"clave": "inpc_anual", "valor": None, "fecha": None,
                "error": "No se encontraron observaciones válidas en INEGI"}

    except requests.exceptions.Timeout:
        return {"clave": "inpc_anual", "valor": None, "fecha": None,
                "error": "Timeout al conectar con INEGI"}
    except requests.exceptions.HTTPError as e:
        return {"clave": "inpc_anual", "valor": None, "fecha": None,
                "error": f"HTTP {resp.status_code}: {e}"}
    except (KeyError, IndexError, ValueError) as e:
        return {"clave": "inpc_anual", "valor": None, "fecha": None,
                "error": f"Error al parsear respuesta INEGI: {e}"}
    except Exception as e:
        return {"clave": "inpc_anual", "valor": None, "fecha": None,
                "error": f"Error inesperado INEGI: {e}"}


# ── Función principal ──────────────────────────────────────────────────────

def obtener_datos() -> dict:
    """
    Extrae todos los indicadores y los devuelve en un dict unificado.

    Estructura del resultado:
        {
            "fecha_extraccion": "2026-04-20",
            "usd_fix": {
                "valor": 17.35,
                "fecha": "2026-04-18",
                "serie": "SF43718",
                "error": None
            },
            "tiie_28d":  { ... },
            "cetes_28d": { ... },
            "inpc_anual":{ ... },
            "errores":   []   # lista de claves que fallaron
        }
    """
    print("Iniciando extracción de datos...")

    resultado = {
        "fecha_extraccion": date.today().strftime("%Y-%m-%d"),
    }

    # ── Banxico
    for clave, id_serie in SERIES_BANXICO.items():
        print(f"  Consultando Banxico: {clave} ({id_serie})...")
        dato = obtener_serie_banxico(clave, id_serie)
        resultado[clave] = dato
        if dato["error"]:
            print(f"    AVISO: {dato['error']}")
        else:
            print(f"    OK → {dato['valor']} ({dato['fecha']})")

    # ── INEGI
    print("  Consultando INEGI: INPC anual...")
    inpc = obtener_inpc_inegi()
    resultado["inpc_anual"] = inpc
    if inpc["error"]:
        print(f"    AVISO: {inpc['error']}")
    else:
        print(f"    OK → {inpc['valor']}% ({inpc['fecha']})")

    # ── Resumen de errores
    errores = [
        clave for clave in ("usd_fix", "tiie_28d", "cetes_28d", "inpc_anual")
        if resultado[clave]["error"] is not None
    ]
    resultado["errores"] = errores

    if errores:
        print(f"\nExtracción completada con avisos en: {', '.join(errores)}")
    else:
        print("\nExtracción completada sin errores.")

    return resultado


# ── Ejecución directa ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    datos = obtener_datos()

    print("\n── Resultado ──────────────────────────────────")
    print(json.dumps(datos, indent=2, ensure_ascii=False))