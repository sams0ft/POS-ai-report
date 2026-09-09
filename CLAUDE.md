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

### Arquitectura objetivo

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

### Pipeline implementado hoy

El flujo que funciona de punta a punta es **síncrono y sin estado**: la API dispara el ETL
dentro de la misma petición usando el rango de fechas del request, el ETL deja el JSON en
disco y de ahí se alimenta el LLM. TimescaleDB, Celery y la persistencia en las tablas IA
todavía no están conectados.

```
POS DB (Supabase, read-only)
      │
      ▼  asyncio.gather — 5 extractors en paralelo
app/etl/extractors/     catálogo · ventas · inventario · compras · gastos
      │                 + app/analytics/flash_sales.py (consultas crudas)
      ▼  DataFrames pandas + ventanas temporales
app/analytics/          TODA la aritmética vive aquí
      │
      ▼  13 transformers — solo orquestan, no calculan
app/etl/transformers/
      │
      ▼  payload 17 claves · schema v1.0 · 8–14 KB
app/etl/output/empresa_{id}_{desde}_{hasta}.json
      │
      ▲  run_etl(empresa_id, fecha_desde, fecha_hasta)  ← lo dispara el endpoint
      │  app/etl/json_loader.py  lee el archivo recién escrito
POST /api/v1/reports/generate
      │
      ▼  general_prompt.txt + payload recortado (_trim_payload)
LLM  ──▶  ReportResponse { resumen, sugerencias[], datos }
```

**Regla de oro del pipeline:** el LLM **nunca calcula**. Recibe números ya listos.
Toda la aritmética (promedios, IVA, márgenes, descuentos, impacto) vive en
`app/analytics/`; los transformers solo orquestan y colocan el resultado en su clave.

**Regla de acceso:**
- **Read-only:** todas las tablas operacionales del POS (`venta`, `producto`, `inventario`, etc.)
- **Read-write:** solo las 4 tablas IA en `system_pos` (`reporte_ia`, `ejecucion_ia`, `insight_ia`, `recomendacion_ia`)

## Base de Datos del POS (esquema: `system_pos`)

> **FUENTE DE VERDAD DEL ESQUEMA: [`db/POS-AI-scriptdb.sql`](db/POS-AI-scriptdb.sql)**
> — el DDL completo del esquema `system_pos`. Lo que sigue en esta sección es un
> **resumen de consulta rápida**: ante cualquier discrepancia, manda el DDL.
>
> **Leer el DDL antes de** escribir un extractor nuevo, agregar una consulta en
> `app/analytics/`, o depurar una query que falla por columna inexistente. No copiar
> nombres de columna de otros archivos del proyecto: ya hubo casos de queries con
> nombres viejos que no existen en el esquema real.

> **IMPORTANTE:** Todas las tablas viven bajo el esquema `system_pos`, NO en `public`.
> En las queries SQLAlchemy usar `schema="system_pos"` o el prefijo `system_pos.tabla`.
> Los PKs siguen el patrón `id_<tabla>` (ej: `id_venta`, `id_producto`), NO simplemente `id`.

### Tablas operacionales — solo lectura

#### Núcleo transaccional
- **venta** — `id_venta`, `id_empresa`, `id_sucursal`, `id_cliente` (null), `id_usuario`, `id_metodo_pago` (null en crédito), `id_sesion_caja`, `numero_venta`, `numero_factura`, `fecha_venta` (timestamp SIN tz), `subtotal`, `descuento`, `impuesto`, `total`, `monto_recibido`, `estado`, `estado_devolucion`, `condicion_pago`, `estado_pago`, `monto_abonado`, `saldo_pendiente`, `monto_devuelto_credito`, `venta_offline`, `observacion`
  - ⚠️ `estado` admite `'registrada'|'completada'|'anulada'|'cancelada'`. Para ingresos del período usar `'completada'`.
  - ⚠️ Hay ventas a crédito: el `total` se registra al vender aunque no se haya cobrado (`saldo_pendiente`).
- **detalle_venta** — `id_detalle_venta`, `id_empresa`, `id_venta`, `id_producto`, `id_paquete_producto` (null), `cantidad`, `precio_unitario`, `descuento`, `subtotal`, `sku_escaneado`, `nombre_producto_historico`, `unidad_base_producto_historica`, `unidades_por_item_usadas`
  - ⚠️ `cantidad` está en items de la presentación vendida, NO en unidad base. Para unidad base: `cantidad * COALESCE(unidades_por_item_usadas, 1)`.
- **comprobante_venta** — `id_comprobante_venta`, `id_empresa`, `id_venta`, `numero_comprobante`, `tipo_comprobante`, `contenido` (jsonb), `fecha_emision`

