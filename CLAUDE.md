# CLAUDE.md — Contexto del Proyecto

## ¿Qué es esto?

Servicio de **Reportes IA** para un sistema POS modularizado (tiendas, cafeterías, minimarkets).
Este microservicio se despliega **independiente del POS** — lectura de sus tablas operacionales
y escritura exclusiva en las tablas IA (`reporte_ia`, `ejecucion_ia`, `insight_ia`, `recomendacion_ia`)
que también viven en el mismo esquema `system_pos`.
El factor diferencial son reportes inteligentes con **sugerencias accionables** y proyecciones
basadas en la data real del negocio.

## Stack Tecnológico

- **Lenguaje:** Python 3.12+
- **Framework API:** FastAPI (async, Pydantic v2)
- **Base de datos analítica:** PostgreSQL + TimescaleDB (series temporales, métricas pre-calculadas)
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
POS (DB PostgreSQL — esquema system_pos)
  │
  ├── Tablas operacionales (read-only): venta, producto, inventario, etc.
  └── Tablas IA (read-write): reporte_ia, ejecucion_ia, insight_ia, recomendacion_ia
                │
                ▼ lectura operacional / escritura IA
         ETL + Analytics Engine (Celery workers)
                │
                ▼
         DB Analítica (TimescaleDB) — métricas pre-calculadas locales
                │
                ▼
         AI Layer (Gemini Flash / Claude Sonnet)
                │
                ▼
         API REST (FastAPI) ──▶ Dashboard / PDF
