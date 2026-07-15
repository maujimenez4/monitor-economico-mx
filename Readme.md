# Monitor Económico MX — Evolved

Evolución del [Monitor Económico MX](https://github.com/maujimenez4/monitor-economico-mx) original.
Migra de un script de envío por correo a una arquitectura con base de datos persistente, API REST y (próximamente) dashboard y agente conversacional.

## Versiones

| Versión | Estado | Descripción |
|---------|--------|-------------|
| **V1** | ✅ En desarrollo | PostgreSQL + FastAPI + Docker |
| V2 | 🔜 Planeada | Dashboard Power BI / Metabase |
| V3 | 🔜 Planeada | Agente conversacional LangChain + Claude |

## Stack V1

- **Python 3.12** — scraper de indicadores económicos
- **PostgreSQL 16** — base de datos persistente
- **FastAPI** — API REST para consultar los datos
- **Docker + docker-compose** — containerización completa
- **Railway** — deploy en la nube

## Indicadores incluidos

| Indicador | Fuente | Serie |
|-----------|--------|-------|
| Tipo de cambio USD/MXN (FIX) | Banxico | SF43718 |
| TIIE a 28 días | Banxico | SF60648 |
| CETES a 28 días | Banxico | SF60633 |
| Inflación INPC anual | INEGI | 628229 |

## Requisitos

- Docker Desktop
- Git
- Tokens de Banxico e INEGI

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

## Endpoints V1

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Estado del servidor |
| GET | `/indicadores/latest` | Último snapshot diario |
| GET | `/indicadores/historico` | Serie de tiempo filtrable |

## Estructura del proyecto

```
monitor-economico-mx/  (rama evolved/v1)
├── scraper/
│   ├── modules/          # extraccion, procesamiento, excel_builder, correo
│   ├── main.py           # orquestador + scheduler
│   ├── models.py         # modelos SQLAlchemy
│   ├── database.py       # conexión PostgreSQL
│   ├── init.sql          # schema inicial
│   ├── Dockerfile
│   └── requirements.txt
├── backend/
│   ├── main.py           # FastAPI + endpoints
│   ├── database.py       # sesión SQLAlchemy
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```