#### Productos
- **producto** — `id_producto`, `id_empresa`, `id_categoria`, `id_marca`, `id_proveedor` (null), `nombre`, `descripcion`, `referencia`, `slug`, `precio_compra`, `porcentaje_ganancia`, `precio_venta`, `iva_porcentaje`, `precio_incluye_iva`, `retencion_fuente_porcentaje`, `retencion_iva_porcentaje`, `stock_minimo`, `stock_minimo_base`, `controla_inventario`, `unidad`, `unidad_base`, `escala_unidad_base`, `estado`, `fecha_creacion`, `actualizado_en`
  - ⚠️ NO tiene `codigo_barras` — el código de barras está en `producto_paquete`. Acá el identificador es `referencia`.
  - ⚠️ NO tiene `stock_actual`, `fecha_vencimiento` ni `es_perecedero`.
  - ⚠️ Para márgenes: si `precio_incluye_iva` es true hay que descontar `iva_porcentaje` antes. El IVA no es utilidad.
- **producto_paquete** — presentación vendible (la unidad real de mostrador): `id_producto_paquete`, `id_empresa`, `id_producto`, `referencia`, `nombre`, `codigo_barras`, `unidades_por_paquete`, `unidades_por_item`, `unidad`, `precio_compra`, `precio_venta`, `iva_porcentaje`, `precio_incluye_iva`, `stock_minimo`, `estado`
  - `unidades_por_item` es el factor de conversión a la unidad base del producto.
- **categoria** — `id_categoria`, `id_empresa`, `nombre`, `descripcion`, `color`, `icono`, `estado`
- **marca** — `id_marca`, `id_empresa`, `nombre`, `descripcion`, `estado`, `fecha_creacion`
- **familia** — `id_familia`, `id_empresa`, `nombre`, `descripcion`, `estado`, `creado_en`, `actualizado_en`

#### Inventario — ⚠️ la tabla `inventario` YA NO EXISTE

Está partido en tres tablas. Todas las cantidades van en **unidad base** del producto.

- **saldo_inventario_producto_sucursal_base** — el stock actual: `id_saldo_inventario_producto_base`, `id_empresa`, `id_producto`, `id_sucursal`, `stock_base_disponible`, `stock_base_reservado`, `version`, `creado_en`, `actualizado_en`
  - Una fila por (empresa, producto, sucursal) → agregar antes de joinear con `detalle_venta` o hay fan-out.
- **lote_inventario_producto** — acá vive el vencimiento: `id_lote_inventario_producto`, `id_saldo_inventario_producto_base`, `id_empresa`, `id_producto`, `id_sucursal`, `codigo_lote`, `fecha_vencimiento` (null), `cantidad_base_inicial`, `cantidad_base_disponible`, `costo_unitario_base`, `estado` ('activo'|'agotado'|'vencido'|'bloqueado'|'anulado')
  - Perecedero = tiene lotes con `fecha_vencimiento IS NOT NULL`.
  - Vencimiento más próximo (FEFO): `MIN(fecha_vencimiento) WHERE estado='activo' AND cantidad_base_disponible > 0`.
  - ⚠️ Un lote puede seguir `'activo'` con la fecha ya vencida — nada lo marca solo. Contemplar días negativos.
- **movimiento_inventario_producto** — historial: `id_movimiento_inventario_producto`, `id_empresa`, `id_producto`, `id_sucursal`, `id_usuario` (null), `id_lote_inventario_producto` (null), `id_producto_paquete_presentacion` (null), `tipo_movimiento` ('entrada'|'salida'|'ajuste'|'compra'|'venta'|'devolucion'|'anulacion'|'conversion'), `cantidad_base_firmada`, `unidades_por_item_usadas`, `referencia_tipo`, `referencia_id`, `motivo`, `fecha_movimiento`
  - ⚠️ Reemplaza a `movimiento_inventario`. La cantidad viene **firmada** (negativa en salidas). No existen `cantidad`, `cantidad_anterior`, `cantidad_nueva` ni `es_automatico`.

#### Compras y proveedores
- **compra** — `id_compra`, `id_empresa`, `id_sucursal`, `id_proveedor` (null), `id_usuario`, `id_sesion_caja`, `numero_factura`, `fecha_compra`, `subtotal`, `impuesto`, `total`, `estado`, `observacion`, `proveedor_nombre`, `monto_abonado`, `saldo_pendiente`
  - ⚠️ `estado` admite SOLO `'pendiente'|'pagada'|'abonada'|'cancelada'`. **NO existe `'registrada'`** — filtrar por ese valor devuelve cero filas siempre. Para compras reales: `estado <> 'cancelada'`.
  - `id_proveedor` es null en compras a terceros ocasionales; ahí el nombre está en `proveedor_nombre`.
