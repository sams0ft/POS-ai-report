# FEATURE.md — Endpoint síncrono: ETL → LLM → ReportResponse

## Contexto

El ETL ya corre y produce un JSON en `app/etl/output/empresa_{id}_{fecha_desde}_{fecha_hasta}.json`.
El endpoint `POST /api/v1/reports/generate` existe pero devuelve `PENDING` sin hacer nada.

El objetivo es conectar ese JSON con LM Studio usando un único prompt general y devolver
el análisis completo con todas las sugerencias del negocio en una sola llamada síncrona.

**Modelo LLM:** únicamente `LMStudioClient` — ya implementado en `app/ai/llm_client.py`.
Las credenciales y URL ya están en `.env` (`LMSTUDIO_URL`, `LMSTUDIO_MODEL`).

**Fuera de alcance de esta feature:** `report_type`, templates individuales, Celery async, Redis, guardar en DB, PDFs, `list_reports`.

---

## Fase 1 — Crear el prompt general

**Archivo:** `app/ai/prompt_templates/general_prompt.txt` ← crear desde cero

- [ ] Un único template que recibe todo el JSON del ETL y genera el análisis completo del negocio
- [ ] El template debe cubrir todas las dimensiones en una sola pasada:
  - Resumen ejecutivo del período
  - Análisis de ventas e ingresos
  - Productos con mejor y peor rendimiento
  - Productos perecederos en riesgo
  - Patrones de hora y día
  - Estado del inventario
  - Gastos operativos
  - Sugerencias accionables priorizadas
- [ ] Placeholders del template: solo `{empresa}`, `{periodo}` y `{datos}`
- [ ] El tono debe ser el de un asesor de negocios hablándole directo al dueño de la tienda
- [ ] Respuesta esperada en español colombiano, moneda COP

---

## Fase 2 — Lector del JSON del ETL

**Archivo:** `app/etl/json_loader.py` ← crear desde cero

- [ ] Crear función `load_etl_json(empresa_id, fecha_desde, fecha_hasta) -> dict`
- [ ] Construir el path del archivo usando el mismo patrón que ya usa `etl_runner.py`
- [ ] Si el archivo no existe → lanzar error con mensaje que indique el comando exacto para correr el ETL
- [ ] Si existe → leer y retornar el dict completo sin transformarlo

---

## Fase 3 — Simplificar el generador de reportes

**Archivo:** `app/ai/report_generator.py` ← modificar

- [ ] Eliminar toda la lógica de `report_type` y selección de templates
- [ ] Cargar siempre `app/ai/prompt_templates/general_prompt.txt`
- [ ] Usar siempre `LMStudioClient` directamente — sin pasar por `router.py`
- [ ] Serializar `analytics_data` (dict del ETL) a JSON indentado antes de inyectarlo en `{datos}`
- [ ] Implementar parseo de la respuesta para extraer `sugerencias: list[str]`
  - Buscar líneas numeradas o con bullets en la respuesta
  - Si no encuentra estructura → tomar los últimos párrafos como fallback
- [ ] Retornar `{ "resumen": str, "sugerencias": list[str], "datos": dict }`

---

## Fase 4 — Lógica de negocio en el servicio

**Archivo:** `app/services/report_service.py` ← modificar

- [ ] Agregar método `generate_sync(request: ReportRequest) -> ReportResponse`
  - Llamar a `load_etl_json()` de la Fase 2
  - Si no encuentra el archivo → lanzar `HTTPException 404` con el mensaje de error
  - Extraer `empresa_nombre` del campo `metadata.empresa_nombre` del JSON del ETL
  - Construir el string `periodo` legible (ej: `"1 Abr 2026 – 30 Abr 2026"`)
  - Llamar a `generate_report_content()` de la Fase 3
  - Si LM Studio falla → lanzar `HTTPException 502` con detalle del error
  - Retornar `ReportResponse` con `status=COMPLETED`, `datos`, `resumen` y `sugerencias`
- [ ] `enqueue_report()` — dejar como está
- [ ] `get_report()` y `list_reports()` — dejar lanzando `NotImplementedError`

---

## Fase 5 — Simplificar el endpoint

**Archivo:** `app/api/v1/reports.py` ← modificar

- [ ] `POST /generate` → el body solo necesita `empresa_id`, `fecha_desde`, `fecha_hasta`
  - Eliminar `report_type` del request si es posible, o ignorarlo si el schema lo requiere
  - Llamar a `service.generate_sync(request)`
- [ ] `GET /{report_id}` → devolver `HTTPException 501` con mensaje "pendiente de implementar"
- [ ] `GET /empresa/{empresa_id}` → dejar como está

**Archivo:** `app/schemas/reports.py` ← revisar
- [ ] Si `report_type` es requerido en `ReportRequest`, hacerlo opcional con `None` como default
  - El endpoint ya no lo necesita para nada

---

## Fase 6 — Verificación

- [ ] Confirmar que LM Studio está corriendo en el puerto configurado en `.env`
- [ ] Arrancar el servidor: `uvicorn app.main:app --reload --port 8001`
- [ ] Llamar al endpoint con `empresa_id`, `fecha_desde`, `fecha_hasta` → debe devolver `status: completed` con el análisis completo independientemente del `report_type` enviado
- [ ] Llamar sin JSON del ETL disponible → debe devolver `404` con el comando del ETL
- [ ] Revisar que `sugerencias` en la respuesta contiene acciones concretas, no párrafos genéricos

---

## Referencia rápida de archivos

| Fase | Archivo | Acción |
|------|---------|--------|
| 1 | `app/ai/prompt_templates/general_prompt.txt` | Crear |
| 2 | `app/etl/json_loader.py` | Crear |
| 3 | `app/ai/report_generator.py` | Modificar |
| 4 | `app/services/report_service.py` | Modificar |
| 5 | `app/api/v1/reports.py` | Modificar |
| 5 | `app/schemas/reports.py` | Revisar — hacer `report_type` opcional |
| — | `app/ai/llm_client.py` | No tocar (LMStudioClient ya funciona) |
| — | `app/ai/router.py` | No tocar |
| — | `app/etl/etl_runner.py` | No tocar |
| — | `app/ai/prompt_templates/*.txt` | No tocar (los individuales quedan como referencia) |
