"""
Backend FastAPI — Monitor Económico MX Evolved
Endpoints V1:
  GET  /health                          → healthcheck
  GET  /indicadores/latest              → snapshot más reciente
  GET  /indicadores/historico           → serie de tiempo filtrable
  GET  /suscriptores                    → formulario de suscripción (HTML)
  POST /suscriptores/suscribir          → agregar suscriptor
  POST /suscriptores/cancelar           → dar de baja suscriptor
"""

import os
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from database import get_db
from models import Historico, Indicador, Suscriptor

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Monitor Económico MX",
    description="API de indicadores económicos de México — Banxico + INEGI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Schemas Pydantic (forma de los datos en request/response) ──────────────

class IndicadorResponse(BaseModel):
    fecha:       date
    tipo_cambio: Optional[Decimal]
    tiie_28:     Optional[Decimal]
    cetes_28:    Optional[Decimal]
    inpc_anual:  Optional[Decimal]

    class Config:
        from_attributes = True


class HistoricoItem(BaseModel):
    fecha:    date
    serie_id: str
    nombre:   str
    valor:    Optional[Decimal]
    fuente:   str

    class Config:
        from_attributes = True


class SuscribirRequest(BaseModel):
    nombre: str
    correo: EmailStr


class CancelarRequest(BaseModel):
    correo: EmailStr


class MensajeResponse(BaseModel):
    ok:      bool
    mensaje: str


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Sistema"])
def health():
    """Healthcheck — Railway lo usa para verificar que el servidor responde."""
    return {"status": "ok", "servicio": "Monitor Económico MX", "version": "1.0.0"}


@app.get(
    "/indicadores/latest",
    response_model=IndicadorResponse,
    tags=["Indicadores"],
    summary="Último snapshot diario",
)
def get_latest(db: Session = Depends(get_db)):
    """
    Devuelve los valores más recientes de los 4 indicadores económicos.
    Es la fila más reciente de la tabla indicadores.
    """
    row = db.query(Indicador).order_by(desc(Indicador.fecha)).first()
    if not row:
        raise HTTPException(status_code=404, detail="No hay datos disponibles aún")
    return row


@app.get(
    "/indicadores/historico",
    response_model=list[HistoricoItem],
    tags=["Indicadores"],
    summary="Serie de tiempo por indicador",
)
def get_historico(
    serie_id: Optional[str] = Query(
        default=None,
        description="ID de la serie: SF43718, SF60648, SF60633, 628229",
        example="SF43718",
    ),
    dias: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Número de días hacia atrás (1-365)",
    ),
    db: Session = Depends(get_db),
):
    """
    Devuelve la serie de tiempo de uno o todos los indicadores.
    - Sin `serie_id`: devuelve todos los indicadores de los últimos N días.
    - Con `serie_id`: filtra por serie específica.

    Útil para conectar Power BI en V2.
    """
    query = db.query(Historico).order_by(desc(Historico.fecha))

    if serie_id:
        series_validas = {"SF43718", "SF60648", "SF60633", "628229"}
        if serie_id not in series_validas:
            raise HTTPException(
                status_code=400,
                detail=f"serie_id inválido. Valores aceptados: {sorted(series_validas)}",
            )
        query = query.filter(Historico.serie_id == serie_id)

    # Limitar por días usando subquery de fechas distintas
    from sqlalchemy import func
    fecha_limite = (
        db.query(func.min(Historico.fecha))
        .filter(
            Historico.fecha >= db.query(
                func.date(func.now() - func.cast(f"{dias} days", type_=db.bind.dialect.colspecs.get(type(None), None)))
            ).scalar_subquery()
        )
        .scalar()
    )
    # Forma simple y compatible: filtrar por offset de días directamente
    from sqlalchemy import text
    query = query.filter(
        Historico.fecha >= text(f"CURRENT_DATE - INTERVAL '{dias} days'")
    )

    rows = query.limit(500).all()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No hay datos históricos para los parámetros indicados",
        )
    return rows


@app.get(
    "/suscriptores",
    response_class=HTMLResponse,
    tags=["Suscriptores"],
    summary="Formulario de suscripción",
)
def formulario_suscripcion():
    """Sirve el formulario HTML de suscripción (migrado de Flask)."""
    html_path = os.path.join(os.path.dirname(__file__), "templates", "formulario.html")
    if os.path.exists(html_path):
        with open(html_path, encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    # Formulario mínimo si no existe el template
    return HTMLResponse(content="""
    <html><body style="font-family:sans-serif;max-width:400px;margin:2rem auto">
      <h2>Suscribirse al Monitor Económico MX</h2>
      <form onsubmit="suscribir(event)">
        <input id="nombre" placeholder="Tu nombre" required style="display:block;width:100%;margin:8px 0;padding:8px"><br>
        <input id="correo" type="email" placeholder="Tu correo" required style="display:block;width:100%;margin:8px 0;padding:8px"><br>
        <button type="submit" style="padding:8px 24px">Suscribirse</button>
      </form>
      <p id="msg"></p>
      <script>
        async function suscribir(e) {
          e.preventDefault();
          const r = await fetch('/suscriptores/suscribir', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({nombre: document.getElementById('nombre').value,
                                  correo: document.getElementById('correo').value})
          });
          const d = await r.json();
          document.getElementById('msg').textContent = d.mensaje;
        }
      </script>
    </body></html>
    """)


@app.post(
    "/suscriptores/suscribir",
    response_model=MensajeResponse,
    tags=["Suscriptores"],
    summary="Agregar suscriptor",
)
def suscribir(body: SuscribirRequest, db: Session = Depends(get_db)):
    """
    Agrega un suscriptor nuevo o reactiva uno dado de baja.
    Acepta JSON: { "nombre": "...", "correo": "..." }
    """
    from sqlalchemy.exc import IntegrityError

    existente = db.query(Suscriptor).filter_by(correo=str(body.correo)).first()

    if existente:
        if existente.activo:
            return MensajeResponse(ok=False, mensaje="Este correo ya está suscrito")
        existente.activo = True
        existente.nombre = body.nombre
        db.commit()
        return MensajeResponse(
            ok=True,
            mensaje=f"¡Bienvenido de vuelta {body.nombre}! Tu suscripción fue reactivada.",
        )

    db.add(Suscriptor(nombre=body.nombre, correo=str(body.correo)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return MensajeResponse(ok=False, mensaje="Este correo ya está suscrito")

    return MensajeResponse(ok=True, mensaje=f"¡Listo {body.nombre}! Te suscribiste correctamente.")


@app.post(
    "/suscriptores/cancelar",
    response_model=MensajeResponse,
    tags=["Suscriptores"],
    summary="Cancelar suscripción",
)
def cancelar(body: CancelarRequest, db: Session = Depends(get_db)):
    """
    Da de baja a un suscriptor (soft delete — no borra el registro).
    Acepta JSON: { "correo": "..." }
    """
    suscriptor = db.query(Suscriptor).filter_by(
        correo=str(body.correo), activo=True
    ).first()

    if not suscriptor:
        return MensajeResponse(ok=False, mensaje="Correo no encontrado o ya dado de baja")

    suscriptor.activo = False
    db.commit()
    return MensajeResponse(ok=True, mensaje="Suscripción cancelada correctamente")