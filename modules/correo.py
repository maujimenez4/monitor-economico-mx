"""
Módulo 4 — Envío por correo
Monitor Económico MX

Envía el Excel generado como adjunto por Gmail usando smtplib.
El asunto incluye la fecha y el valor actual del dólar.

Uso:
  Importado: from correo import enviar_reporte
             ok = enviar_reporte(ruta_excel, datos_crudos)
"""

import os
import smtplib
from datetime import date
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GMAIL_USER        = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
DESTINATARIO      = os.getenv("DESTINATARIO")


# ── Helpers ────────────────────────────────────────────────────────────────

def _construir_asunto(datos: dict) -> str:
    """
    Construye el asunto del correo con fecha y valor del dólar.
    Ejemplo: "Monitor MX — 27 abr 2026 | USD $17.38 (-0.12%)"
    """
    fecha_str = date.today().strftime("%d %b %Y")

    usd_data  = datos.get("usd_fix", {})
    usd_valor = usd_data.get("valor")
    usd_var   = None

    # Intentar obtener variación diaria si viene en datos procesados
    if usd_valor is not None:
        usd_str = f"USD ${usd_valor:,.2f}"
    else:
        usd_str = "USD N/D"

    # Indicar si hubo errores en la extracción
    errores = datos.get("errores", [])
    sufijo  = f" ⚠️ ({len(errores)} error(es))" if errores else ""

    return f"Monitor MX — {fecha_str} | {usd_str}{sufijo}"


def _construir_cuerpo(datos: dict) -> str:
    """
    Construye el cuerpo HTML del correo con un resumen de los indicadores.
    """
    fecha_str = date.today().strftime("%d de %B de %Y")

    def _fila(nombre, dato):
        valor = dato.get("valor")
        fecha = dato.get("fecha", "")
        error = dato.get("error")

        if error:
            valor_str = f'<span style="color:#c00">Error al obtener dato</span>'
        elif valor is None:
            valor_str = "N/D"
        else:
            valor_str = f"{valor:,.4f}" if nombre == "USD/MXN (FIX)" else f"{valor:,.2f}"

        return f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0">{nombre}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;
                     text-align:right;font-weight:bold">{valor_str}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;
                     color:#888;font-size:12px">{fecha}</td>
        </tr>"""

    indicadores = [
        ("USD/MXN (FIX)",           datos.get("usd_fix",    {})),
        ("TIIE 28 días (%)",         datos.get("tiie_28d",   {})),
        ("CETES 28 días (%)",        datos.get("cetes_28d",  {})),
        ("Inflación INPC anual (%)", datos.get("inpc_anual", {})),
    ]

    filas_html = "".join(_fila(nombre, dato) for nombre, dato in indicadores)

    errores = datos.get("errores", [])
    bloque_errores = ""
    if errores:
        bloque_errores = f"""
        <p style="margin-top:16px;padding:10px 14px;background:#fff3cd;
                  border-left:4px solid #ffc107;border-radius:4px;font-size:13px">
          ⚠️ No se pudieron obtener datos de: {", ".join(errores)}
        </p>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto">

      <div style="background:#1F3864;padding:20px 24px;border-radius:8px 8px 0 0">
        <h2 style="margin:0;color:#fff;font-size:20px">Monitor Económico MX</h2>
        <p style="margin:4px 0 0;color:#a8c4e0;font-size:13px">{fecha_str}</p>
      </div>

      <div style="background:#f9f9f9;padding:16px 24px;border:1px solid #e0e0e0">
        <p style="margin:0 0 12px;font-size:14px">
          Adjunto encontrarás el reporte del día con los indicadores económicos
          de México. Aquí un resumen rápido:
        </p>

        <table style="width:100%;border-collapse:collapse;background:#fff;
                      border:1px solid #e0e0e0;border-radius:6px;font-size:14px">
          <thead>
            <tr style="background:#2E75B6;color:#fff">
              <th style="padding:10px 12px;text-align:left">Indicador</th>
              <th style="padding:10px 12px;text-align:right">Valor</th>
              <th style="padding:10px 12px;text-align:left">Fecha dato</th>
            </tr>
          </thead>
          <tbody>{filas_html}</tbody>
        </table>

        {bloque_errores}

        <p style="margin-top:16px;font-size:12px;color:#888">
          Fuentes: Banco de México (Banxico) · INEGI<br>
          Este correo es generado automáticamente por el Monitor Económico MX.
        </p>
      </div>

    </body></html>
    """


def _validar_credenciales() -> list[str]:
    """Verifica que todas las variables de entorno necesarias estén presentes."""
    faltantes = []
    for var in ("GMAIL_USER", "GMAIL_APP_PASSWORD", "DESTINATARIO"):
        if not os.getenv(var):
            faltantes.append(var)
    return faltantes


# ── Función principal ──────────────────────────────────────────────────────

def enviar_reporte(ruta_excel: str, datos: dict) -> bool:
    """
    Envía el reporte Excel por correo desde Gmail.

    Parámetros:
        ruta_excel: ruta absoluta al archivo .xlsx generado
        datos:      dict de extraccion.obtener_datos() para construir asunto

    Retorna:
        True si el envío fue exitoso, False si hubo algún error.
    """
    # ── Validar credenciales
    faltantes = _validar_credenciales()
    if faltantes:
        print(f"  ERROR: Faltan variables de entorno: {', '.join(faltantes)}")
        print("  Verifica tu archivo .env")
        return False

    # ── Verificar que el archivo existe
    archivo = Path(ruta_excel)
    if not archivo.exists():
        print(f"  ERROR: No se encontró el archivo: {ruta_excel}")
        return False

    print(f"  Preparando correo para: {DESTINATARIO}")

    # ── Construir mensaje
    msg = MIMEMultipart("alternative")
    msg["Subject"] = _construir_asunto(datos)
    msg["From"]    = GMAIL_USER
    msg["To"]      = DESTINATARIO

    # Cuerpo HTML
    cuerpo_html = _construir_cuerpo(datos)
    msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    # Adjunto Excel
    with open(ruta_excel, "rb") as f:
        adjunto = MIMEApplication(f.read(), _subtype="xlsx")
        adjunto.add_header(
            "Content-Disposition",
            "attachment",
            filename=archivo.name
        )
        msg.attach(adjunto)

    # ── Enviar via Gmail SMTP
    print("  Conectando con Gmail SMTP...")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
            servidor.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            servidor.sendmail(GMAIL_USER, DESTINATARIO, msg.as_string())

        print(f"  Correo enviado exitosamente a {DESTINATARIO}")
        print(f"  Asunto: {msg['Subject']}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("  ERROR: Autenticación fallida.")
        print("  Verifica que GMAIL_APP_PASSWORD sea una App Password válida,")
        print("  no tu contraseña normal de Gmail.")
        return False

    except smtplib.SMTPException as e:
        print(f"  ERROR SMTP: {e}")
        return False

    except Exception as e:
        print(f"  ERROR inesperado al enviar correo: {e}")
        return False


# ── Ejecución directa ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).parent))

    from extraccion   import obtener_datos
    from procesamiento import procesar_datos
    from excel_builder import generar_excel

    print("── Extrayendo datos...")
    datos_crudos = obtener_datos()

    print("\n── Procesando datos...")
    df_resumen, df_historico = procesar_datos(datos_crudos)

    print("\n── Generando Excel...")
    ruta = generar_excel(df_resumen, df_historico)

    print("\n── Enviando correo...")
    exito = enviar_reporte(ruta, datos_crudos)

    if exito:
        print("\nPipeline completo ejecutado exitosamente.")
    else:
        print("\nPipeline completado con errores en el envío.")