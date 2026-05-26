# Prompt para Claude Code — Refactor analytics + transformers (POS Reportes IA)

## Contexto

Lee `CLAUDE.md` primero para el contexto general. El ETL ya está implementado y funciona, pero el JSON resultante es demasiado verboso para alimentarlo como input a un prompt de LLM. Necesitamos transformarlo en un payload conciso de ~10-20 KB con métricas de negocio destiladas.

**Lo que ya funciona y NO se toca:**
- `app/etl/extractors/` — los 6 extractores se quedan exactamente como están.
- `app/etl/loaders/json_loader.py` — el serializador queda igual.
- `app/etl/base.py`, `sync_*.py` — son para una fase futura, no tocar.

**Lo que se reescribe:**
- `app/analytics/` — se convierte en una librería de funciones puras que reciben DataFrames y devuelven cálculos de negocio.
- `app/etl/transformers/` — se reescribe completo. Cada transformer ensambla un bloque del payload llamando a funciones de `analytics/`.
- `app/etl/etl_runner.py` — se reescribe el ensamblado final para producir el nuevo schema.

## Filosofía de la nueva arquitectura

```
extractors/ → DataFrames crudos
    ↓
analytics/  → funciones puras: reciben DataFrames, devuelven cálculos
    ↓
transformers/ → orquestadores delgados: importan analytics, arman bloques del payload
    ↓
etl_runner → ensambla los bloques en el JSON final con schema exacto
    ↓
loaders/  → serializa (sin cambios)
```

**Regla de oro**: las fórmulas de negocio (lift de Apriori, clasificación de tendencia, detección de anomalías, etc.) viven SIEMPRE en `app/analytics/`. Los transformers no deben tener fórmulas — solo orquestan y arman estructuras. Si te encuentras escribiendo `if delta > 10` en un transformer, esa lógica debe ser una función en `analytics/`.

**Por qué**: cuando alguien quiera debuggear "¿de dónde sale `lift` en `afinidad_productos`?", abre `app/analytics/promotions.py` y la fórmula está ahí, no enterrada en un transformer junto a código de ensamblado.

## Schema exacto del payload de salida

El JSON final debe tener exactamente estas 17 claves de primer nivel, en este orden. Cuando una sección no tenga datos, retorna la clave con array vacío o campos en cero — NUNCA omitas claves.

**No incluir campos con prefijo `_` (como `_nota` o `_desc`) en el JSON.** Esa información es para el prompt template del LLM, no para el payload.

```json
{
  "meta": { ... },
  "resumen_ejecutivo": { ... },
  "ventas_serie_diaria": { ... },
  "patron_horario": { ... },
  "metodos_pago": [ ... ],
  "productos_top": [ ... ],
  "productos_bottom": [ ... ],
  "categorias": [ ... ],
  "inventario_salud": { ... },
  "alertas_stock": [ ... ],
  "perecederos_riesgo": [ ... ],
  "afinidad_productos": [ ... ],
  "proveedores_top": [ ... ],
  "clientes_resumen": { ... },
  "gastos_breakdown": [ ... ],
  "sucursales": [ ... ],
  "anomalias_detectadas": [ ... ]
}
```

### `meta`
```json
{
  "id_empresa": int,
  "empresa_nombre": str,
  "sector": str,                          // de empresa.sector_economico
  "moneda": "COP",
  "periodo": {
    "fecha_inicio": "YYYY-MM-DD",
    "fecha_fin": "YYYY-MM-DD",
    "dias_calendario": int,
    "dias_operados": int                  // días con al menos 1 venta en el rango
  },
  "periodo_comparacion": {
    "fecha_inicio": "YYYY-MM-DD",
    "fecha_fin": "YYYY-MM-DD"
  },
  "generado_at": "ISO-8601 con tz America/Bogota",
  "version_schema": "1.0"
}
```

