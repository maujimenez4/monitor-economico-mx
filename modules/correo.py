"""
Módulo 4 — Envío por correo
Monitor Económico MX

Envía el Excel generado como adjunto por Gmail usando smtplib.
Lee los destinatarios desde la BD de suscriptores (SQLite).

Uso:
  Importado: from correo import enviar_reporte
             resultados = enviar_reporte(ruta_excel, datos_crudos)
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

GMAIL_USER         = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


# ── Helpers ────────────────────────────────────────────────────────────────

def _construir_asunto(datos: dict) -> str:
    """
    Ejemplo: "Monitor MX — 27 abr 2026 | USD $17.38"
    """
    fecha_str = date.today().strftime("%d %b %Y")
    usd_data  = datos.get("usd_fix", {})
    usd_valor = usd_data.get("valor")
    usd_str   = f"USD ${usd_valor:,.2f}" if usd_valor is not None else "USD N/D"
    errores   = datos.get("errores", [])
    sufijo    = f" ⚠️ ({len(errores)} error(es))" if errores else ""
    return f"Monitor MX — {fecha_str} | {usd_str}{sufijo}"


def _construir_cuerpo(datos: dict, nombre: str) -> str:
    """
    Cuerpo HTML personalizado con el nombre del suscriptor.
    """
    fecha_str = date.today().strftime("%d de %B de %Y")

    def _fila(label, dato):
        valor = dato.get("valor")
        fecha = dato.get("fecha", "")
        error = dato.get("error")
        if error:
            valor_str = '<span style="color:#c00">Error al obtener dato</span>'
        elif valor is None:
            valor_str = "N/D"
        else:
            valor_str = f"{valor:,.4f}" if label == "USD/MXN (FIX)" else f"{valor:,.2f}"
        return f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0">{label}</td>
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
    filas_html = "".join(_fila(n, d) for n, d in indicadores)

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
          Hola <strong>{nombre}</strong>, aquí está tu reporte económico de hoy:
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

        <p style="margin-top:20px;font-size:12px;color:#888;border-top:1px solid #e0e0e0;padding-top:12px">
          Fuentes: Banco de México (Banxico) · INEGI<br>
          Para cancelar tu suscripción responde este correo con el asunto <em>BAJA</em>.
        </p>
      </div>

    </body></html>
    """


def _validar_credenciales() -> list[str]:
    faltantes = []
    for var in ("GMAIL_USER", "GMAIL_APP_PASSWORD"):
        if not os.getenv(var):
            faltantes.append(var)
    return faltantes


def _enviar_a_uno(
    nombre: str,
    correo_destino: str,
    asunto: str,
    cuerpo_html: str,
    ruta_excel: str,
    archivo: Path
) -> bool:
    """
    Envía el correo a un suscriptor específico.
    Retorna True si fue exitoso.
    """
    msg            = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"]    = GMAIL_USER
    msg["To"]      = correo_destino

    msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    with open(ruta_excel, "rb") as f:
        adjunto = MIMEApplication(f.read(), _subtype="xlsx")
        adjunto.add_header("Content-Disposition", "attachment", filename=archivo.name)
        msg.attach(adjunto)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
            servidor.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            servidor.sendmail(GMAIL_USER, correo_destino, msg.as_string())
        return True
    except smtplib.SMTPAuthenticationError:
        print("  ERROR: App Password inválida — revisa GMAIL_APP_PASSWORD en .env")
        return False
    except smtplib.SMTPException as e:
        print(f"  ERROR SMTP enviando a {correo_destino}: {e}")
        return False
    except Exception as e:
        print(f"  ERROR inesperado enviando a {correo_destino}: {e}")
        return False


# ── Función principal ──────────────────────────────────────────────────────

def enviar_reporte(ruta_excel: str, datos: dict) -> dict:
    """
    Envía el reporte a todos los suscriptores activos de la BD.

    Retorna un resumen:
        {
            "total":    3,
            "enviados": 2,
            "fallidos": 1,
            "detalle":  [{"correo": "...", "ok": True}, ...]
        }
    """
    import sys
    sys.path.append(str(Path(__file__).parent))
    from suscriptores import obtener_suscriptores_activos, inicializar_bd

    # ── Validar credenciales
    faltantes = _validar_credenciales()
    if faltantes:
        print(f"  ERROR: Faltan variables de entorno: {', '.join(faltantes)}")
        return {"total": 0, "enviados": 0, "fallidos": 0, "detalle": []}

    # ── Verificar archivo
    archivo = Path(ruta_excel)
    if not archivo.exists():
        print(f"  ERROR: No se encontró el archivo: {ruta_excel}")
        return {"total": 0, "enviados": 0, "fallidos": 0, "detalle": []}

    # ── Obtener suscriptores
    inicializar_bd()
    suscriptores = obtener_suscriptores_activos()

    if not suscriptores:
        print("  AVISO: No hay suscriptores activos en la BD")
        return {"total": 0, "enviados": 0, "fallidos": 0, "detalle": []}

    print(f"  Enviando a {len(suscriptores)} suscriptor(es)...")

    asunto   = _construir_asunto(datos)
    detalle  = []
    enviados = 0
    fallidos = 0

    for sub in suscriptores:
        nombre = sub["nombre"]
        correo = sub["correo"]
        cuerpo = _construir_cuerpo(datos, nombre)

        ok     = _enviar_a_uno(nombre, correo, asunto, cuerpo, ruta_excel, archivo)

        estado = "✓" if ok else "✗"
        print(f"  {estado} {nombre:<15} {correo}")

        detalle.append({"correo": correo, "nombre": nombre, "ok": ok})
        if ok:
            enviados += 1
        else:
            fallidos += 1

    print(f"\n  Resumen: {enviados} enviados, {fallidos} fallidos de {len(suscriptores)} total")

    return {
        "total":    len(suscriptores),
        "enviados": enviados,
        "fallidos": fallidos,
        "detalle":  detalle,
    }


# ── Ejecución directa ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).parent))

    from extraccion    import obtener_datos
    from procesamiento import procesar_datos
    from excel_builder import generar_excel

    print("── Extrayendo datos...")
    datos_crudos = obtener_datos()

    print("\n── Procesando datos...")
    df_resumen, df_historico = procesar_datos(datos_crudos)

    print("\n── Generando Excel...")
    ruta = generar_excel(df_resumen, df_historico)

    print("\n── Enviando a suscriptores...")
    resultado = enviar_reporte(ruta, datos_crudos)

    print(f"\nPipeline completo — {resultado['enviados']}/{resultado['total']} enviados")