# Monitor Económico MX

Pipeline automático que extrae indicadores económicos de México (Banxico + INEGI), los procesa con pandas y envía un reporte Excel cada mañana por correo.

## Indicadores incluidos

| Indicador | Fuente | Serie |
|---|---|---|
| Tipo de cambio USD/MXN (FIX) | Banxico | SF43718 |
| TIIE a 28 días | Banxico | SF60648 |
| CETES a 28 días | Banxico | SF60633 |
| Inflación INPC anual | INEGI | 628229 |

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/monitor-economico-mx.git
cd monitor-economico-mx

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar credenciales
cp .env.example .env
# Editar .env con tus tokens y credenciales
```

## Configuración

Edita el archivo `.env` con tus credenciales:

- **BANXICO_TOKEN** — solicitar en [banxico.org.mx/SieAPIRest](https://www.banxico.org.mx/SieAPIRest/service/v1/)
- **INEGI_TOKEN** — solicitar en [inegi.org.mx](https://www.inegi.org.mx/servicios/api_indicadores.html)
- **GMAIL_APP_PASSWORD** — generar en Google Account → Seguridad → Contraseñas de aplicaciones

## Uso

```bash
# Ejecutar una vez manualmente
python main.py --once

# Iniciar el scheduler diario (corre en segundo plano)
python main.py
```

## Estructura

```
monitor-economico-mx/
├── .env                  # Credenciales (no se sube a GitHub)
├── .env.example          # Plantilla de credenciales
├── .gitignore
├── requirements.txt
├── README.md
├── main.py               # Orquestador del pipeline
├── modules/
│   ├── extraccion.py     # Módulo 1 — Banxico + INEGI APIs
│   ├── procesamiento.py  # Módulo 2 — pandas
│   ├── excel_builder.py  # Módulo 3 — openpyxl
│   └── correo.py         # Módulo 4 — smtplib
└── outputs/              # Excel generados (ignorado por git)
```

## Reporte generado

El pipeline genera un `.xlsx` con dos hojas:

- **Resumen del día** — valor actual de cada indicador con variación diaria y semanal, coloreado en verde/rojo
- **Histórico 30 días** — serie de tiempo del tipo de cambio con máximos y mínimos del mes