### `resumen_ejecutivo`
```json
{
  "total_ingresos": int,                  // suma venta.total
  "total_egresos": int,                   // gastos_operativos + costo_mercancia_vendida
  "utilidad_bruta": int,                  // total_ingresos - costo_mercancia_vendida
  "utilidad_neta": int,                   // utilidad_bruta - gastos_operativos - impuestos
  "margen_bruto_pct": float,              // 2 decimales
  "margen_neto_pct": float,
  "impuestos_pagados": int,               // suma venta.impuesto
  "gastos_operativos": int,               // suma gasto.monto
  "costo_mercancia_vendida": int,         // sum(detalle_venta.cantidad × producto.precio_compra)
  "cantidad_ventas": int,                 // count distinct id_venta
  "cantidad_unidades_vendidas": int,      // sum detalle_venta.cantidad
  "ticket_promedio": int,                 // total_ingresos / cantidad_ventas, sin decimales
  "items_por_ticket": float,              // unidades / ventas, 2 decimales
  "variacion_vs_mes_anterior": {
    "ingresos_pct": float,                // (actual - anterior) / anterior * 100
    "ventas_pct": float,
    "ticket_promedio_pct": float,
    "margen_pct_delta": float             // puntos porcentuales (NO porcentaje del porcentaje)
  }
}
```

### `ventas_serie_diaria`
Arrays paralelos por fecha, una entrada por cada día del rango (incluso si no hubo ventas → ingreso 0).
```json
{
  "fechas": ["YYYY-MM-DD", ...],
  "ingresos": [int, ...],
  "transacciones": [int, ...],
  "unidades": [int, ...]
}
```

### `patron_horario`
```json
{
  "matriz_hora_dia": [
    {"h": int 0-23, "d": int 1-7, "v": int, "t": int}
  ],                                       // solo celdas con actividad (no la matriz 24×7 con ceros)
  "horas_pico": [int, int, int],          // top 3 horas por ingresos
  "horas_valle": [int, int, int],         // bottom 3 horas con actividad
  "dia_pico": int,                        // 1=lunes...7=domingo
  "dia_valle": int,
  "concentracion_top3_horas_pct": float   // % ventas que ocurren en las top 3 horas
}
```

### `metodos_pago`
Array, una entrada por método de pago usado en el período:
```json
[
  {"id": int, "nombre": str, "monto": int, "transacciones": int, "pct": float}
]
```

### `productos_top`
Top 10 productos por ingresos. Si hay menos de 10 con ventas, retorna los que existan.
```json
[
  {
    "id": int,
    "nombre": str,
    "categoria": str,
    "marca": str,
    "unidades": int,
    "ingresos": int,
    "costo_total": int,                   // unidades × precio_compra
    "margen_bruto": int,                  // ingresos - costo_total
    "margen_pct": float,
    "precio_venta_prom": int,             // promedio de detalle_venta.precio_unitario
    "precio_compra_prom": int,            // producto.precio_compra (snapshot)
    "stock_actual": int,                  // suma stock_actual a través de sucursales
    "dias_cobertura": float,              // stock_actual / velocidad_diaria_30d
    "tendencia": "subiendo" | "estable" | "bajando",
    "delta_unidades_pct": float,          // vs período anterior
    "alerta": "quiebre_inminente" | "sobrestock" | null   // omitir si null
  }
]
```

### `productos_bottom`
Bottom 5 productos por ingresos, **excluyendo los que tienen 0 unidades vendidas**. Si quieres incluir productos con cero ventas pero con inventario, usa el campo `clasificacion` para marcarlos como "estancado" o "muerto".

```json
[
  {
    "id": int,
    "nombre": str,
    "categoria": str,
    "marca": str,
    "unidades": int,
    "ingresos": int,
    "stock_actual": int,
    "dias_sin_venta": int,                // días desde la última venta DENTRO del rango del reporte
    "dias_cobertura": float,
    "margen_pct": float,
    "valor_inventario_inmovilizado": int, // stock_actual × precio_compra
    "tendencia": "bajando" | "estable",
    "clasificacion": "estancado" | "muerto" | "lento"
  }
]
```
Reglas de clasificación: `muerto` si 0 unidades vendidas en el período Y stock > 0; `estancado` si dias_sin_venta >= 14; `lento` si vende pero está en el bottom.

