"""
main.py — Scraper orquestador
Monitor Económico MX — Evolved V1

Extiende el pipeline original con un paso de persistencia en PostgreSQL.
El Excel y correo se mantienen como pasos opcionales (si las credenciales
de correo están configuradas en .env).

Pasos del pipeline:
  1. Extracción   — Banxico + INEGI APIs
  2. Procesamiento — pandas
  3. Excel         — openpyxl (opcional)
  4. Correo        — smtplib (opcional, requiere GMAIL_APP_PASSWORD)
  5. Persistencia  — PostgreSQL via SQLAlchemy  ← nuevo en V1 evolved
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
sys.path.append(str(ROOT / "modules"))

from extraccion import obtener_datos
from procesamiento import procesar_datos
from excel_builder import generar_excel
from persistencia import guardar_todo

# Correo es opcional — si no hay credenciales, se omite sin error
_correo_disponible = bool(os.getenv("GMAIL_APP_PASSWORD"))
if _correo_disponible:
    from correo import enviar_reporte

from database import SessionLocal

# ── Logging ────────────────────────────────────────────────────────────────
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_DIR / "monitor.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Pipeline ───────────────────────────────────────────────────────────────
def run_pipeline() -> bool:
    log.info("=" * 55)
    log.info("INICIANDO PIPELINE — Monitor Económico MX Evolved")
    log.info("=" * 55)

    exito = True

    # ── Paso 1: Extracción
    log.info("Paso 1/5 — Extracción de datos")
    try:
        datos = obtener_datos()
        if datos["errores"]:
            log.warning(f"Indicadores con error: {', '.join(datos['errores'])}")
        else:
            log.info("Extracción completada sin errores")
    except Exception as e:
        log.exception(f"Error fatal en extracción: {e}")
        return False

    # ── Paso 2: Procesamiento
    log.info("Paso 2/5 — Procesamiento con pandas")
    try:
        df_resumen, df_historico = procesar_datos(datos)
        log.info(
            f"DataFrames listos — resumen: {len(df_resumen)} filas, "
            f"histórico: {len(df_historico)} filas"
        )
    except Exception as e:
        log.exception(f"Error en procesamiento: {e}")
        return False

    # ── Paso 3: Excel (siempre se genera como backup)
    log.info("Paso 3/5 — Generación del Excel")
    ruta_excel = None
    try:
        ruta_excel = generar_excel(df_resumen, df_historico)
        log.info(f"Excel generado: {Path(ruta_excel).name}")
    except Exception as e:
        log.warning(f"No se pudo generar Excel (no es fatal): {e}")

    # ── Paso 4: Correo (opcional)
    if _correo_disponible and ruta_excel:
        log.info("Paso 4/5 — Envío por correo")
        try:
            enviado = enviar_reporte(ruta_excel, datos)
            if enviado:
                log.info("Correo enviado exitosamente")
            else:
                log.warning("No se pudo enviar el correo")
        except Exception as e:
            log.warning(f"Error en correo (no es fatal): {e}")
    else:
        log.info("Paso 4/5 — Correo omitido (GMAIL_APP_PASSWORD no configurado)")

    # ── Paso 5: Persistencia en PostgreSQL  ← nuevo
    log.info("Paso 5/5 — Persistencia en PostgreSQL")
    try:
        session = SessionLocal()
        try:
            resultado = guardar_todo(
                session=session,
                datos=datos,
                df_resumen=df_resumen,
                df_historico=df_historico,
            )
            session.commit()

            log.info(
                f"PostgreSQL — indicador guardado: {resultado['indicador_guardado']}, "
                f"filas histórico: {resultado['filas_historico']}"
            )
            if resultado["errores"]:
                log.warning(f"Errores en persistencia: {resultado['errores']}")
                exito = False
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    except Exception as e:
        log.exception(f"Error fatal en persistencia: {e}")
        exito = False

    estado = "EXITOSO" if exito else "CON ERRORES"
    log.info(f"PIPELINE FINALIZADO — {estado}")
    log.info("=" * 55)
    return exito


# ── Scheduler ──────────────────────────────────────────────────────────────
def iniciar_scheduler() -> None:
    hora_envio = os.getenv("HORA_ENVIO", "07:30")
    try:
        datetime.strptime(hora_envio, "%H:%M")
    except ValueError:
        log.error(f"HORA_ENVIO='{hora_envio}' inválido, usando 07:30")
        hora_envio = "07:30"

    schedule.every().day.at(hora_envio).do(run_pipeline)
    log.info(f"Scheduler activo — pipeline programado para las {hora_envio}")

    while True:
        schedule.run_pending()
        time.sleep(30)


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor Económico MX — Evolved")
    parser.add_argument("--once", action="store_true", help="Ejecutar una sola vez y salir")
    args = parser.parse_args()

    if args.once:
        log.info("Modo: ejecución única (--once)")
        exito = run_pipeline()
        sys.exit(0 if exito else 1)
    else:
        log.info("Modo: scheduler diario")
        try:
            iniciar_scheduler()
        except KeyboardInterrupt:
            log.info("Scheduler detenido por el usuario")
            sys.exit(0)