```

**Regla de acceso:**
- **Read-only:** todas las tablas operacionales del POS (`venta`, `producto`, `inventario`, etc.)
- **Read-write:** solo las 4 tablas IA en `system_pos` (`reporte_ia`, `ejecucion_ia`, `insight_ia`, `recomendacion_ia`)

## Base de Datos del POS (esquema: `system_pos`)

> **IMPORTANTE:** Todas las tablas viven bajo el esquema `system_pos`, NO en `public`.
> En las queries SQLAlchemy usar `schema="system_pos"` o el prefijo `system_pos.tabla`.
> Los PKs siguen el patrón `id_<tabla>` (ej: `id_venta`, `id_producto`), NO simplemente `id`.

### Tablas operacionales — solo lectura

#### Núcleo transaccional
- **venta** — `id_venta`, `id_sucursal`, `id_cliente` (null), `id_usuario`, `id_metodo_pago`, `numero_venta`, `fecha_venta`, `subtotal`, `descuento`, `impuesto`, `total`, `estado` ('completada'|'anulada'|...), `id_empresa`
- **detalle_venta** — `id_detalle_venta`, `id_venta`, `id_producto`, `cantidad`, `precio_unitario`, `descuento`, `subtotal`, `id_empresa`
- **comprobante_venta** — `id_comprobante_venta`, `id_empresa`, `id_venta`, `numero_comprobante`, `tipo_comprobante`, `contenido` (jsonb), `fecha_emision`

#### Productos e inventario
- **producto** — `id_producto`, `id_categoria`, `id_empresa`, `id_proveedor`, `id_marca`, `codigo_barras`, `nombre`, `descripcion`, `precio_compra`, `precio_venta`, `stock_minimo`, `controla_inventario`, `unidad`, `estado`, `fecha_creacion`, `actualizado_en`
  - ⚠️ NO tiene `stock_actual`, `fecha_vencimiento`, ni `es_perecedero` — esos campos están en `inventario`
- **inventario** — `id_inventario`, `id_producto`, `id_sucursal`, `id_empresa`, `stock_actual`, `stock_reservado`, `ubicacion`, `fecha_vencimiento` (null si no aplica), `ultima_actualizacion`
  - ⚠️ `fecha_vencimiento` está aquí, no en `producto`. Un producto puede tener varias entradas por sucursal.
  - Para detectar perecederos: `WHERE inventario.fecha_vencimiento IS NOT NULL`
- **movimiento_inventario** — `id_movimiento`, `id_producto`, `id_sucursal`, `id_usuario`, `id_empresa`, `tipo_movimiento`, `cantidad`, `cantidad_anterior`, `cantidad_nueva`, `motivo`, `referencia`, `fecha_movimiento`, `es_automatico`
- **categoria** — `id_categoria`, `id_empresa`, `nombre`, `descripcion`, `color`, `icono`, `estado`
- **marca** — `id_marca`, `id_empresa`, `nombre`, `descripcion`, `estado`, `fecha_creacion`

#### Compras y proveedores
- **compra** — `id_compra`, `id_sucursal`, `id_proveedor`, `id_usuario`, `id_empresa`, `numero_factura`, `fecha_compra`, `subtotal`, `impuesto`, `total`, `estado`, `observacion`
- **detalle_compra** — `id_detalle_compra`, `id_compra`, `id_producto`, `id_empresa`, `cantidad`, `costo_unitario`, `subtotal`
  - ⚠️ El campo es `costo_unitario`, NO `precio_unitario`
- **proveedor** — `id_proveedor`, `id_empresa`, `nit`, `razon_social`, `nombre_contacto`, `telefono`, `correo`, `direccion`, `estado`, `notas`
  - ⚠️ El nombre del proveedor es `razon_social`, no `nombre`. El email es `correo`, no `email`.

#### Financiero
- **gasto** — `id_gasto`, `id_empresa`, `id_sucursal` (null), `id_categoria_gasto`, `id_usuario`, `descripcion`, `monto`, `fecha_gasto`, `referencia`, `estado` ('registrado'|'anulado')
  - ⚠️ Reemplaza a `movimiento_financiero` (que NO existe). Para egresos usar esta tabla.
- **movimiento_caja** — `id_movimiento_caja`, `id_empresa`, `id_sesion_caja`, `id_usuario`, `tipo_movimiento` ('ingreso'|'egreso'|'ajuste'|'apertura'|'cierre'), `origen`, `referencia_tipo`, `referencia_id`, `monto`, `descripcion`, `fecha_movimiento`
- **periodo_financiero** — `id_periodo_financiero`, `id_empresa`, `fecha_inicio`, `fecha_fin`, `tipo_periodo` ('semanal'|'mensual'|'trimestral'|'anual'), `estado` ('abierto'|'cerrado'), `fecha_creacion`
- **resumen_financiero** — `id_resumen_financiero`, `id_empresa`, `id_periodo_financiero`, `total_ingresos`, `total_egresos`, `utilidad_bruta`, `impuestos`, `utilidad_neta`, `datos` (jsonb), `fecha_calculo`
- **categoria_gasto** — `id_categoria_gasto`, `id_empresa`, `nombre`, `descripcion`, `estado`
  - ⚠️ NO tiene campo `tipo`
- **metodo_pago** — `id_metodo_pago`, `nombre`, `descripcion`, `estado`
- **impuesto** — `id_impuesto`, `id_empresa`, `nombre`, `tipo`, `porcentaje`, `estado`
- **registro_impuesto** — `id_registro_impuesto`, `id_empresa`, `id_impuesto`, `origen`, `referencia_id`, `base_gravable`, `valor_impuesto`, `fecha_registro`

#### Caja
- **caja** — `id_caja`, `id_empresa`, `id_sucursal`, `nombre`, `estado`, `fecha_creacion`
- **sesion_caja** — `id_sesion_caja`, `id_empresa`, `id_caja`, `id_usuario_apertura`, `id_usuario_cierre` (null), `fecha_apertura`, `fecha_cierre` (null), `monto_apertura`, `monto_cierre` (null), `estado` ('abierta'|'cerrada'|'anulada'), `observacion`

#### Métricas pre-calculadas (muy útiles para analytics)
- **kpi_resumen** — `id_kpi_resumen`, `id_empresa`, `id_sucursal` (null), `fecha_inicio`, `fecha_fin`, `total_ventas`, `cantidad_ventas`, `ticket_promedio`, `margen_estimado`, `rotacion_inventario`, `productos_bajo_stock`, `datos` (jsonb), `fecha_calculo`
- **metrica_venta_semanal** — `id_metrica_venta_semanal`, `id_empresa`, `id_sucursal` (null), `semana_inicio`, `semana_fin`, `total_ventas`, `cantidad_ventas`, `ticket_promedio`, `hora_pico`, `dia_pico`, `datos` (jsonb), `fecha_calculo`
- **metrica_producto_semanal** — `id_metrica_producto_semanal`, `id_empresa`, `id_producto`, `id_sucursal` (null), `semana_inicio`, `semana_fin`, `unidades_vendidas`, `ingresos`, `margen_estimado`, `stock_promedio`, `dias_sin_rotacion`, `clasificacion`, `fecha_calculo`

### Tablas IA — lectura y escritura permitida

> Estas tablas pertenecen a `system_pos` pero el servicio de reportes tiene permiso de escritura sobre ellas.

- **ejecucion_ia** — `id_ejecucion_ia`, `id_empresa`, `tipo_ejecucion` ('manual'|'semanal'|'mensual'), `estado` ('pendiente'|'procesando'|'completada'|'fallida'), `fecha_inicio`, `fecha_fin`, `parametros` (jsonb), `error`, `fecha_creacion`
- **reporte_ia** — `id_reporte_ia`, `id_empresa`, `id_ejecucion_ia` (null), `fecha_inicio`, `fecha_fin`, `titulo`, `resumen`, `estado` ('generado'|'publicado'|'archivado'), `contenido` (jsonb), `fecha_generacion`
- **insight_ia** — `id_insight_ia`, `id_empresa`, `id_reporte_ia`, `tipo_insight`, `titulo`, `descripcion`, `severidad` ('info'|'success'|'warning'|'error'|'critical'), `datos` (jsonb), `fecha_creacion`
- **recomendacion_ia** — `id_recomendacion_ia`, `id_empresa`, `id_reporte_ia`, `tipo_recomendacion`, `titulo`, `descripcion`, `accion_sugerida`, `prioridad` ('baja'|'media'|'alta'|'critica'), `impacto_estimado` (null), `estado` ('pendiente'|'aceptada'|'rechazada'|'aplicada'|'archivada'), `entidad_tipo`, `entidad_id`, `datos` (jsonb), `fecha_creacion`, `fecha_resolucion` (null)

### Tablas de soporte
- **empresa** — `id_empresa`, `nombre`, `nit`, `correo`, `telefono`, `direccion`, `sector_economico`, `estado`, `fecha_creacion`
  - ⚠️ Email es `correo`, no `email`
- **sucursal** — `id_sucursal`, `id_empresa`, `nombre`, `tipo_negocio`, `direccion`, `telefono`, `estado`, `fecha_creacion`
- **usuario** — `id_usuario`, `id_empresa`, `id_sucursal`, `nombre`, `apellido`, `correo`, `username`, `password_hash`, `rol`, `estado`, `fecha_creacion`
  - ⚠️ Email es `correo`. Solo lectura — nunca leer `password_hash` en queries de análisis.
- **cliente** — `id_cliente`, `id_empresa`, `tipo_documento`, `numero_documento`, `nombre`, `apellido`, `telefono`, `correo`, `direccion`, `fecha_registro`, `estado`
- **stock_notification_rule** — `id_stock_notification_rule`, `id_producto`, `id_sucursal`, `min_stock`, `enabled`, `cooldown_minutes`, `last_triggered_at`

### Tablas irrelevantes para analytics (ignorar)
- `auditoria_evento`, `jwt_token_revocado`, `usuario_credencial` — seguridad/auditoría
- `notification`, `notification_event_type`, `notification_delivery_outbox`, `notification_preference`, `notification_recipient` — sistema de notificaciones del POS
- `secuencia_comprobante` — numeración interna del POS

## Tipos de Reportes a Generar

### 1. Ingresos y Egresos
- Resumen financiero por período (ingresos de ventas vs egresos de gastos)
- Tendencia de ingresos vs egresos (serie temporal)
- Proyección a 30/60/90 días
- **Fuentes:** `venta` (ingresos), `gasto` (egresos), `movimiento_caja`, `resumen_financiero`, `periodo_financiero`
- ⚠️ `movimiento_financiero` NO existe — usar `gasto` para egresos y `venta.total` para ingresos

### 2. Top 5 / Bottom 5 Productos
- Ranking por volumen de ventas y por margen de ganancia
- Tendencia de cada producto (subiendo/bajando)
- Sugerencia: qué hacer con los bottom 5 (descontinuar, promocionar, reubicar)
- **Fuentes:** `detalle_venta`, `producto`, `categoria`, `metrica_producto_semanal`

### 3. Horas Mágicas
- Análisis de ventas por hora del día y día de la semana
- Detección de picos y valles con estacionalidad
- Sugerencia: horarios óptimos de personal, promociones por horario
- **Fuentes:** `venta` (`fecha_venta` con timestamp), `metrica_venta_semanal`

### 4. Anti-Desperdicio
- Productos con `inventario.fecha_vencimiento` próxima (7, 14, 30 días)
- Velocidad de rotación vs fecha de vencimiento
- Alerta temprana: "Al ritmo actual, X unidades de Y van a vencer antes de venderse"
- **Fuentes:** `inventario` (`fecha_vencimiento`, `stock_actual`), `producto`, `detalle_venta`
- ⚠️ `es_perecedero` NO existe en `producto`. Perecederos = `inventario.fecha_vencimiento IS NOT NULL`
- ⚠️ `fecha_vencimiento` está en `inventario`, NO en `producto`

### 5. Precio Óptimo
- Análisis de elasticidad precio-demanda por producto
- Comparación margen actual vs margen sugerido
- Simulación: "Si sube el precio de X un 10%, estimamos que las ventas bajan Y%"
- **Fuentes:** `detalle_venta` (`precio_unitario` histórico), `producto` (`precio_venta`, `precio_compra`)

### 6. Promociones Inteligentes
- Combos por afinidad (Market Basket Analysis con Apriori)
- Combinar productos estancados con productos estrella
- Promociones para productos próximos a vencer
- **Fuentes:** `detalle_venta` (productos comprados juntos por `id_venta`), `producto`, `inventario`

### 7. Predicción de Quiebre de Stock
- Velocidad de venta vs `inventario.stock_actual` vs tiempo de reposición del proveedor
- Alerta: "Producto X se agota en N días, el proveedor tarda M días"
- **Fuentes:** `inventario`, `detalle_venta`, `compra`, `proveedor`, `stock_notification_rule`

### 8. Score de Salud del Negocio
- Indicador compuesto 0-100 basado en: margen, rotación, desperdicio, tendencia
- Dashboard resumen ejecutivo
- **Fuentes:** `kpi_resumen`, `resumen_financiero`, + todas las anteriores combinadas

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
│   │   ├── database.py          ← conexiones DB (POS + analítica)
│   │   └── redis.py             ← cliente Redis
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── sync_ventas.py       ← sincroniza ventas del POS
│   │   ├── sync_inventario.py   ← sincroniza inventario
│   │   ├── sync_financiero.py   ← sincroniza gastos y movimientos
│   │   └── base.py              ← clase base para sincronizadores
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── revenue.py           ← ingresos/egresos (venta + gasto)
│   │   ├── product_ranking.py   ← top/bottom productos
│   │   ├── peak_hours.py        ← horas mágicas
│   │   ├── expiry_tracker.py    ← anti-desperdicio (via inventario.fecha_vencimiento)
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
│   │   ├── pos_models.py        ← SQLAlchemy models (esquema system_pos)
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
- **DB:** SQLAlchemy 2.0 style (`select()` en vez de `query()`), schema `system_pos` siempre explícito
- **Schemas:** Pydantic v2, un archivo por dominio
- **PKs:** siempre usar `id_<tabla>` (ej: `id_venta`, `id_producto`), nunca asumir `id` genérico

## Variables de Entorno (.env)

```
# Base de datos POS (lectura operacional + escritura tablas IA)
POS_DATABASE_URL=postgresql+asyncpg://pos_user:pass@pos-host:5432/pos_db

