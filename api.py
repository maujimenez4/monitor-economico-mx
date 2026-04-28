"""
API Flask — Monitor Económico MX
Endpoints:
  GET  /           → formulario de suscripción
  POST /suscribir  → agregar suscriptor a la BD
  GET  /health     → status del servidor (Railway lo usa para healthcheck)
"""

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# Agregar modules/ al path
ROOT = Path(__file__).parent
sys.path.append(str(ROOT / "modules"))

from suscriptores import agregar_suscriptor, inicializar_bd

app = Flask(__name__, template_folder="templates")
CORS(app)

# Inicializar BD al arrancar el servidor
inicializar_bd()


# ── Rutas ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Sirve el formulario de suscripción."""
    return render_template("formulario.html")


@app.route("/suscribir", methods=["POST"])
def suscribir():
    """
    Recibe nombre y correo, los guarda en la BD.
    Acepta JSON o form data.
    Retorna JSON: { "ok": true/false, "mensaje": "..." }
    """
    if request.is_json:
        data   = request.get_json()
        nombre = data.get("nombre", "").strip()
        correo = data.get("correo", "").strip()
    else:
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()

    resultado   = agregar_suscriptor(nombre, correo)
    status_code = 200 if resultado["ok"] else 400
    return jsonify(resultado), status_code


@app.route("/health")
def health():
    """Healthcheck — Railway verifica que el servidor está corriendo."""
    return jsonify({"status": "ok", "servicio": "Monitor Económico MX"}), 200


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # En desarrollo usa puerto 5000, en producción Railway inyecta $PORT
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV", "production") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)