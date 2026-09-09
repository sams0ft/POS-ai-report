OBJETIVO
Sobre las consultas crudas de flash_sales.py, calcular las métricas
derivadas, elegir el día objetivo y el producto, armar el bloque de
sugerencia "venta flash por día" y exponerlo en el JSON del ETL.

DECISIÓN A CONFIRMAR ANTES DE TOCAR NADA
[ ] Nombre de la key en el JSON (propuesta: "ventas_flash") 

CONTEXTO
- Microservicio read-only sobre la DB del POS (schema system_pos, Supabase).
- Fuente de verdad del esquema: db/POS-AI-scriptdb.sql y CLAUDE.md.
- Las consultas crudas ya existen en app/analytics/flash_sales.py (Prompt 1):
  devuelven "dia_debil_crudo" y "pool_productos_crudo".
- TODA la aritmética vive en app/analytics/. El transformer solo orquesta.
  El LLM NO calcula nada: recibe números ya listos.

ARCHIVOS
[ ] app/analytics/flash_sales.py       (ampliar con los cálculos)
[ ] transformer orquestador en app/etl/transformers/  (SOLO llama a analytics
    y coloca el resultado en la key; NADA de lógica de negocio)

TAREA 1 — Cálculos del día débil
[ ] Promedio por ocurrencia (no por suma bruta):
    transacciones_prom = transacciones / ocurrencias
    monto_prom = monto / ocurrencias
[ ] Excluir días CERRADOS: si transacciones_prom cae por debajo de un umbral
    configurable, ese día no es "débil", es un día que no se opera.
    Descártalo. Documenta el umbral en el archivo.
[ ] Promedio general de transacciones entre días OPERATIVOS.
[ ] Día objetivo = el de menor transacciones_prom entre los operativos.
[ ] pct_bajo_promedio = qué tanto está ese día por debajo del promedio general
    (para explicar el "porqué" en la sugerencia).

TAREA 2 — Selección del producto + cálculos
[ ] Filtrar el pool: stock_actual > 0 (tiene que estar en inventario para
    poder promocionarlo).
[ ] Por producto calcular:
    - velocidad_venta = unidades_vendidas / días_del_período
    - dias_para_vencer = fecha_vencimiento - fecha_referencia (si aplica)
    - margen_actual: VER REGLA DE IVA abajo.

    REGLA DE IVA (importante, no la saltes):
    El precio_venta puede incluir IVA (columna producto.precio_incluye_iva).
    El IVA NO es utilidad del negocio, es recaudo para la DIAN. Si calculas
    el margen sobre el precio CON IVA, el descuento máximo saldrá inflado.
    - Si precio_incluye_iva = true: calcula un precio_sin_iva quitando el
      iva_porcentaje del producto, y saca el margen sobre ese valor.
    - Si precio_incluye_iva = false: usa precio_venta tal cual.
    Trabaja el piso de utilidad y el descuento SIEMPRE sobre valores sin IVA.

[ ] REGLA DE DESCUENTO MÁXIMO (piso de utilidad, sobre precio sin IVA):
    Elige el piso según urgencia del producto:
    - Lento normal (no perecedero, o vence en +30 días): mínimo 15% de margen
    - Perecedero que vence en 8-30 días:                  mínimo 5% de margen
    - Perecedero que vence en ≤7 días:                    permite hasta 0%
                                                          (vender al costo)
    - BARRERA DURA en todos los casos: NUNCA por debajo del costo.
      El sistema jamás sugiere un precio flash que haga perder plata en la
      unidad. Regalar es decisión manual del dueño, no de la IA.

    Con el piso correspondiente, calcula:
    - descuento_maximo (%)
    - precio_flash = precio con ese descuento (preséntalo como lo paga el
      cliente, es decir con IVA de vuelta si el precio original lo incluía)
    - margen_tras_descuento

[ ] Elegir el candidato con esta prioridad (NO el peor absoluto, que suele
    ser malo porque nadie lo quiere):
    entre los lentos, uno que tenga margen suficiente para aguantar descuento
    Y stock suficiente para la promo; BONUS si es perecedero próximo a vencer
    (mueve capital congelado + evita desperdicio + activa el día, todo de una).

[ ] impacto_estimado_cop: rango precalculado con supuesto explícito
    (ej: "si se mueven N unidades ese día a precio flash → ~$X").

TAREA 3 — Bloque de salida para el JSON
[ ] dict con:
    - dia_objetivo: { nombre_es, indice_dow }   (DOW 0=domingo … 6=sábado)
    - transacciones_promedio_dia
    - pct_bajo_promedio
    - producto: { id_producto, nombre, categoria, precio_normal, precio_flash,
      descuento_pct, margen_tras_descuento, stock_actual, es_perecedero,
      dias_para_vencer }
    - impacto_estimado_cop: { rango, supuesto }
    - como_medir: qué comparar a las 2 semanas — flujo de ese día con flash
      vs promedio base del mismo día (para cerrar el ciclo con estado).
[ ] Formato de dinero: cifras grandes abreviadas ($180 mil), precios de
    producto completos ($3.500).
[ ] Nombres de día en español según DOW 0=domingo.

TAREA 4 — ETL
[ ] En el transformer, llamar la función de analytics y colocar su resultado
    bajo la key confirmada, respetando el orden fijo del payload.
[ ] Verificar que el payload total sigue en ~10–20 KB.

REGLAS GENERALES
[ ] TODA la aritmética en app/analytics/ (promedios, IVA, margen, descuento,
    impacto). El transformer y el LLM NO calculan nada.
[ ] Convención DOW fija del proyecto: 0=domingo … 6=sábado. Consistente con
    peak_hours.py.
[ ] async/await, type hints, docstrings Google en español.
[ ] Solo lectura de la DB. No escribir.
[ ] NO tocar app/etl/base.py, sync_ventas.py, sync_inventario.py,
    sync_financiero.py (reservados para la fase TimescaleDB).

DONE
[ ] Corriendo el ETL con data real, la key aparece con día objetivo, producto
    elegido, precio flash e impacto coherentes.
[ ] El día elegido es el más débil OPERATIVO (no un día cerrado).
[ ] El producto tiene stock y margen para aguantar el descuento (no el peor
    absoluto sin salida).
[ ] El margen y el descuento se calcularon sobre precio SIN IVA.
[ ] Ningún precio flash queda por debajo del costo.