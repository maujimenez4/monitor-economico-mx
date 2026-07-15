# Monitor Económico MX — Evolved

Evolución del [Monitor Económico MX](https://github.com/maujimenez4/monitor-economico-mx) original — un script que extraía indicadores económicos de México y los enviaba por correo como Excel. Esta versión migra esa misma lógica a una arquitectura con base de datos persistente, API REST y containerización completa con Docker.

El proyecto se construye en tres versiones incrementales sobre la misma base.

## Roadmap

| Versión | Estado | Descripción |
|---------|--------|-------------|
| **V1** | ✅ Completa | PostgreSQL + FastAPI + Docker Compose |
| V2 | 🔜 Planeada | Dashboard Power BI / Metabase |
| V3 | 🔜 Planeada | Agente conversacional LangChain + Claude API |

## Stack V1

- **Python 3.12** — scraper de indicadores económicos (Banxico + INEGI)
- **PostgreSQL 16** — base de datos persistente con histórico completo
- **FastAPI** — API REST con documentación automática en `/docs`
- **SQLAlchemy** — ORM con upsert idempotente (ON CONFLICT DO UPDATE)
- **Docker + docker-compose** — tres servicios containerizados

## Indicadores

| Indicador | Fuente | Serie ID |
|-----------|--------|----------|
| Tipo de cambio USD/MXN (FIX) | Banxico | SF43718 |
| TIIE a 28 días | Banxico | SF60648 |
| CETES a 28 días | Banxico | SF60633 |
| Inflación INPC anual | INEGI | 628229 |

## Arquitectura

```
┌─────────────────────────────────────────┐
│           docker-compose network         │
│                                         │
│  ┌──────────┐      ┌──────────────────┐ │
│  │ Scraper  │─────▶│   PostgreSQL 16  │ │
│  │ 07:30 am │      │   puerto 5432    │ │
│  └──────────┘      └────────┬─────────┘ │
│                             │           │
│  ┌──────────┐               │           │
│  │ FastAPI  │───────────────┘           │
│  │ :8000    │                           │
│  └──────────┘                           │
└─────────────────────────────────────────┘
         │
    Cliente REST
    localhost:8000
```

El scraper corre diariamente a las 07:30 y escribe en PostgreSQL usando upsert — si se ejecuta más de una vez en el mismo día, actualiza en lugar de duplicar. FastAPI expone los datos vía REST. PostgreSQL no se expone al exterior: solo es accesible dentro de la red de Docker.

## Requisitos

- Docker Desktop
- Token de Banxico — [solicitar aquí](https://www.banxico.org.mx/SieAPIRest/service/v1/)
- Token de INEGI — [solicitar aquí](https://www.inegi.org.mx/servicios/api_indicadores.html)

## Instalación local

```bash
# 1. Clonar y cambiar a la rama evolved
git clone https://github.com/maujimenez4/monitor-economico-mx.git
cd monitor-economico-mx
git checkout evolved/v1

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus tokens y credenciales

# 3. Levantar todos los servicios
docker compose up --build

# 4. Verificar que la API responde
curl http://localhost:8000/health
```

> **Nota:** Usar siempre `docker compose up --build` al modificar código Python. El `restart` solo reinicia el contenedor sin reconstruir la imagen.

## Poblar datos manualmente

El scraper corre automáticamente a las 07:30. Para ejecutarlo de inmediato:

```bash
docker exec monitor_scraper python main.py --once
```

## Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Estado del servidor |
| GET | `/indicadores/latest` | Último snapshot diario |
| GET | `/indicadores/historico` | Serie de tiempo filtrable |
| GET | `/suscriptores` | Formulario de suscripción |
| POST | `/suscriptores/suscribir` | Alta de suscriptor |
| POST | `/suscriptores/cancelar` | Baja de suscriptor |

Documentación interactiva disponible en **`http://localhost:8000/docs`**

### Ejemplos de uso

```bash
# Último snapshot
curl http://localhost:8000/indicadores/latest

# Histórico de tipo de cambio, últimos 30 días
curl "http://localhost:8000/indicadores/historico?serie_id=SF43718&dias=30"

# Suscribirse al reporte
curl -X POST http://localhost:8000/suscriptores/suscribir \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Mauricio", "correo": "tu@correo.com"}'
```

## Estructura del proyecto

```
monitor-economico-mx/  (rama evolved/v1)
├── scraper/
│   ├── modules/
│   │   ├── extraccion.py      # Banxico + INEGI APIs
│   │   ├── procesamiento.py   # pandas — limpieza y cálculo
│   │   ├── excel_builder.py   # reporte Excel (backup diario)
│   │   ├── correo.py          # envío por Gmail (opcional)
│   │   ├── persistencia.py    # escritura en PostgreSQL
│   │   └── suscriptores.py    # CRUD suscriptores
│   ├── main.py                # orquestador + scheduler
│   ├── models.py              # modelos SQLAlchemy
│   ├── database.py            # conexión PostgreSQL
│   ├── init.sql               # schema inicial (3 tablas)
│   ├── Dockerfile
│   └── requirements.txt
├── backend/
│   ├── main.py                # FastAPI + endpoints REST
│   ├── models.py              # modelos SQLAlchemy (lectura)
│   ├── database.py            # sesión con Depends(get_db)
│   ├── templates/
│   │   └── formulario.html    # formulario de suscripción
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

## Variables de entorno

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `POSTGRES_USER` | Usuario de PostgreSQL | ✅ |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL | ✅ |
| `POSTGRES_DB` | Nombre de la base de datos | ✅ |
| `BANXICO_TOKEN` | Token API de Banxico | ✅ |
| `INEGI_TOKEN` | Token API de INEGI | ✅ |
| `HORA_ENVIO` | Hora del pipeline diario (HH:MM) | ⬜ default 07:30 |
| `GMAIL_USER` | Correo Gmail para envío | ⬜ opcional |
| `GMAIL_APP_PASSWORD` | App Password de Gmail | ⬜ opcional |
| `DESTINATARIO` | Correo destino (legado V1) | ⬜ opcional |

## Schema de base de datos

```sql
-- Snapshot diario de los 4 indicadores
CREATE TABLE indicadores (
    id          SERIAL PRIMARY KEY,
    fecha       DATE UNIQUE NOT NULL,
    tipo_cambio NUMERIC(10,4),  -- SF43718
    tiie_28     NUMERIC(10,4),  -- SF60648
    cetes_28    NUMERIC(10,4),  -- SF60633
    inpc_anual  NUMERIC(10,4),  -- 628229
    creado_en   TIMESTAMP DEFAULT NOW()
);

-- Serie de tiempo por indicador (para Power BI en V2)
CREATE TABLE historico (
    id        SERIAL PRIMARY KEY,
    fecha     DATE NOT NULL,
    serie_id  VARCHAR(20) NOT NULL,
    nombre    VARCHAR(100) NOT NULL,
    valor     NUMERIC(10,4),
    fuente    VARCHAR(20) NOT NULL,
    UNIQUE(fecha, serie_id)
);

-- Suscriptores al reporte diario
CREATE TABLE suscriptores (
    id                SERIAL PRIMARY KEY,
    nombre            VARCHAR(100) NOT NULL,
    correo            VARCHAR(150) UNIQUE NOT NULL,
    fecha_suscripcion TIMESTAMP DEFAULT NOW(),
    activo            BOOLEAN DEFAULT TRUE
);
```

## Historial de versiones

### V1 — evolved/v1
- Migración de script simple a arquitectura containerizada
- PostgreSQL como base de datos persistente
- FastAPI con 6 endpoints REST y documentación automática
- Upsert idempotente — el scraper puede correr N veces sin duplicar datos
- Suscriptores migrados de SQLite a PostgreSQL
- Excel diario como backup local en `scraper/outputs/`