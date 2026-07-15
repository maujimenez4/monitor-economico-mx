-- Monitor Económico MX — Evolved
-- Schema inicial V1

CREATE TABLE IF NOT EXISTS indicadores (
    id          SERIAL PRIMARY KEY,
    fecha       DATE NOT NULL,
    tipo_cambio NUMERIC(10, 4),   -- Banxico SF43718: USD/MXN FIX
    tiie_28     NUMERIC(10, 4),   -- Banxico SF60648: TIIE 28 días
    cetes_28    NUMERIC(10, 4),   -- Banxico SF60633: CETES 28 días
    inpc_anual  NUMERIC(10, 4),   -- INEGI 628229: Inflación INPC anual
    creado_en   TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_indicadores_fecha UNIQUE (fecha)
);

CREATE TABLE IF NOT EXISTS historico (
    id        SERIAL PRIMARY KEY,
    fecha     DATE NOT NULL,
    serie_id  VARCHAR(20)  NOT NULL,  -- "SF43718", "SF60648", etc.
    nombre    VARCHAR(100) NOT NULL,  -- "Tipo de cambio USD/MXN"
    valor     NUMERIC(10, 4),
    fuente    VARCHAR(20)  NOT NULL,  -- "banxico" | "inegi"
    creado_en TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_historico_fecha_serie UNIQUE (fecha, serie_id)
);

-- Índices para las consultas más comunes
CREATE INDEX IF NOT EXISTS idx_indicadores_fecha ON indicadores (fecha DESC);
CREATE INDEX IF NOT EXISTS idx_historico_serie   ON historico (serie_id, fecha DESC);