- **detalle_compra** — `id_detalle_compra`, `id_empresa`, `id_compra`, `id_producto`, `id_producto_paquete`, `cantidad`, `costo_unitario`, `subtotal`, `cantidad_compra`, `unidad_compra`, `factor_conversion`
  - ⚠️ El campo es `costo_unitario`, NO `precio_unitario`
  - `cantidad` está en unidad base; `cantidad_compra` en la unidad en que se compró.
- **proveedor** — `id_proveedor`, `id_empresa`, `nit`, `razon_social`, `nombre_contacto`, `telefono`, `correo`, `direccion`, `estado`, `notas`
  - ⚠️ El nombre del proveedor es `razon_social`, no `nombre`. El email es `correo`, no `email`.

#### Financiero
- **gasto** — `id_gasto`, `id_empresa`, `id_sucursal` (null), `id_categoria_gasto`, `id_usuario`, `descripcion`, `monto`, `fecha_gasto`, `referencia`, `estado` ('registrado'|'anulado'), `metodo_pago`, `proveedor_id`, `proveedor_nombre`, `tercero_nombre`, `tercero_nit`, `iva_incluido`, `iva_monto`, `adjuntos` (jsonb), `id_compra`, `id_gasto_recurrente`, `fecha_programada`
  - ⚠️ Reemplaza a `movimiento_financiero` (que NO existe). Para egresos usar esta tabla.
  - `iva_monto` va aparte del `monto` cuando `iva_incluido` es true.
- **ingreso** — contraparte de `gasto`: `id_ingreso`, `id_empresa`, `id_sucursal`, `id_venta` (null), `id_usuario`, `id_metodo_pago`, `id_abono_venta`, `descripcion`, `monto`, `fecha_ingreso`, `referencia`, `origen` ('venta_pos'|'manual'|'ajuste'|'abono_venta'), `estado` ('registrado'|'anulado')
  - ⚠️ Las ventas del POS generan fila acá. Sumar `venta.total` **y** `ingreso.monto` duplica los ingresos — elegir una sola fuente.
- **movimiento_caja** — `id_movimiento_caja`, `id_empresa`, `id_sesion_caja`, `id_usuario`, `tipo_movimiento` ('ingreso'|'egreso'|'ajuste'|'apertura'|'cierre'|'traslado'), `origen`, `referencia_tipo`, `referencia_id`, `monto`, `descripcion`, `fecha_movimiento`, `sentido` ('entrada'|'salida'), `metodo_pago`, `venta_offline`, `afecta_caja`
  - ⚠️ `monto` es siempre positivo. La dirección la da `sentido`, no el signo. `afecta_caja` marca si mueve efectivo real (una venta con tarjeta no).
- **periodo_financiero** — `id_periodo_financiero`, `id_empresa`, `fecha_inicio`, `fecha_fin`, `tipo_periodo` ('semanal'|'mensual'|'trimestral'|'anual'), `estado` ('abierto'|'cerrado'), `fecha_creacion`
- **resumen_financiero** — `id_resumen_financiero`, `id_empresa`, `id_periodo_financiero`, `total_ingresos`, `total_egresos`, `utilidad_bruta`, `utilidad_operativa`, `impuestos`, `utilidad_neta`, `total_gastos_mercancia`, `total_gastos_servicios`, `total_gastos_impuestos`, `total_gastos_otros`, `impuestos_registro_neto`, `balance`, `margen_neto`, `resultado` ('ganancia'|'perdida'|'equilibrio'), `datos` (jsonb), `fecha_calculo`
  - Trae el desglose de gastos ya separado por tipo — útil para no recalcular desde cero.
- **categoria_gasto** — `id_categoria_gasto`, `id_empresa`, `nombre`, `descripcion`, `estado`, `tipo`, `color`, `icono`, `codigo`, `fecha_creacion`, `actualizado_en`
  - ✅ SÍ tiene campo `tipo`: 'mercancia'|'servicio'|'impuesto'|'otro'. Sirve para separar costo de mercancía de gasto operativo.
- **metodo_pago** — `id_metodo_pago`, `nombre`, `descripcion`, `estado`, `afecta_caja`
- **impuesto** — `id_impuesto`, `id_empresa`, `nombre`, `tipo` ('iva'|'retencion_fuente'|'retencion_iva'|'otro'), `porcentaje`, `estado`, `codigo`, `descripcion`
- **registro_impuesto** — `id_registro_impuesto`, `id_empresa`, `id_impuesto`, `id_sucursal`, `origen` ('venta'|'compra'|'gasto'|'ajuste'), `referencia_id`, `base_gravable`, `valor_impuesto`, `porcentaje`, `naturaleza` ('debito'|'credito'|'retencion'), `estado` ('registrado'|'anulado'), `es_automatico`, `metadata` (jsonb), `fecha_registro`

