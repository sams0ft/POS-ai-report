# CLAUDE.md — Contexto del Proyecto

## ¿Qué es esto?

Servicio de **Reportes IA** para un sistema POS modularizado (tiendas, cafeterías, minimarkets).
Este microservicio se despliega **independiente del POS** — solo lectura de su base de datos.
El factor diferencial del producto son reportes inteligentes que generan **sugerencias accionables**
y escenarios futuros basados en la data real del negocio.

## Stack Tecnológico

- **Lenguaje:** Python 3.12+
- **Framework API:** FastAPI (async, Pydantic v2)
- **Base de datos analítica:** PostgreSQL + TimescaleDB (series temporales)
- **Cola de tareas:** Celery + Redis
- **Caché:** Redis
- **Analytics:** Pandas, Statsmodels/Prophet (series temporales), Scikit-learn (clustering, anomalías)
- **LLM:** Estrategia dual:
  - **Gemini 2.5 Flash** → reportes rutinarios (80% del volumen, ~$0.30/$2.50 por 1M tokens)
  - **Claude Sonnet 4.6** → sugerencias de alto valor (20%, ~$3/$15 por 1M tokens)
- **Generación PDF:** WeasyPrint
- **Contenedores:** Docker + Docker Compose
- **Testing:** pytest + pytest-asyncio

## Arquitectura

```
POS (DB PostgreSQL) ──read-only──▶ ETL (Celery workers)
                                        │
                                        ▼
                                  DB Analítica (TimescaleDB)
                                        │
                                        ▼
                                  Analytics Engine (Pandas/Scikit/Prophet)
                                        │
                                        ▼
                                  AI Layer (Gemini Flash / Claude Sonnet)
                                        │
                                        ▼
                                  API REST (FastAPI) ──▶ Dashboard / PDF
```

El flujo es: Ingestión → Procesamiento analítico → Generación IA → Entrega.

## Base de Datos del POS (Modelo Entidad-Relación)

El POS tiene las siguientes tablas relevantes para reportes (conexión read-only):

### Tablas principales para análisis
- **ventas** — id, id_producto, id_cliente, id_empresa, cantidad, monto_total, descuento, fecha_venta, metodo_pago, estado
- **detalle_venta** — id, id_venta, id_producto, cantidad, precio_unitario, subtotal, descuento, id_empresa
- **productos** — id, id_empresa, nombre, descripcion, precio_venta, precio_compra, stock_actual, stock_minimo, id_categoria, fecha_vencimiento, es_perecedero, estado, fecha_creacion
- **inventario** — id, id_producto, stock_actual, stock_minimo, stock_maximo, ultima_actualizacion, id_empresa
- **movimientos_cap** — id, id_empresa, id_producto, tipo_movimiento (entrada/salida), cantidad, referencia, diferencia_tipo, diferencia_id, fecha_movimiento
- **compras** — id, id_proveedor, numero_factura, fecha_compra, total, estado, id_empresa
- **detalle_compra** — id, id_compra, id_producto, cantidad, precio_unitario, subtotal, id_empresa
- **categorias** — id, nombre, descripcion, id_empresa
- **categorias_gasto** — id, nombre, tipo, id_empresa
- **proveedores** — id, nombre, telefono, email, direccion, nit, contacto, id_empresa
- **comprobantes_pago** — id, id_venta, monto, tipo_comprobante, fecha_emision
- **movimiento_financiero** — id, tipo (ingreso/egreso), monto, descripcion, id_empresa, fecha_creacion
- **periodo_financiero** — id, fecha_inicio, fecha_fin, estado, id_empresa
- **empresa** — id, nombre, nit, direccion, telefono, email, estado

### Tablas de soporte
- **usuarios** — id, nombre, email, rol, id_empresa
- **sucursal** — id, nombre, direccion, id_empresa
- **clientes** — id, nombre, email, telefono, direccion, fecha_registro, id_empresa
- **catalogo_productos_general** — datos maestros de productos con código de barras, imágenes, marca

