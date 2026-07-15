"""
Módulo — Base de datos de suscriptores
Monitor Económico MX

Maneja el CRUD de suscriptores usando SQLite.
No requiere instalar nada — SQLite viene incluido en Python.

Uso:
  from modules.suscriptores import (
      inicializar_bd,
      agregar_suscriptor,
      obtener_suscriptores_activos,
      desactivar_suscriptor,
  )
"""

import sqlite3
from datetime import datetime
from pathlib import Path

# BD en la raíz del proyecto
DB_PATH = Path(__file__).parent.parent / "suscriptores.db"


# ── Conexión ───────────────────────────────────────────────────────────────

def _conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row   # permite acceder columnas por nombre
    return conn


# ── Inicialización ─────────────────────────────────────────────────────────

def inicializar_bd():
    """
    Crea la tabla suscriptores si no existe.
    Es seguro llamarla múltiples veces — usa CREATE TABLE IF NOT EXISTS.

    Columnas:
        id              INTEGER  PK autoincremental
        nombre          TEXT     nombre del suscriptor
        correo          TEXT     único, obligatorio
        fecha_suscripcion TEXT   ISO 8601: '2026-04-27 07:30:00'
        activo          INTEGER  1 = activo, 0 = dado de baja
    """
    with _conectar() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS suscriptores (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre            TEXT    NOT NULL,
                correo            TEXT    NOT NULL UNIQUE,
                fecha_suscripcion TEXT    NOT NULL,
                activo            INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.commit()
    print(f"BD inicializada: {DB_PATH}")


# ── CRUD ───────────────────────────────────────────────────────────────────

def agregar_suscriptor(nombre: str, correo: str) -> dict:
    """
    Agrega un suscriptor nuevo.

    Retorna:
        { "ok": True,  "mensaje": "Suscriptor agregado" }
        { "ok": False, "mensaje": "El correo ya está registrado" }
    """
    correo = correo.strip().lower()
    nombre = nombre.strip()

    if not correo or "@" not in correo:
        return {"ok": False, "mensaje": "Correo no válido"}

    if not nombre:
        return {"ok": False, "mensaje": "El nombre es obligatorio"}

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with _conectar() as conn:
            conn.execute(
                "INSERT INTO suscriptores (nombre, correo, fecha_suscripcion) VALUES (?, ?, ?)",
                (nombre, correo, fecha)
            )
            conn.commit()
        return {"ok": True, "mensaje": f"¡Listo {nombre}! Te suscribiste correctamente."}

    except sqlite3.IntegrityError:
        # El UNIQUE de correo lanzó error — correo ya existe
        # Puede estar activo o dado de baja — reactivar si estaba inactivo
        with _conectar() as conn:
            row = conn.execute(
                "SELECT activo FROM suscriptores WHERE correo = ?", (correo,)
            ).fetchone()

        if row and row["activo"] == 0:
            # Reactivar suscripción
            with _conectar() as conn:
                conn.execute(
                    "UPDATE suscriptores SET activo = 1, fecha_suscripcion = ? WHERE correo = ?",
                    (fecha, correo)
                )
                conn.commit()
            return {"ok": True, "mensaje": f"¡Bienvenido de vuelta {nombre}! Tu suscripción fue reactivada."}

        return {"ok": False, "mensaje": "Este correo ya está suscrito."}


def obtener_suscriptores_activos() -> list[dict]:
    """
    Devuelve todos los suscriptores activos como lista de dicts.

    Ejemplo de un elemento:
        {
            "id": 1,
            "nombre": "Mauricio",
            "correo": "mauricio@gmail.com",
            "fecha_suscripcion": "2026-04-27 07:30:00"
        }
    """
    with _conectar() as conn:
        rows = conn.execute(
            "SELECT id, nombre, correo, fecha_suscripcion "
            "FROM suscriptores WHERE activo = 1 ORDER BY fecha_suscripcion"
        ).fetchall()

    return [dict(row) for row in rows]


def desactivar_suscriptor(correo: str) -> dict:
    """
    Da de baja a un suscriptor (soft delete — no borra el registro).

    Retorna:
        { "ok": True,  "mensaje": "Suscripción cancelada" }
        { "ok": False, "mensaje": "Correo no encontrado" }
    """
    correo = correo.strip().lower()

    with _conectar() as conn:
        cursor = conn.execute(
            "UPDATE suscriptores SET activo = 0 WHERE correo = ? AND activo = 1",
            (correo,)
        )
        conn.commit()

    if cursor.rowcount == 0:
        return {"ok": False, "mensaje": "Correo no encontrado o ya dado de baja"}

    return {"ok": True, "mensaje": "Suscripción cancelada correctamente"}


def listar_todos(incluir_inactivos: bool = False) -> list[dict]:
    """
    Lista todos los suscriptores. Útil para admin/debug.
    """
    query = "SELECT * FROM suscriptores"
    if not incluir_inactivos:
        query += " WHERE activo = 1"
    query += " ORDER BY fecha_suscripcion"

    with _conectar() as conn:
        rows = conn.execute(query).fetchall()

    return [dict(row) for row in rows]


# ── Ejecución directa — demo y prueba ─────────────────────────────────────

if __name__ == "__main__":
    print("── Inicializando BD...")
    inicializar_bd()

    print("\n── Agregando suscriptores de prueba...")
    casos = [
        ("Mauricio",  "mauricio@gmail.com"),
        ("Ana López", "ana@gmail.com"),
        ("Mauricio",  "mauricio@gmail.com"),   # duplicado — debe manejarse
        ("",          "sin-nombre@gmail.com"), # sin nombre — debe fallar
        ("Juan",      "correo-invalido"),       # correo inválido
    ]
    for nombre, correo in casos:
        resultado = agregar_suscriptor(nombre, correo)
        estado = "✓" if resultado["ok"] else "✗"
        print(f"  {estado} {correo:<28} → {resultado['mensaje']}")

    print("\n── Suscriptores activos:")
    for s in obtener_suscriptores_activos():
        print(f"  [{s['id']}] {s['nombre']:<15} {s['correo']:<28} {s['fecha_suscripcion']}")

    print("\n── Dando de baja a ana@gmail.com...")
    print(" ", desactivar_suscriptor("ana@gmail.com")["mensaje"])

    print("\n── Suscriptores activos después de baja:")
    for s in obtener_suscriptores_activos():
        print(f"  [{s['id']}] {s['nombre']:<15} {s['correo']}")

    print("\n── Reactivando ana@gmail.com...")
    print(" ", agregar_suscriptor("Ana López", "ana@gmail.com")["mensaje"])

    print("\nDemo completada.")