#### Caja
- **caja** — `id_caja`, `id_empresa`, `id_sucursal`, `nombre`, `estado`, `fecha_creacion`, `default_opening_amount`
- **sesion_caja** — `id_sesion_caja`, `id_empresa`, `id_caja`, `id_usuario_apertura`, `id_usuario_cierre` (null), `fecha_apertura`, `fecha_cierre` (null), `monto_apertura`, `monto_cierre` (null), `estado` ('abierta'|'cerrada'|'anulada'), `observacion`

#### Métricas pre-calculadas (muy útiles para analytics)
- **kpi_resumen** — `id_kpi_resumen`, `id_empresa`, `id_sucursal` (null), `fecha_inicio`, `fecha_fin`, `total_ventas`, `cantidad_ventas`, `ticket_promedio`, `margen_estimado`, `rotacion_inventario`, `productos_bajo_stock`, `datos` (jsonb), `fecha_calculo`
- **metrica_venta_semanal** — `id_metrica_venta_semanal`, `id_empresa`, `id_sucursal` (null), `semana_inicio`, `semana_fin`, `total_ventas`, `cantidad_ventas`, `ticket_promedio`, `hora_pico` (0-23), `dia_pico` (1-7), `datos` (jsonb), `fecha_calculo`
  - ⚠️ `dia_pico` va de 1 a 7 acá — NO es el DOW `0=domingo` que usa el resto del proyecto. Convertir antes de mezclar.
- **metrica_producto_semanal** — `id_metrica_producto_semanal`, `id_empresa`, `id_producto`, `id_sucursal` (null), `semana_inicio`, `semana_fin`, `unidades_vendidas`, `ingresos`, `margen_estimado`, `stock_promedio`, `dias_sin_rotacion`, `clasificacion`, `fecha_calculo`

### Tablas IA — lectura y escritura permitida

> Estas tablas pertenecen a `system_pos` pero el servicio de reportes tiene permiso de escritura sobre ellas.

- **ejecucion_ia** — `id_ejecucion_ia`, `id_empresa`, `tipo_ejecucion` ('manual'|'semanal'|'mensual'), `estado` ('pendiente'|'procesando'|'completada'|'fallida'), `fecha_inicio`, `fecha_fin`, `parametros` (jsonb), `error`, `fecha_creacion`
- **reporte_ia** — `id_reporte_ia`, `id_empresa`, `id_ejecucion_ia` (null), `fecha_inicio`, `fecha_fin`, `titulo`, `resumen`, `estado` ('generado'|'publicado'|'archivado'), `contenido` (jsonb), `fecha_generacion`
- **insight_ia** — `id_insight_ia`, `id_empresa`, `id_reporte_ia`, `tipo_insight`, `titulo`, `descripcion`, `severidad` ('info'|'success'|'warning'|'error'|'critical'), `datos` (jsonb), `fecha_creacion`
- **recomendacion_ia** — `id_recomendacion_ia`, `id_empresa`, `id_reporte_ia`, `tipo_recomendacion`, `titulo`, `descripcion`, `accion_sugerida`, `prioridad` ('baja'|'media'|'alta'|'critica'), `impacto_estimado` (null), `estado` ('pendiente'|'aceptada'|'rechazada'|'aplicada'|'archivada'), `entidad_tipo`, `entidad_id`, `datos` (jsonb), `fecha_creacion`, `fecha_resolucion` (null)

> ⚠️ **Hay una segunda generación de tablas IA en el esquema**, en inglés y paralela a las anteriores.
> Confirmar con el equipo del POS cuál consume el dashboard antes de escribir en cualquiera.

- **ai_reports** — `id_ai_report`, `id_empresa`, `source_report_id` (id externo, único por empresa → sirve de llave de idempotencia), `period_start`, `period_end`, `generated_at`, `prompt_version`, `status` ('pending'|'processing'|'completed'|'failed'), `summary`, `raw_output` (jsonb), `parsed_sections` (jsonb)
- **ai_report_suggestions** — `id_ai_report_suggestion`, `id_ai_report`, `id_empresa`, `type`, `title`, `description`, `affected_products` (jsonb), `priority` ('low'|'medium'|'high'|'urgent'), `action_suggested`, `impact_estimate`, `is_read`, `read_at`
  - ⚠️ La prioridad va en inglés acá, a diferencia de `recomendacion_ia`.