### `categorias`
Todas las categorías que tuvieron ventas en el período:
```json
[
  {
    "id": int,
    "nombre": str,
    "ingresos": int,
    "unidades": int,
    "margen_pct_prom": float,
    "pct_total_ventas": float,
    "productos_activos": int,             // count distinct id_producto vendido en la categoría
    "tendencia": "subiendo" | "estable" | "bajando"
  }
]
```

### `inventario_salud`
```json
{
  "valor_total_inventario": int,          // sum(stock_actual × precio_compra)
  "productos_total": int,
  "productos_bajo_stock_minimo": int,
  "productos_sin_stock": int,
  "productos_sobrestock": int,            // dias_cobertura > 90
  "rotacion_promedio": float,             // (unidades_vendidas_periodo / dias) / stock_actual_promedio
  "dias_inventario_promedio": float,      // valor_inventario / (costo_mercancia_vendida / dias)
  "valor_inmovilizado_estancados": int,
  "pct_inmovilizado": float
}
```

### `alertas_stock`
Solo productos con `dias_restantes <= 7`, ordenados por urgencia, máx 15:
```json
[
  {
    "id_producto": int,
    "nombre": str,
    "stock": int,
    "venta_diaria": float,                // velocidad de venta 30d
    "dias_restantes": float,              // stock / venta_diaria
    "severidad": "critica" | "alta"       // critica si <= 2 días, alta si <= 7
  }
]
```

### `perecederos_riesgo`
Solo productos perecederos (`inventario.fecha_vencimiento IS NOT NULL`) que vencen en <= 14 días con stock no vendible, máx 10:
```json
[
  {
    "id_producto": int,
    "nombre": str,
    "stock": int,
    "fecha_vencimiento": "YYYY-MM-DD",
    "dias_restantes": int,
    "velocidad_diaria": float,
    "unidades_vendibles_proyectadas": float,  // velocidad × dias_restantes
    "unidades_en_riesgo": float,              // max(0, stock - unidades_vendibles)
    "perdida_estimada": int                   // unidades_en_riesgo × precio_compra
  }
]
```
Solo incluir si `unidades_en_riesgo > 0`.

### `afinidad_productos`
Top 5 pares por lift, solo si hay >100 ventas en el período. Si <=100 ventas, retornar `[]`.
```json
[
  {
    "par": [id1, id2],
    "co_ocurrencia": int,
    "lift": float
  }
]
```

### `proveedores_top`
Top 5 por monto de compras en el período:
```json
[
  {
    "id": int,
    "razon_social": str,
    "compras_periodo": int,
    "productos_suministrados": int,
    "lead_time_dias_prom": float,
    "pct_compras_total": float
  }
]
```

### `clientes_resumen`
```json
{
  "total_clientes_activos": int,                  // distintos id_cliente con venta en el período
  "clientes_nuevos_periodo": int,                 // primera venta del cliente cae en el período
  "ticket_promedio_cliente_recurrente": int,      // recurrente = 2+ ventas en el período
  "ticket_promedio_cliente_nuevo": int,
  "pct_ventas_clientes_identificados": float      // % ventas con id_cliente != null
}
```

### `gastos_breakdown`
Top 5 categorías + "Otros" (agrupa todo lo que no entra en top 5):
```json
[
  {"categoria": str, "monto": int, "pct": float}
]
```

### `sucursales`
Todas las sucursales con actividad:
```json
[
  {
    "id": int,
    "nombre": str,
    "ingresos": int,
    "transacciones": int,
    "ticket_promedio": int,
    "pct_total": float
  }
]
```

### `anomalias_detectadas`
Tres tipos habilitados en esta versión:
```json
[
  {
    "tipo": "caida_ventas_categoria" | "margen_caido" | "pico_ventas_inusual",
    "entidad": str,                                // nombre de la categoría/producto
    "descripcion": str,                            // máx 100 caracteres
    "severidad": "alta" | "media" | "baja",
    "datos": { /* contexto numérico relevante */ }
  }
]
```

