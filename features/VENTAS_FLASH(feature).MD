OBJETIVO
Crear las dos consultas base para la sugerencia "venta flash por día":
(1) el día más débil de la semana y (2) el pool de productos lentos.
Deben devolver datos CRUDOS agregados, sin cálculos derivados todavía,
para validar antes de calcular nada.

CONTEXTO
- Microservicio read-only sobre la DB del POS (schema system_pos, Supabase).
- Fuente de verdad del esquema: db/POS-AI-scriptdb.sql y CLAUDE.md.
- OJO: app/analytics/peak_hours.py y product_ranking.py usan nombres de
  columna VIEJOS (monto_total, p.id, ventas...) que NO coinciden con el
  esquema real. Usa SIEMPRE los nombres reales del script SQL. No copies
  de esos archivos.
- Usa prefijo explícito system_pos. en todas las tablas.

ARCHIVO A CREAR
[ ] app/analytics/flash_sales.py   (si prefieres otro nombre, avísame)

TAREA 1 — Día débil (función async: pos_db, empresa_id, fecha_desde, fecha_hasta)
[ ] Fuente: system_pos.venta
[ ] Filtros: id_empresa = empresa_id, estado = 'completada',
    fecha_venta entre fecha_desde y fecha_hasta
[ ] Agrupar por día de semana con EXTRACT(DOW FROM fecha_venta).
    CONVENCIÓN FIJA DEL PROYECTO: DOW 0=domingo, 1=lunes ... 6=sábado.
    Documenta esta convención en el archivo (unifica con peak_hours.py).
[ ] Por cada día devolver crudo, SIN promediar en SQL:
    - transacciones: COUNT(DISTINCT id_venta)
    - monto: SUM(total)
    - ocurrencias: cuántas veces ocurrió ese día en el período
      (COUNT DISTINCT sobre la fecha calendario, no el timestamp)
[ ] Ordenar por día de semana asc.

TAREA 2 — Pool de productos candidatos (mismo archivo)
[ ] IMPORTANTE (evitar fan-out): inventario tiene una fila por
    (id_producto, id_sucursal). Un join directo con detalle_venta
    multiplica filas e infla SUM(cantidad). Solución:
    - CTE A: ventas por producto (SUM cantidad, SUM subtotal)
    - CTE B: inventario por producto (SUM stock_actual como stock total,
      MIN fecha_vencimiento como vencimiento más próximo)
    - unir A y B por id_producto
[ ] Fuentes: system_pos.detalle_venta, system_pos.venta, system_pos.producto,
    system_pos.inventario, system_pos.categoria (nombres/joins con columnas
    reales: v.id_venta, p.id_producto, p.id_categoria = c.id_categoria, etc.)
[ ] Filtros: v.id_empresa = empresa_id, v.estado = 'completada',
    v.fecha_venta en el rango, p.estado = true
[ ] Devolver por producto: id_producto, nombre, categoria (c.nombre),
    unidades_vendidas, ingresos, precio_venta, precio_compra,
    stock_actual, fecha_vencimiento
[ ] Ordenar por unidades_vendidas asc (los más lentos primero)
[ ] NO filtrar por stock ni elegir candidato aquí: devuelve el pool crudo.

REGLAS
[ ] async/await, SQLAlchemy 2.0 con text() y parámetros nombrados,
    type hints, docstring Google en español.
[ ] Solo SELECT. No escribir en la DB.
[ ] NO tocar app/etl/base.py, sync_ventas.py, sync_inventario.py,
    sync_financiero.py (reservados para la fase TimescaleDB).
[ ] Devolver un dict con las dos estructuras crudas:
    { "dia_debil_crudo": [...], "pool_productos_crudo": [...] }

DONE
[ ] Se ejecuta con un empresa_id y rango real y muestra ambos datasets.
[ ] Todos los nombres de columna coinciden 100% con db/POS-AI-scriptdb.sql.
[ ] Cero cálculos derivados (eso es el siguiente prompt).