- **ai_report_insert_failures** — cola de fallos de inserción: `payload` (jsonb), `error_message`, `attempts`, `resolved_at`

### Tablas de soporte
- **empresa** — `id_empresa`, `nombre`, `nit`, `correo`, `telefono`, `direccion`, `sector_economico`, `estado`, `fecha_creacion`
  - ⚠️ Email es `correo`, no `email`
- **sucursal** — `id_sucursal`, `id_empresa`, `nombre`, `tipo_negocio`, `direccion`, `telefono`, `estado`, `fecha_creacion`, `ancho_comprobante`
- **usuario** — `id_usuario`, `id_empresa`, `id_sucursal`, `nombre`, `apellido`, `correo`, `username`, `rol`, `estado`, `fecha_creacion`, `token_version`, `ultimo_cambio_rol`, `actualizado_en`
  - ⚠️ Email es `correo`. `password_hash` NO está acá — está en `usuario_credencial`, y nunca se lee en queries de análisis.
- **cliente** — `id_cliente`, `id_empresa`, `tipo_documento`, `numero_documento`, `nombre`, `apellido`, `telefono`, `correo`, `direccion`, `estado`, `nota`, `fecha_registro`, `fecha_creacion`
- **stock_notification_rule** — `id_stock_notification_rule`, `id_producto`, `id_sucursal`, `min_stock`, `enabled`, `cooldown_minutes`, `last_triggered_at`, `created_at`, `updated_at`

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
- **Fuentes:** `lote_inventario_producto` (`fecha_vencimiento`, `cantidad_base_disponible`), `saldo_inventario_producto_sucursal_base` (stock), `producto`, `detalle_venta`
- ⚠️ `es_perecedero` NO existe. Perecederos = tienen lotes con `fecha_vencimiento IS NOT NULL`
- ⚠️ `fecha_vencimiento` está en `lote_inventario_producto`, NO en `producto` ni en `inventario` (que ya no existe)
- ⚠️ Un lote puede seguir `estado='activo'` con la fecha vencida — contemplar días restantes negativos

### 5. Precio Óptimo
- Análisis de elasticidad precio-demanda por producto
- Comparación margen actual vs margen sugerido
- Simulación: "Si sube el precio de X un 10%, estimamos que las ventas bajan Y%"
- **Fuentes:** `detalle_venta` (`precio_unitario` histórico), `producto` (`precio_venta`, `precio_compra`)

### 6. Promociones Inteligentes
- Combos por afinidad (Market Basket Analysis con Apriori)
- Combinar productos estancados con productos estrella
- Promociones para productos próximos a vencer
- **Fuentes:** `detalle_venta` (productos comprados juntos por `id_venta`), `producto`, `saldo_inventario_producto_sucursal_base`, `lote_inventario_producto`

### 7. Predicción de Quiebre de Stock
- Velocidad de venta vs `saldo_inventario_producto_sucursal_base.stock_base_disponible` vs tiempo de reposición del proveedor
- Alerta: "Producto X se agota en N días, el proveedor tarda M días"
- **Fuentes:** `saldo_inventario_producto_sucursal_base`, `detalle_venta`, `compra`, `proveedor`, `stock_notification_rule`
- ⚠️ El stock está en unidad base y `detalle_venta.cantidad` en items de presentación — llevar ambos a la misma unidad antes de dividir

### 8. Score de Salud del Negocio
- Indicador compuesto 0-100 basado en: margen, rotación, desperdicio, tendencia
- Dashboard resumen ejecutivo
- **Fuentes:** `kpi_resumen`, `resumen_financiero`, + todas las anteriores combinadas

### 9. Ventas Flash — sugerencia de promoción de un día ✅ implementado

Una sola sugerencia accionable: qué producto poner en promoción, qué día, a qué precio,
para levantar el día más flojo de la semana moviendo producto que no rota.

- **Día objetivo:** el de menor `transacciones_prom` entre los días **operativos**
- **Producto:** un lento con stock y margen suficiente para aguantar el descuento
  (NO el peor absoluto, que suele ser malo porque nadie lo quiere). Bonus si es
  perecedero próximo a vencer: mueve capital congelado, evita desperdicio y activa
  el día, todo de una.
- **Fuentes:** `venta`, `detalle_venta`, `producto`, `inventario`, `categoria`
- **Código:** `app/analytics/flash_sales.py` (cálculos) + `app/etl/transformers/transform_ventas_flash.py` (orquestación)
- **Clave del JSON:** `ventas_flash`
- **Spec completa:** `features/VENTAS_FLASH(feature).MD` y `features/VENTAS_FLASH_ETL(feature).md`