Reglas de detección:
- `caida_ventas_categoria`: categoría con caída >15% vs período anterior → severidad alta. Entre 10-15% → media.
- `margen_caido`: producto del top 20 con margen_pct >3pp por debajo del promedio histórico → media.
- `pico_ventas_inusual`: día con ventas >2x el promedio diario del período → baja (informativo).

## Reglas de cálculo transversales

1. **Decisiones tomadas (no cuestionar)**:
   - **Umbral de tendencia**: ±10% delta vs período anterior. Entre -10% y +10% = "estable".
   - **Días sin venta**: contar solo desde la última venta DENTRO del rango del reporte. Si no hay ventas en el período → `dias_sin_venta = dias_calendario`.
   - **Cliente recurrente**: tiene 2+ ventas distintas en el período.
   - **Cliente nuevo**: su primera venta histórica cae dentro del período (necesita query a `venta` sin filtro de fecha para identificar la primera).
   - **Categorías de gasto**: top 5 + agrupar el resto en "Otros".
   - **Apriori (afinidad)**: solo correr si hay >100 ventas; min_support = 0.02; min_lift = 1.5; devolver top 5 por lift.
   - **Anomalías habilitadas**: solo las 3 tipos listados arriba. NO implementar `stock_anormal` en esta versión.
   - **Período de comparación**: rango inmediatamente previo de la misma duración. Si el reporte es 1-30 abril, el comparativo es 2-31 marzo.

2. **Tipos**:
   - Todos los montos en COP: `int` sin decimales. Usar `round()` antes de convertir.
   - Porcentajes: `float` con 2 decimales.
   - Fechas: strings ISO `YYYY-MM-DD`.
   - `generado_at`: ISO-8601 con timezone `America/Bogota`.

3. **Sin ruido**:
   - No incluir productos con ventas = 0 en `productos_top`.
   - No incluir productos con stock = 0 en `alertas_stock`.
   - No incluir perecederos con `unidades_en_riesgo = 0` en `perecederos_riesgo`.
   - No incluir campos opcionales si están en null (ej: `alerta` se omite si no aplica).

4. **Tamaño objetivo**: 10-20 KB. Si supera 50 KB, hay un bug — probablemente algún transformer no aplicó su límite de top-N.

## Estructura de archivos

### `app/analytics/` — refactor completo

Cada archivo expone funciones puras. **Reciben DataFrames (no DB sessions), retornan DataFrames o dicts**. Sin I/O, sin side effects. Todas testables aisladas.

```
app/analytics/
├── __init__.py
├── financials.py          ← resumen ejecutivo, márgenes, variaciones
├── product_ranking.py     ← top/bottom, tendencias, clasificación de estancados (REESCRIBIR)
├── peak_hours.py          ← matriz hora×día, picos/valles (REESCRIBIR)
├── expiry_tracker.py      ← perecederos en riesgo (REESCRIBIR)
├── stock_predictor.py     ← alertas de stock, días de cobertura
├── promotions.py          ← Apriori para afinidad
├── revenue.py             ← ventas serie diaria, métodos de pago, sucursales
├── inventory_health.py    ← salud global del inventario
├── customers.py           ← nuevos vs recurrentes
├── expenses.py            ← breakdown de gastos
├── anomalies.py           ← detección de las 3 anomalías habilitadas
├── trends.py              ← helper: clasificar_tendencia(delta_pct, umbral=10.0)
└── periods.py             ← helper: calcular_periodo_comparacion(fecha_desde, fecha_hasta)
```

**Importante sobre los archivos existentes** (`expiry_tracker.py`, `peak_hours.py`, `product_ranking.py`): tienen SQL pegado adentro contra un schema viejo. **Hay que reescribirlos completos** para que reciban DataFrames del extractor en vez de DB session. Los demás archivos (`pricing.py`, `health_score.py`, etc.) están en TODO — implementar solo los que correspondan al schema de payload nuevo. Borrar los que no se usen (`pricing.py`, `health_score.py` — esos eran para una etapa posterior).

