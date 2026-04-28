"""
Módulo 5 — Scheduler + main.py
Monitor Económico MX

Orquesta los 4 módulos anteriores y los corre automáticamente
cada mañana a la hora definida en .env (HORA_ENVIO).

Uso:
  Ejecutar una vez:   python main.py --once
  Scheduler diario:   python main.py
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule
from dotenv import load_dotenv
import os

load_dotenv()

# ── Agregar modules/ al path ───────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.append(str(ROOT / "modules"))

from extraccion    import obtener_datos
from procesamiento import procesar_datos
from excel_builder import generar_excel
from correo        import enviar_reporte


# ── Logging ────────────────────────────────────────────────────────────────
# Guarda logs en archivo y también los muestra en terminal

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_DIR / "monitor.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Pipeline principal ─────────────────────────────────────────────────────

def run_pipeline():
    """
    Ejecuta el pipeline completo:
      1. Extrae datos de Banxico + INEGI
      2. Procesa con pandas
      3. Genera el Excel
      4. Envía por correo

    Registra cada paso en logs/monitor.log
    """
    log.info("=" * 55)
    log.info("INICIANDO PIPELINE — Monitor Económico MX")
    log.info("=" * 55)

    exito = True

    try:
        # ── Paso 1: Extracción
        log.info("Paso 1/4 — Extracción de datos")
        datos = obtener_datos()

        if datos["errores"]:
            log.warning(f"Indicadores con error: {', '.join(datos['errores'])}")
        else:
            log.info("Extracción completada sin errores")

        # ── Paso 2: Procesamiento
        log.info("Paso 2/4 — Procesamiento con pandas")
        df_resumen, df_historico = procesar_datos(datos)
        log.info(f"DataFrames listos — resumen: {len(df_resumen)} filas, "
                 f"histórico: {len(df_historico)} filas")

        # ── Paso 3: Generación del Excel
        log.info("Paso 3/4 — Generación del Excel")
        ruta_excel = generar_excel(df_resumen, df_historico)
        log.info(f"Excel generado: {Path(ruta_excel).name}")

        # ── Paso 4: Envío por correo
        log.info("Paso 4/4 — Envío por correo")
        enviado = enviar_reporte(ruta_excel, datos)

        if enviado:
            log.info("Correo enviado exitosamente")
        else:
            log.error("Error al enviar el correo — revisa las credenciales en .env")
            exito = False

    except Exception as e:
        log.exception(f"Error inesperado en el pipeline: {e}")
        exito = False

    estado = "EXITOSO" if exito else "CON ERRORES"
    log.info(f"PIPELINE FINALIZADO — {estado}")
    log.info("=" * 55)

    return exito


# ── Scheduler ──────────────────────────────────────────────────────────────

def iniciar_scheduler():
    """
    Configura el scheduler para correr el pipeline todos los días
    a la hora definida en HORA_ENVIO (default 07:30).
    """
    hora_envio = os.getenv("HORA_ENVIO", "07:30")

    # Validar formato HH:MM
    try:
        datetime.strptime(hora_envio, "%H:%M")
    except ValueError:
        log.error(f"HORA_ENVIO='{hora_envio}' no tiene formato válido HH:MM")
        log.error("Usando hora por defecto: 07:30")
        hora_envio = "07:30"

    schedule.every().day.at(hora_envio).do(run_pipeline)

    log.info(f"Scheduler activo — pipeline programado para las {hora_envio} cada día")
    log.info("Presiona Ctrl+C para detener")

    while True:
        schedule.run_pending()
        time.sleep(30)   # revisa cada 30 segundos si hay tarea pendiente


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Monitor Económico MX — Pipeline automático"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Ejecutar el pipeline una sola vez y salir (sin scheduler)"
    )
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