**Reglas de negocio que NO se pueden romper:**

1. **Día operativo:** un día cuyo promedio de transacciones por ocurrencia caiga bajo
   `MIN_TRANSACCIONES_DIA_OPERATIVO` (default 3) es un día **cerrado**, no un día débil.
   Se descarta del ranking.
2. **Regla de IVA:** `producto.precio_venta` puede incluir IVA. El IVA no es utilidad,
   es recaudo para la DIAN. Márgenes, pisos de utilidad y descuentos se calculan
   **SIEMPRE sobre precio sin IVA**; el `precio_flash` se presenta con IVA de vuelta
   si el precio original lo incluía. Calcular el margen sobre el precio con IVA infla
   el descuento máximo.
3. **Piso de utilidad según urgencia** (sobre precio sin IVA):
   - Lento normal (no perecedero, o vence en +30 días) → mínimo **15%** de margen
   - Perecedero que vence en 8–30 días → mínimo **5%**
   - Perecedero que vence en ≤7 días → hasta **0%** (vender al costo)
4. **Barrera dura:** ningún `precio_flash` queda por debajo del costo, nunca. Regalar
   es decisión manual del dueño, no de la IA.
5. **Stock mínimo:** `MIN_STOCK_PROMO` (default 3) unidades para ser candidato.
6. **Anti fan-out:** `inventario` tiene una fila por `(id_producto, id_sucursal)`. Un
   join directo con `detalle_venta` multiplica filas e infla `SUM(cantidad)`. Se resuelve
   con CTEs separadas (ventas por producto / inventario por producto) unidas por
   `id_producto`.

---

## Schema del JSON del ETL (v1.0)

`app/etl/etl_runner.py` produce un payload con **17 claves en orden fijo**. Ese orden es
parte del contrato: agregar una clave nueva significa insertarla en su posición, no al final.

```
meta · resumen_ejecutivo · ventas_serie_diaria · patron_horario · ventas_flash
productos_top · productos_bottom · categorias · inventario_salud · alertas_stock
perecederos_riesgo · afinidad_productos · proveedores_top · clientes_resumen
gastos_breakdown · sucursales · anomalias_detectadas
```

- **Presupuesto de tamaño:** 8–20 KB. El runner emite `etl.payload.oversized` si supera 50 KB.
- **Ventanas temporales:** el ETL extrae un rango ampliado (`min(fecha_desde − 30d, inicio
  del período de comparación)`) para poder calcular velocidad de venta y comparación
  contra el período anterior en la misma pasada.
- **Convención DOW fija del proyecto:** `0 = domingo … 6 = sábado` (`EXTRACT(DOW)` de
  PostgreSQL). Consistente entre `peak_hours.py` y `flash_sales.py` — no cambiarla.
- **Formato de dinero:** cifras grandes abreviadas (`$180 mil`, `$48.7M`), precios de
  producto completos (`$3.500`).

---

## Specs de features (`features/`)

Las specs de cada feature viven en `features/` como archivos Markdown con formato de
checklist (OBJETIVO / CONTEXTO / ARCHIVOS / TAREAS / REGLAS / DONE). Documentan las
**reglas de negocio y decisiones de diseño** que no se pueden deducir leyendo el código.

| Archivo | Cubre |
|---------|-------|
| `features/VENTAS_FLASH(feature).MD` | Fase 1 — consultas crudas: día débil + pool de productos lentos, sin cálculos derivados |
| `features/VENTAS_FLASH_ETL(feature).md` | Fase 2 — cálculos derivados, regla de IVA, pisos de descuento, selección de candidato y salida al JSON |
| `FEATURE.md` (raíz) | Endpoint síncrono ETL → LLM → `ReportResponse` |

Al implementar o modificar una feature documentada acá, leer primero su spec: contiene
restricciones (IVA, pisos de utilidad, anti fan-out, días cerrados) que el código respeta
pero no explica.