#### Firma de cada función analítica

Todas siguen este patrón:

```python
def calcular_<algo>(
    df_ventas: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    # ... otros DataFrames necesarios
    parametro_negocio: float = 10.0,   # valores por defecto razonables
) -> pd.DataFrame | dict:
    """Calcula <algo> a partir de los DataFrames del extractor.
    
    Args:
        df_ventas: Output de extract_ventas (líneas de detalle_venta).
        df_catalogo: Output de extract_catalogo['productos'].
        parametro_negocio: ... (default conservador).
    
    Returns:
        DataFrame o dict según el caso, listo para que el transformer lo ensamble.
    """
```

#### Contenido específico de cada analytics

**`trends.py`** — helper que TODOS los otros analytics usan:
```python
def clasificar_tendencia(delta_pct: float, umbral: float = 10.0) -> str:
    if delta_pct > umbral: return "subiendo"
    if delta_pct < -umbral: return "bajando"
    return "estable"
```

**`periods.py`** — helper para período de comparación:
```python
def calcular_periodo_comparacion(fecha_desde: date, fecha_hasta: date) -> tuple[date, date]:
    dias = (fecha_hasta - fecha_desde).days + 1
    return (fecha_desde - timedelta(days=dias), fecha_desde - timedelta(days=1))
```

**`financials.py`** — `calcular_resumen_ejecutivo(df_ventas, df_catalogo, df_gastos, df_ventas_anterior, df_gastos_anterior)`. Devuelve dict con la forma de `resumen_ejecutivo`.

**`revenue.py`** —
- `calcular_serie_diaria(df_ventas, fecha_desde, fecha_hasta)` → dict con arrays paralelos.
- `calcular_metodos_pago(df_ventas)` → list[dict].
- `calcular_por_sucursal(df_ventas, df_catalogo_sucursales)` → list[dict].

**`peak_hours.py`** — `calcular_patron_horario(df_ventas)` → dict con matriz dispersa + horas/días pico/valle. Día semana 1=lunes a 7=domingo (ISO).

**`product_ranking.py`** —
- `calcular_top_productos(df_ventas, df_catalogo, df_inventario, df_velocidad, df_ventas_anterior, n=10)` → list[dict].
- `calcular_bottom_productos(df_ventas, df_catalogo, df_inventario, n=5)` → list[dict] (incluye lógica de `clasificacion` y `dias_sin_venta`).
- `calcular_categorias(df_ventas, df_catalogo, df_ventas_anterior)` → list[dict].

**`stock_predictor.py`** — `calcular_alertas_stock(df_inventario, df_velocidad, df_catalogo, max_dias=7, limite=15)` → list[dict].

**`expiry_tracker.py`** — `calcular_perecederos_riesgo(df_inventario, df_velocidad, df_catalogo, fecha_referencia, dias_max=14, limite=10)` → list[dict].

**`promotions.py`** — `calcular_afinidad(df_ventas, df_catalogo, min_ventas=100, min_support=0.02, min_lift=1.5, n=5)` → list[dict]. Usa mlxtend.Apriori. Si `< min_ventas`, retorna `[]` sin error.

**`inventory_health.py`** — `calcular_inventario_salud(df_inventario, df_catalogo, df_ventas, df_bottom, dias_periodo)` → dict.

**`customers.py`** — `calcular_clientes_resumen(df_ventas, df_ventas_historico_cliente)` → dict. `df_ventas_historico_cliente` es un DataFrame con id_cliente + primera_venta (de toda la historia).

**`expenses.py`** — `calcular_gastos_breakdown(df_gastos, df_catalogo_categorias_gasto, top_n=5)` → list[dict] con agrupación en "Otros".

**`anomalies.py`** —
- `detectar_caida_categoria(df_ventas_actual, df_ventas_anterior, df_catalogo)` → list[dict].
- `detectar_margen_caido(df_ventas_actual, df_catalogo)` → list[dict].
- `detectar_pico_inusual(df_ventas, df_serie_diaria)` → list[dict].
- `detectar_todas(...)` que combina los 3 anteriores → list[dict].