# Base de datos analítica (read-write, TimescaleDB)
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

1. **Acceso a DB del POS:**
   - **Solo lectura** para tablas operacionales (`venta`, `producto`, `inventario`, `gasto`, etc.)
   - **Lectura y escritura** para tablas IA (`reporte_ia`, `ejecucion_ia`, `insight_ia`, `recomendacion_ia`)
2. **Reportes son batch, no real-time.** Se generan con Celery tasks y se cachean en Redis.
3. **Multi-tenant:** todo filtrado por `id_empresa`. Cada empresa ve solo sus datos.
4. **El mercado objetivo es Colombia** — moneda COP, zona horaria America/Bogota, español.
5. **Los prompt templates deben ser en español** — los reportes se entregan en español.
6. **Batch API:** usar batch endpoints de los LLMs para reducir costos 50%.
7. **Schema siempre explícito:** en SQLAlchemy usar `__table_args__ = {"schema": "system_pos"}`.
8. **`movimiento_financiero` NO EXISTE** — para egresos usar `gasto`, para flujo de caja usar `movimiento_caja`.
9. **`es_perecedero` NO EXISTE en `producto`** — un producto es perecedero si tiene registros en `inventario` con `fecha_vencimiento IS NOT NULL`.
10. **`catalogo_productos_general` NO EXISTE** — los datos maestros de producto están en la tabla `producto` con `codigo_barras`, `id_marca`, etc.
11. **Las métricas pre-calculadas** (`kpi_resumen`, `metrica_venta_semanal`, `metrica_producto_semanal`, `resumen_financiero`) ya están en el POS DB — usarlas cuando estén disponibles para evitar recalcular.