---

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
├── FEATURE.md                   ← spec del endpoint síncrono ETL → LLM
├── db/
│   └── POS-AI-scriptdb.sql      ← ⭐ DDL del esquema system_pos — FUENTE DE VERDAD
├── features/                    ← specs de features (reglas de negocio, checklists)
│   ├── VENTAS_FLASH(feature).MD      ← fase 1: consultas crudas
│   └── VENTAS_FLASH_ETL(feature).md  ← fase 2: cálculos, IVA, descuentos, salida
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
│   │   ├── etl_runner.py        ← ORQUESTADOR: extract → transform → load → JSON
│   │   ├── json_loader.py       ← LEE el JSON del ETL (lo consume el servicio)
│   │   ├── extractors/          ← SQL crudo, un archivo por dominio
│   │   │   ├── base_extractor.py
│   │   │   ├── extract_catalogo.py     ← productos, categorías, marcas, proveedores, sucursales
│   │   │   ├── extract_ventas.py
│   │   │   ├── extract_inventario.py
│   │   │   ├── extract_compras.py
│   │   │   ├── extract_gastos.py
│   │   │   └── extract_movimientos.py
│   │   ├── transformers/        ← 13 transformers, uno por clave del JSON (NO calculan)
│   │   │   ├── transform_meta.py
│   │   │   ├── transform_resumen_ejecutivo.py
│   │   │   ├── transform_ventas_serie.py
│   │   │   ├── transform_patron_horario.py
│   │   │   ├── transform_ventas_flash.py
│   │   │   ├── transform_productos.py         ← top + bottom + categorías
│   │   │   ├── transform_inventario.py        ← salud + alertas + perecederos
│   │   │   ├── transform_afinidad.py
│   │   │   ├── transform_proveedores.py
│   │   │   ├── transform_clientes.py
│   │   │   ├── transform_gastos.py
│   │   │   ├── transform_sucursales.py
│   │   │   └── transform_anomalias.py
│   │   ├── loaders/
│   │   │   └── json_loader.py   ← ESCRIBE el JSON en disco (≠ etl/json_loader.py)
│   │   ├── output/              ← empresa_{id}_{desde}_{hasta}.json (gitignorable)
│   │   ├── sync_ventas.py       ← ⏳ stub, reservado fase TimescaleDB — NO TOCAR
│   │   ├── sync_inventario.py   ← ⏳ stub, reservado fase TimescaleDB — NO TOCAR
│   │   ├── sync_financiero.py   ← ⏳ stub, reservado fase TimescaleDB — NO TOCAR
│   │   └── base.py              ← clase base para sincronizadores
│   ├── analytics/               ← TODA la aritmética del proyecto vive aquí
│   │   ├── __init__.py
│   │   ├── periods.py           ← ventanas temporales y período de comparación
│   │   ├── revenue.py           ← ingresos/egresos (venta + gasto)
│   │   ├── financials.py        ← márgenes, utilidad, resumen ejecutivo
│   │   ├── expenses.py          ← breakdown de gastos
│   │   ├── product_ranking.py   ← top/bottom productos
│   │   ├── peak_hours.py        ← horas mágicas (DOW 0=domingo)
│   │   ├── flash_sales.py       ← venta flash: día débil + producto + IVA + descuento
│   │   ├── expiry_tracker.py    ← anti-desperdicio (via inventario.fecha_vencimiento)
│   │   ├── inventory_health.py  ← salud de inventario
│   │   ├── stock_predictor.py   ← velocidad de venta y quiebre de stock
│   │   ├── promotions.py        ← motor de promociones (Apriori)
│   │   ├── customers.py         ← clientes nuevos vs recurrentes
│   │   ├── anomalies.py         ← detección de anomalías
│   │   ├── trends.py            ← utilidades de tendencia
│   │   ├── pricing.py           ← ⏳ pendiente — precio óptimo
│   │   └── health_score.py      ← ⏳ pendiente — score de salud del negocio
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── llm_client.py        ← LMStudio + OpenAI + Gemini(⏳) + Claude
│   │   ├── router.py            ← ⏳ routing entre modelos (aún no se usa)
│   │   ├── report_generator.py  ← carga general_prompt + recorta payload + parsea
│   │   └── prompt_templates/
│   │       ├── general_prompt.txt      ← ✅ EL QUE SE USA HOY (5 secciones en una pasada)
│   │       ├── flash_sales.txt
│   │       ├── ingresos_egresos.txt
│   │       ├── top_bottom_productos.txt
│   │       ├── horas_magicas.txt
│   │       ├── anti_desperdicio.txt
│   │       ├── precio_optimo.txt
│   │       ├── promociones.txt
│   │       ├── quiebre_stock.txt
│   │       ├── score_salud.txt
│   │       └── ejecutivo_completo.txt
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
│   │   ├── test_api.py
│   │   ├── test_llm_router.py
│   │   └── test_etl/            ← json_loader + transformers
│   └── integration/
│       └── __init__.py
├── scripts/
│   ├── init_db.py               ← inicializa DB analítica
│   └── test_connection.py       ← verifica conexión a la DB del POS
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
- **Separación ETL:** los **extractors** solo hacen SELECT, los **transformers** solo orquestan,
  y **toda la aritmética vive en `app/analytics/`**. Un transformer que calcula está mal ubicado.