**Cosa importante**: `proveedores_top` se calcula directo en `revenue.py` o `expenses.py` (ya hay un dataframe de compras). NO crear `suppliers.py`.

### `app/etl/transformers/` — reescritura completa

```
app/etl/transformers/
├── __init__.py
├── transform_meta.py
├── transform_resumen_ejecutivo.py
├── transform_ventas_serie.py
├── transform_patron_horario.py
├── transform_metodos_pago.py
├── transform_productos.py            ← top + bottom + categorias (3 outputs)
├── transform_inventario.py           ← inventario_salud + alertas + perecederos
├── transform_afinidad.py
├── transform_proveedores.py
├── transform_clientes.py
├── transform_gastos.py
├── transform_sucursales.py
└── transform_anomalias.py
```

Cada transformer:
1. Importa de `app.analytics` las funciones que necesita.
2. Recibe DataFrames + contexto (fecha_desde, fecha_hasta, empresa_info).
3. Llama a las funciones de analytics.
4. Ensambla el dict/list con la forma EXACTA del schema del payload.
5. Devuelve el bloque listo para incluir en el JSON.

Plantilla:
```python
"""Transformer para el bloque <X> del payload."""

from datetime import date
import pandas as pd

from app.analytics import financials, trends


def transform(
    df_ventas: pd.DataFrame,
    df_catalogo: pd.DataFrame,
    fecha_desde: date,
    fecha_hasta: date,
    # ... otros inputs
) -> dict:
    """Ensambla el bloque <X> del payload."""
    # Llamar a analytics
    datos = financials.calcular_resumen_ejecutivo(df_ventas, df_catalogo, ...)
    
    # Ensamblar con la forma EXACTA del schema
    return {
        "campo1": int(round(datos["x"])),
        "campo2": round(datos["y"], 2),
        # ...
    }
```

**Importante**: los transformers son DELGADOS. Si te encuentras escribiendo lógica de cálculo dentro de un transformer (filtros complejos, fórmulas, clasificaciones), eso debe estar en `analytics/`. El transformer solo orquesta y formatea.

### Reescribir `app/etl/etl_runner.py`

Nuevo flujo:

```python
async def run_etl(empresa_id: int, fecha_desde: date, fecha_hasta: date) -> Path:
    # 1. Calcular ventanas (rango reporte + 30d velocidad + período comparación)
    fecha_comparacion_desde, fecha_comparacion_hasta = calcular_periodo_comparacion(fecha_desde, fecha_hasta)
    fecha_desde_efectiva = min(
        fecha_desde - timedelta(days=30),
        fecha_comparacion_desde,
    )
    
    # 2. Extraer (igual que antes, en paralelo)
    async with PosSession() as session:
        catalogo, ventas_extended, inventario, compras, gastos, movimientos = await asyncio.gather(
            extract_catalogo(...),
            extract_ventas(..., fecha_desde_efectiva, fecha_hasta),
            extract_inventario(...),
            extract_compras(...),
            extract_gastos(...),
            extract_movimientos(...),
        )
    
    # 3. Separar ventas: rango reporte vs período de comparación
    df_ventas_actual = ventas_extended[
        (ventas_extended['fecha_venta'].dt.date >= fecha_desde) &
        (ventas_extended['fecha_venta'].dt.date <= fecha_hasta)
    ]
    df_ventas_anterior = ventas_extended[
        (ventas_extended['fecha_venta'].dt.date >= fecha_comparacion_desde) &
        (ventas_extended['fecha_venta'].dt.date <= fecha_comparacion_hasta)
    ]
    # Velocidad usa los últimos 30 días desde fecha_hasta
    df_ventas_velocidad = ventas_extended[
        ventas_extended['fecha_venta'].dt.date > (fecha_hasta - timedelta(days=30))
    ]
    
    # 4. Llamar cada transformer (orden importa: algunos dependen de otros)
    meta_block = transform_meta.transform(empresa_info, fecha_desde, fecha_hasta, df_ventas_actual)
    resumen_block = transform_resumen_ejecutivo.transform(df_ventas_actual, df_catalogo, df_gastos, df_ventas_anterior, df_gastos_anterior)
    # ... resto de transformers
    
    # 5. Ensamblar payload final en orden exacto del schema
    payload = {
        "meta": meta_block,
        "resumen_ejecutivo": resumen_block,
        # ... 17 claves
    }
    
    # 6. Validar tamaño (warning si > 50 KB)
    # 7. save_json al output path
    # 8. Retornar path
```