## Tipos de Reportes a Generar

### 1. Ingresos y Egresos
- Resumen de movimientos financieros por período
- Tendencia de ingresos vs egresos (serie temporal)
- Proyección a 30/60/90 días
- **Fuentes:** movimiento_financiero, ventas, compras, periodo_financiero

### 2. Top 5 / Bottom 5 Productos
- Ranking por volumen de ventas y por margen de ganancia
- Tendencia de cada producto (subiendo/bajando)
- Sugerencia: qué hacer con los bottom 5 (descontinuar, promocionar, reubicar)
- **Fuentes:** detalle_venta, productos, categorias

### 3. Horas Mágicas
- Análisis de ventas por hora del día y día de la semana
- Detección de picos y valles con estacionalidad
- Sugerencia: horarios óptimos de personal, promociones por horario
- **Fuentes:** ventas (fecha_venta con timestamp)

### 4. Anti-Desperdicio
- Productos perecederos próximos a vencer (7, 14, 30 días)
- Velocidad de rotación vs fecha de vencimiento
- Alerta temprana: "Al ritmo actual, X unidades de Y van a vencer antes de venderse"
- **Fuentes:** productos (fecha_vencimiento, es_perecedero), inventario, detalle_venta

### 5. Precio Óptimo
- Análisis de elasticidad precio-demanda por producto
- Comparación margen actual vs margen sugerido
- Simulación: "Si sube el precio de X un 10%, estimamos que las ventas bajan Y%"
- **Fuentes:** detalle_venta (precio_unitario histórico), productos (precio_venta, precio_compra)

### 6. Promociones Inteligentes
- Combos por afinidad (Market Basket Analysis con Apriori)
- Combinar productos estancados con productos estrella
- Promociones para productos próximos a vencer
- **Fuentes:** detalle_venta (productos comprados juntos por venta), productos, inventario

### 7. Predicción de Quiebre de Stock (adicional)
- Velocidad de venta vs inventario actual vs tiempo de reposición del proveedor
- Alerta: "Producto X se agota en N días, el proveedor tarda M días"
- **Fuentes:** inventario, detalle_venta, compras, proveedores

### 8. Score de Salud del Negocio (adicional)
- Indicador compuesto 0-100 basado en: margen, rotación, desperdicio, tendencia
- Dashboard resumen ejecutivo
- **Fuentes:** todas las anteriores combinadas

## Estrategia LLM — Routing de Modelos

```python
# Lógica de routing
ROUTING = {
    "rutinario": {  # 80% de reportes
        "modelo": "gemini-2.5-flash",
        "casos": [
            "ingresos_egresos",
            "top_bottom_productos",
            "horas_magicas",
            "anti_desperdicio",
            "quiebre_stock",
        ]
    },
    "premium": {  # 20% de reportes
        "modelo": "claude-sonnet-4-6",
        "casos": [
            "precio_optimo",
            "promociones_inteligentes",
            "score_salud",
            "reporte_ejecutivo_completo",
        ]
    }
}
```

Los prompt templates están en `app/ai/prompt_templates/` — un archivo .txt por tipo de reporte.
Cada template recibe datos ya procesados por el Analytics Engine (no data cruda).

## Estructura del Proyecto