- **DOW:** `0 = domingo … 6 = sábado` en todo el proyecto (`EXTRACT(DOW)` de PostgreSQL)

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
# 1. Verificar conexión a la DB del POS
python scripts/test_connection.py

# 2. Correr el ETL suelto — OPCIONAL, para inspeccionar el JSON sin llamar al LLM.
#    El endpoint /generate ya lo dispara solo con las fechas del request.
python -m app.etl.etl_runner --empresa-id 5 --fecha-desde 2026-08-01 --fecha-hasta 2026-09-08

# 3. Levantar la API
uvicorn app.main:app --reload --port 8001

# 4. Pedir el reporte — corre el ETL con estas fechas y después el LLM (~17s).
#    No hace falta el paso 2: el JSON se genera dentro de la misma petición.
curl -X POST http://localhost:8001/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"empresa_id":5,"fecha_desde":"2026-08-01","fecha_hasta":"2026-09-08"}'

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
2. **Reportes son batch, no real-time.** Objetivo: Celery + caché en Redis. **Hoy** el flujo
   es síncrono — `POST /generate` corre el ETL con las fechas del request (bloqueando la
   petición ~10s) y luego el LLM; el JSON queda en `app/etl/output/` y se sobrescribe.
3. **Multi-tenant:** todo filtrado por `id_empresa`. Cada empresa ve solo sus datos.
4. **El mercado objetivo es Colombia** — moneda COP, zona horaria America/Bogota, español.
5. **Los prompt templates deben ser en español** — los reportes se entregan en español.
6. **Batch API:** usar batch endpoints de los LLMs para reducir costos 50%.
7. **Schema siempre explícito:** en SQLAlchemy usar `__table_args__ = {"schema": "system_pos"}`.
8. **`movimiento_financiero` NO EXISTE** — para egresos usar `gasto`, para flujo de caja usar `movimiento_caja`.
9. **`inventario` y `movimiento_inventario` NO EXISTEN** — el inventario está en `saldo_inventario_producto_sucursal_base` (stock), `lote_inventario_producto` (vencimiento) y `movimiento_inventario_producto` (historial). `es_perecedero` tampoco existe: es perecedero si tiene lotes con `fecha_vencimiento IS NOT NULL`.
10. **`catalogo_productos_general` NO EXISTE** — los datos maestros están en `producto`; el `codigo_barras` está en `producto_paquete` y en `producto` el identificador es `referencia`.
11. **Las métricas pre-calculadas** (`kpi_resumen`, `metrica_venta_semanal`, `metrica_producto_semanal`, `resumen_financiero`) ya están en el POS DB — usarlas cuando estén disponibles para evitar recalcular.
11b. **Cuidado al mezclar unidades.** El stock está en **unidad base** del producto; `detalle_venta.cantidad` está en **items de la presentación** vendida, con el factor en `unidades_por_item_usadas`. Dividir stock entre velocidad de venta sin normalizar da días de cobertura equivocados. Un producto pesable (banano en gramos) lo hace evidente: stock 23.701 contra ventas de 5 "unidades".
12. **El LLM no calcula.** Recibe números listos. Si una cifra hay que derivarla, se deriva en
    `app/analytics/` y se mete al JSON — nunca se le pide al modelo que la saque.
13. **El DDL manda sobre el resumen.** `db/POS-AI-scriptdb.sql` es la fuente de verdad del
    esquema; la sección "Base de Datos del POS" de este archivo es solo un resumen y puede
    quedar desactualizada. Re-exportar el DDL cuando el POS cambie de esquema
    (`pg_dump --schema-only --schema=system_pos`) y actualizar su fecha de exportación.
14. **Antes de tocar una feature documentada, leer su spec en `features/`.** Ahí están las
    reglas que el código respeta pero no explica: regla de IVA, pisos de utilidad, exclusión
    de días cerrados, anti fan-out en joins con `inventario`.
15. **`sync_ventas.py`, `sync_inventario.py`, `sync_financiero.py` y `base.py` no se tocan** —
    están reservados para la fase TimescaleDB.
16. **El orden de las 17 claves del JSON es contrato.** Una clave nueva se inserta en su
    posición, no al final.
17. **Estado actual — lo que NO está conectado:** Celery/Redis (tareas vacías), DB analítica
    TimescaleDB (sin modelos ni sincronizadores), persistencia en las tablas IA (nada se
    guarda en `reporte_ia`/`insight_ia`/`recomendacion_ia`), `GET /reports/{id}` y
    `GET /reports/empresa/{id}` (501), routing dual Gemini/Claude, y generación de PDF.