### Eliminar archivos obsoletos

- `app/analytics/pricing.py` — borrar (no está en este payload).
- `app/analytics/health_score.py` — borrar (no está en este payload).
- Cualquier transformer viejo del ETL anterior — borrar y reemplazar por los nuevos.

## Convenciones de código

Lee la sección de `CLAUDE.md`. Críticas para este refactor:
- Funciones puras en `analytics/`: sin async, sin I/O, sin side effects.
- Imports: stdlib → third-party → `app.*`, separados por línea en blanco.
- Type hints en TODAS las funciones (incluido `-> pd.DataFrame` o `-> dict`).
- Docstrings Google-style en español.
- `Decimal` desde DB → `float` en analytics → `int` o `float(2 decimales)` en transformer.
- No usar `print()` — structlog. Solo `etl_runner.py` necesita loggear.

## Lo que NO debes hacer

- No tocar `extractors/`, `loaders/`, `base.py`, `sync_*.py`.
- No agregar `policies.py` ni capa de reducers (se discutió y se descartó).
- No agregar tipos de anomalías nuevos. Solo las 3 listadas.
- No incluir `_nota` o `_desc` en el JSON.
- No incluir productos con cero ventas en `productos_top`.
- No usar `detalle_compra.costo_unitario` para margen. Usar `producto.precio_compra`.
- No inventar columnas. Si el schema de `CLAUDE.md` no las tiene, preguntar.

## Criterios de aceptación

1. El JSON resultante tiene exactamente las 17 claves de primer nivel, en el orden definido.
2. Tamaño entre 5 KB y 50 KB para un mes de operación con datos realistas. Si supera 50 KB, hay bug.
3. Todas las funciones en `app/analytics/` son puras (sin async, sin DB session como parámetro).
4. Los transformers no contienen fórmulas — solo orquestan y formatean.
5. `ruff check app/analytics/ app/etl/transformers/` sin errores.
6. El comando `python -m app.etl.etl_runner --empresa-id 1 --fecha-desde 2026-04-01 --fecha-hasta 2026-04-30` produce el JSON nuevo en `app/etl/output/`.

## Orden sugerido de implementación

1. **Helpers primero** (`trends.py`, `periods.py`) — sin deps, testeable inmediato.
2. **Analytics de cálculo puro** (`financials.py`, `revenue.py`, `peak_hours.py`) — no necesitan combinar muchos DataFrames.
3. **Analytics que cruzan datos** (`product_ranking.py`, `stock_predictor.py`, `expiry_tracker.py`, `inventory_health.py`) — necesitan catálogo + inventario + velocidad.
4. **Analytics avanzados** (`promotions.py` con Apriori, `anomalies.py`) — los más complejos, al final.
5. **Customers + expenses** — independientes, en cualquier momento.
6. **Transformers** — uno por uno en orden del schema. Después de cada transformer, correr el `etl_runner` parcial para validar que ese bloque sale bien.
7. **etl_runner final** — ensamblar todo.
8. **Cleanup**: borrar `pricing.py`, `health_score.py` y transformers viejos.

Pregúntame si:
- Algún cálculo no queda claro (especialmente anomalías y Apriori).
- Falta un dato en los extractors actuales que algún analytics necesite.
- Hay una decisión de negocio que no esté documentada acá.

No inventes valores por defecto fuera de los listados. No agregues secciones al payload. No cambies el schema de salida.