```
pos-reportes-ia/
├── CLAUDE.md                    ← este archivo
├── app/
│   ├── __init__.py
│   ├── main.py                  ← FastAPI app entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py        ← agrupa todos los routers
│   │       ├── reports.py       ← endpoints de reportes
│   │       └── health.py        ← health check
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            ← settings con Pydantic
│   │   ├── database.py          ← conexiones DB (POS read-only + analítica)
│   │   └── redis.py             ← cliente Redis
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── sync_ventas.py       ← sincroniza ventas del POS
│   │   ├── sync_inventario.py   ← sincroniza inventario
│   │   ├── sync_financiero.py   ← sincroniza movimientos financieros
│   │   └── base.py              ← clase base para sincronizadores
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── revenue.py           ← ingresos/egresos
│   │   ├── product_ranking.py   ← top/bottom productos
│   │   ├── peak_hours.py        ← horas mágicas
│   │   ├── expiry_tracker.py    ← anti-desperdicio
│   │   ├── pricing.py           ← precio óptimo
│   │   ├── promotions.py        ← motor de promociones (Apriori)
│   │   ├── stock_predictor.py   ← predicción quiebre de stock
│   │   └── health_score.py      ← score de salud del negocio
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── llm_client.py        ← cliente unificado (Gemini + Claude)
│   │   ├── router.py            ← routing entre modelos
│   │   ├── report_generator.py  ← orquesta analytics + LLM
│   │   └── prompt_templates/
│   │       ├── ingresos_egresos.txt
│   │       ├── top_bottom_productos.txt
│   │       ├── horas_magicas.txt
│   │       ├── anti_desperdicio.txt
│   │       ├── precio_optimo.txt
│   │       ├── promociones.txt
│   │       ├── quiebre_stock.txt
│   │       └── score_salud.txt
│   ├── models/
│   │   ├── __init__.py
│   │   ├── pos_models.py        ← SQLAlchemy models (reflejo read-only del POS)
│   │   └── analytics_models.py  ← modelos propios de la DB analítica
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── reports.py           ← Pydantic schemas para request/response
│   │   └── analytics.py         ← schemas de datos analíticos
│   ├── services/
│   │   ├── __init__.py
│   │   └── report_service.py    ← lógica de negocio de reportes
│   └── tasks/
│       ├── __init__.py
│       ├── celery_app.py        ← configuración Celery
│       ├── etl_tasks.py         ← tareas programadas de sincronización
│       └── report_tasks.py      ← generación async de reportes
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   └── __init__.py
│   └── integration/
│       └── __init__.py
├── scripts/
│   └── init_db.py               ← inicializa DB analítica
├── docs/
│   └── api.md
├── docker/
│   ├── Dockerfile
│   └── Dockerfile.worker
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── .env.example
└── .gitignore
```

## Convenciones de Código

- **Async everywhere:** todos los endpoints y servicios usan async/await
- **Type hints:** obligatorio en todas las funciones
- **Docstrings:** Google style en español
- **Naming:** snake_case para funciones/variables, PascalCase para clases
- **Imports:** stdlib → third-party → local, separados por línea en blanco
- **Errores:** usar HTTPException con códigos apropiados, nunca retornar 200 con error en body
- **Logs:** usar structlog con contexto (empresa_id, reporte_tipo)
- **DB:** SQLAlchemy 2.0 style (select() en vez de query())
- **Schemas:** Pydantic v2, un archivo por dominio

## Variables de Entorno (.env)

```
# Base de datos POS (read-only)
POS_DATABASE_URL=postgresql+asyncpg://readonly:pass@pos-host:5432/pos_db

# Base de datos analítica (read-write)
ANALYTICS_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/analytics_db

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM APIs
GEMINI_API_KEY=
ANTHROPIC_API_KEY=

# General
ENVIRONMENT=development
LOG_LEVEL=INFO
DEFAULT_EMPRESA_ID=1
```

## Comandos Útiles

```bash
# Desarrollo
uvicorn app.main:app --reload --port 8001

# Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# Celery beat (scheduler)
celery -A app.tasks.celery_app beat --loglevel=info

# Tests
pytest tests/ -v

# Docker
docker-compose up -d
docker-compose logs -f api
```

## Notas Importantes

1. **NUNCA escribir en la DB del POS.** Solo lectura. La conexión debe ser con un usuario read-only.
2. **Reportes son batch, no real-time.** Se generan con Celery tasks y se cachean en Redis.
3. **Multi-tenant:** todo filtrado por `id_empresa`. Cada empresa ve solo sus datos.
4. **El mercado objetivo es Colombia** — moneda COP, zona horaria America/Bogota, español.
5. **Los prompt templates deben ser en español** — los reportes se entregan en español.
6. **Batch API:** usar batch endpoints de los LLMs para reducir costos 50%.
