"""Analytics: datos crudos y cálculos derivados para sugerencia "venta flash por día".

Convención DOW (EXTRACT DOW de PostgreSQL, compartida con peak_hours.py):
    0 = domingo, 1 = lunes, 2 = martes, 3 = miércoles,
    4 = jueves, 5 = viernes, 6 = sábado

Key en el JSON del ETL: "ventas_flash"

Umbral de día operativo: MIN_TRANSACCIONES_DIA_OPERATIVO
    Un día cuyo promedio de transacciones por ocurrencia quede por debajo de
    este valor se considera día cerrado o atípico y se excluye del ranking.
    Ajustar según el volumen real del negocio; valor por defecto: 3.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# --- Constantes del módulo ---

MIN_TRANSACCIONES_DIA_OPERATIVO: int = 3
MIN_STOCK_PROMO: int = 3  # Unidades mínimas en stock para que el producto sea candidato a promo

NOMBRES_DIA_ES: dict[int, str] = {
    0: "domingo",
    1: "lunes",
    2: "martes",
    3: "miércoles",
    4: "jueves",
    5: "viernes",
    6: "sábado",
}


async def get_dia_debil_crudo(
    db: AsyncSession,
    empresa_id: int,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict]:
    """Devuelve ventas agrupadas por día de semana, sin promedios calculados.

    Cada fila contiene el acumulado bruto del día de semana en el período:
    transacciones totales, monto total y cuántas veces ocurrió ese día en
    el rango. El promedio se calcula en la capa siguiente, no aquí.

    Args:
        db: Sesión async a la DB del POS (read-only).
        empresa_id: ID de la empresa.
        fecha_desde: Inicio del período (inclusive).
        fecha_hasta: Fin del período (inclusive).

    Returns:
        Lista de dicts ordenados por dow asc, cada uno con:
        ``dow`` (0=domingo…6=sábado), ``transacciones``, ``monto_total``,
        ``ocurrencias`` (días calendario distintos con ese DOW en el rango).
    """
    result = await db.execute(
        text(
            """
            SELECT
                EXTRACT(DOW FROM fecha_venta)::int       AS dow,
                COUNT(DISTINCT id_venta)                 AS transacciones,
                SUM(total)                               AS monto_total,
                COUNT(DISTINCT fecha_venta::date)        AS ocurrencias
            FROM system_pos.venta
            WHERE id_empresa       = :empresa_id
              AND estado           = 'completada'
              AND fecha_venta::date BETWEEN :fecha_desde AND :fecha_hasta
            GROUP BY dow
            ORDER BY dow ASC
            """
        ),
        {
            "empresa_id": empresa_id,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        },
    )
    rows = result.mappings().all()
    return [
        {
            "dow": int(row["dow"]),
            "transacciones": int(row["transacciones"]),
            "monto_total": float(row["monto_total"] or 0),
            "ocurrencias": int(row["ocurrencias"]),
        }
        for row in rows
    ]


async def get_pool_productos_crudo(
    db: AsyncSession,
    empresa_id: int,
    fecha_desde: date,
    fecha_hasta: date,
) -> list[dict]:
    """Devuelve el pool completo de productos candidatos a venta flash.

    Usa CTEs separadas para evitar fan-out: el saldo de inventario tiene una
    fila por (producto, sucursal) y los lotes varias por producto, así que un
    join directo con detalle_venta multiplicaría filas e inflaría SUM(cantidad).
    - CTE A agrega ventas por producto.
    - CTE B agrega stock por producto (suma sobre sucursales).
    - CTE C toma el vencimiento más próximo entre los lotes activos con
      existencias (FEFO).

    No filtra por stock ni selecciona candidatos: devuelve datos crudos para
    que la capa siguiente aplique las reglas de negocio.

    Args:
        db: Sesión async a la DB del POS (read-only).
        empresa_id: ID de la empresa.
        fecha_desde: Inicio del período (inclusive).
        fecha_hasta: Fin del período (inclusive).

    Returns:
        Lista de dicts ordenados por unidades_vendidas asc (más lentos primero),
        cada uno con: ``id_producto``, ``nombre``, ``categoria``,
        ``unidades_vendidas``, ``ingresos``, ``precio_venta``,
        ``precio_compra``, ``stock_actual``, ``fecha_vencimiento``.
    """
    result = await db.execute(
        text(
            """
            WITH ventas_por_producto AS (
                SELECT
                    dv.id_producto,
                    SUM(dv.cantidad)  AS unidades_vendidas,
                    SUM(dv.subtotal)  AS ingresos
                FROM system_pos.detalle_venta dv
                JOIN system_pos.venta v ON v.id_venta = dv.id_venta
                WHERE v.id_empresa        = :empresa_id
                  AND v.estado            = 'completada'
                  AND v.fecha_venta::date BETWEEN :fecha_desde AND :fecha_hasta
                GROUP BY dv.id_producto
            ),
            stock_por_producto AS (
                SELECT
                    s.id_producto,
                    SUM(s.stock_base_disponible) AS stock_actual
                FROM system_pos.saldo_inventario_producto_sucursal_base s
                WHERE s.id_empresa = :empresa_id
                GROUP BY s.id_producto
            ),
            vencimiento_por_producto AS (
                SELECT
                    l.id_producto,
                    MIN(l.fecha_vencimiento) AS fecha_vencimiento
                FROM system_pos.lote_inventario_producto l
                WHERE l.id_empresa               = :empresa_id
                  AND l.estado                   = 'activo'
                  AND l.cantidad_base_disponible > 0
                  AND l.fecha_vencimiento IS NOT NULL
                GROUP BY l.id_producto
            )
            SELECT
                p.id_producto,
                p.nombre,
                c.nombre                        AS categoria,
                vp.unidades_vendidas,
                vp.ingresos,
                p.precio_venta,
                p.precio_compra,
                p.precio_incluye_iva,
                p.iva_porcentaje,
                COALESCE(sp.stock_actual, 0)    AS stock_actual,
                vc.fecha_vencimiento
            FROM ventas_por_producto vp
            JOIN system_pos.producto p   ON p.id_producto  = vp.id_producto
            LEFT JOIN system_pos.categoria c ON c.id_categoria = p.id_categoria
            LEFT JOIN stock_por_producto sp        ON sp.id_producto = p.id_producto
            LEFT JOIN vencimiento_por_producto vc  ON vc.id_producto = p.id_producto
            WHERE p.id_empresa = :empresa_id
              AND p.estado     = true
            ORDER BY vp.unidades_vendidas ASC
            """
        ),
        {
            "empresa_id": empresa_id,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        },
    )
    rows = result.mappings().all()
    return [
        {
            "id_producto": int(row["id_producto"]),
            "nombre": str(row["nombre"]),
            "categoria": str(row["categoria"] or ""),
            "unidades_vendidas": float(row["unidades_vendidas"] or 0),
            "ingresos": float(row["ingresos"] or 0),
            "precio_venta": float(row["precio_venta"] or 0),
            "precio_compra": float(row["precio_compra"] or 0),
            "precio_incluye_iva": bool(row["precio_incluye_iva"] or False),
            "iva_porcentaje": float(row["iva_porcentaje"] or 0),
            "stock_actual": float(row["stock_actual"] or 0),
            "fecha_vencimiento": row["fecha_vencimiento"].isoformat()
            if row["fecha_vencimiento"]
            else None,
        }
        for row in rows
    ]


# ─── Helpers privados de IVA, precios y formato ───────────────────────────


def _precio_sin_iva(precio: float, incluye_iva: bool, iva_pct: float) -> float:
    """Devuelve el precio sin IVA. Si no incluye IVA, lo retorna tal cual."""
    if incluye_iva and iva_pct > 0:
        return precio / (1 + iva_pct / 100)
    return precio


def _aplicar_iva(precio_base: float, incluye_iva: bool, iva_pct: float) -> float:
    """Añade IVA al precio base. Solo si el precio original lo incluía."""
    if incluye_iva and iva_pct > 0:
        return precio_base * (1 + iva_pct / 100)
    return precio_base


def _piso_margen(dias_para_vencer: int | None) -> float:
    """Retorna el piso de margen mínimo según urgencia del producto.

    Lento normal (sin fecha o vence en +30 días): 15%
    Perecedero que vence en 8-30 días: 5%
    Perecedero que vence en ≤7 días: 0% (el límite inferior es el costo)
    """
    if dias_para_vencer is None or dias_para_vencer > 30:
        return 0.15
    if dias_para_vencer >= 8:
        return 0.05
    return 0.0


def _fmt_cop_abreviado(valor: float) -> str:
    """COP abreviado colombiano: '$180 mil', '$1,2 millones'."""
    if valor >= 1_000_000:
        return f"${valor / 1_000_000:.1f} millones".replace(".", ",")
    if valor >= 1_000:
        return f"${round(valor / 1_000)} mil"
    return f"${round(valor)}"


def _fmt_cop_precio(valor: float) -> str:
    """COP precio completo con punto como separador de miles: '$3.500'."""
    return "$" + f"{round(valor):,}".replace(",", ".")


# ─── Selección del candidato y cálculos derivados ─────────────────────────


def calcular_candidato_flash(
    pool_productos_crudo: list[dict],
    dias_periodo: int,
    fecha_referencia: date,
) -> dict | None:
    """Filtra el pool, calcula métricas IVA-correctas y elige el candidato flash.

    Reglas aplicadas:
    - Solo productos con stock_actual >= MIN_STOCK_PROMO.
    - Margen y descuento calculados SIEMPRE sobre precio sin IVA.
    - Precio flash presentado al cliente CON IVA si el original lo incluía.
    - BARRERA DURA: precio_flash nunca queda por debajo de precio_compra.
    - Selección: prioriza perecederos próximos a vencer sobre lentos sin urgencia.
      Entre igual bonus, elige el de menor velocidad de venta.

    Args:
        pool_productos_crudo: Resultado de get_pool_productos_crudo.
        dias_periodo: Días del período analizado (para calcular velocidad_venta).
        fecha_referencia: Fecha de corte para calcular dias_para_vencer (fecha_hasta).

    Returns:
        Dict con el candidato elegido y su precio flash, o None si no hay viables.
    """
    if not pool_productos_crudo or dias_periodo <= 0:
        return None

    candidatos: list[dict] = []

    for p in pool_productos_crudo:
        stock = p.get("stock_actual", 0) or 0
        if stock < MIN_STOCK_PROMO:
            continue

        precio_venta = float(p.get("precio_venta", 0) or 0)
        precio_compra = float(p.get("precio_compra", 0) or 0)
        if precio_venta <= 0 or precio_compra <= 0:
            continue

        incluye_iva = bool(p.get("precio_incluye_iva", False))
        iva_pct = float(p.get("iva_porcentaje", 0) or 0)

        precio_sin_iva = _precio_sin_iva(precio_venta, incluye_iva, iva_pct)

        # Sin margen ni siquiera bruto → no apto
        if precio_sin_iva <= precio_compra:
            continue

        margen_actual = (precio_sin_iva - precio_compra) / precio_sin_iva

        # Días para vencer (None si no es perecedero)
        fv = p.get("fecha_vencimiento")
        dias_para_vencer: int | None = None
        if fv:
            fv_date = date.fromisoformat(fv) if isinstance(fv, str) else fv
            dias_para_vencer = (fv_date - fecha_referencia).days

        es_perecedero = dias_para_vencer is not None

        # Piso de margen y precio mínimo sin IVA (barrera dura = costo)
        piso = _piso_margen(dias_para_vencer)
        # margen >= piso  →  precio >= costo / (1 - piso)
        precio_min_sin_iva = precio_compra / (1 - piso) if piso < 1 else precio_compra

        # Si el precio de venta ya está por debajo del precio mínimo → sin margen
        if precio_sin_iva <= precio_min_sin_iva:
            continue

        descuento_max_pct = (precio_sin_iva - precio_min_sin_iva) / precio_sin_iva * 100
        precio_flash_sin_iva = precio_min_sin_iva  # máximo descuento aplicado
        precio_flash = _aplicar_iva(precio_flash_sin_iva, incluye_iva, iva_pct)
        margen_tras_descuento = piso  # por construcción es exactamente el piso

        velocidad_venta = (p.get("unidades_vendidas", 0) or 0) / dias_periodo

        # Bonus de prioridad: mayor urgencia de vencimiento = mejor candidato
        if dias_para_vencer is not None:
            if dias_para_vencer <= 7:
                bonus = 3
            elif dias_para_vencer <= 30:
                bonus = 2
            else:
                bonus = 1
        else:
            bonus = 0

        candidatos.append(
            {
                "id_producto": p["id_producto"],
                "nombre": p["nombre"],
                "categoria": p.get("categoria", ""),
                "precio_normal": round(precio_venta, 0),
                "precio_flash": round(precio_flash, 0),
                "descuento_pct": round(descuento_max_pct, 1),
                "margen_actual_pct": round(margen_actual * 100, 1),
                "margen_tras_descuento_pct": round(margen_tras_descuento * 100, 1),
                "stock_actual": stock,
                "es_perecedero": es_perecedero,
                "dias_para_vencer": dias_para_vencer,
                "velocidad_venta": round(velocidad_venta, 2),
                "_bonus": bonus,
            }
        )

    if not candidatos:
        return None

    # Mayor bonus primero; dentro del mismo bonus, el más lento (menor velocidad)
    elegido = max(candidatos, key=lambda c: (c["_bonus"], -c["velocidad_venta"]))

    # Impacto estimado: rango 1.5× – 3× la velocidad diaria normal
    vel = elegido["velocidad_venta"]
    unidades_low = max(1, round(vel * 1.5))
    unidades_high = max(unidades_low + 1, round(vel * 3))
    cop_low = unidades_low * elegido["precio_flash"]
    cop_high = unidades_high * elegido["precio_flash"]
    pf_fmt = _fmt_cop_precio(elegido["precio_flash"])

    impacto_estimado_cop = {
        "rango": f"~{_fmt_cop_abreviado(cop_low)} a {_fmt_cop_abreviado(cop_high)}",
        "supuesto": (
            f"entre {unidades_low} y {unidades_high} unidades vendidas "
            f"ese día a precio flash de {pf_fmt}"
        ),
    }

    return {
        "id_producto": elegido["id_producto"],
        "nombre": elegido["nombre"],
        "categoria": elegido["categoria"],
        "precio_normal": elegido["precio_normal"],
        "precio_flash": elegido["precio_flash"],
        "descuento_pct": elegido["descuento_pct"],
        "margen_tras_descuento": elegido["margen_tras_descuento_pct"],
        "stock_actual": elegido["stock_actual"],
        "es_perecedero": elegido["es_perecedero"],
        "dias_para_vencer": elegido["dias_para_vencer"],
        "velocidad_venta": elegido["velocidad_venta"],
        "impacto_estimado_cop": impacto_estimado_cop,
    }


def calcular_dia_objetivo(
    dia_debil_crudo: list[dict],
    umbral_operativo: int = MIN_TRANSACCIONES_DIA_OPERATIVO,
) -> dict | None:
    """Calcula el día objetivo para la venta flash a partir de los datos crudos.

    Pasos:
    1. Calcula el promedio por ocurrencia de cada día (no la suma bruta).
    2. Descarta días con transacciones_prom < umbral_operativo (días cerrados).
    3. Calcula el promedio general entre los días operativos.
    4. Elige el día con menor transacciones_prom como día objetivo.
    5. Calcula pct_bajo_promedio para explicar la brecha en la sugerencia.

    Args:
        dia_debil_crudo: Resultado de get_dia_debil_crudo (lista de dicts con
            dow, transacciones, monto_total, ocurrencias).
        umbral_operativo: Transacciones promedio mínimas para considerar un día
            operativo. Default: MIN_TRANSACCIONES_DIA_OPERATIVO (3).

    Returns:
        Dict con día objetivo y métricas, o None si no hay datos suficientes.
        Claves: dow, nombre_es, transacciones_promedio_dia, monto_promedio_dia,
        pct_bajo_promedio, promedio_general_transacciones.
    """
    if not dia_debil_crudo:
        return None

    # 1. Calcular promedios por ocurrencia
    dias: list[dict] = []
    for row in dia_debil_crudo:
        ocurrencias = row["ocurrencias"]
        if ocurrencias == 0:
            continue
        dias.append(
            {
                "dow": row["dow"],
                "transacciones_prom": row["transacciones"] / ocurrencias,
                "monto_prom": row["monto_total"] / ocurrencias,
                "ocurrencias": ocurrencias,
            }
        )

    # 2. Excluir días cerrados o atípicos
    dias_operativos = [d for d in dias if d["transacciones_prom"] >= umbral_operativo]
    if not dias_operativos:
        return None

    # 3. Promedio general entre días operativos
    promedio_general = sum(d["transacciones_prom"] for d in dias_operativos) / len(dias_operativos)

    # 4. Día objetivo = menor transacciones_prom entre los operativos
    dia_obj = min(dias_operativos, key=lambda d: d["transacciones_prom"])

    # 5. Porcentaje que está por debajo del promedio general
    pct_bajo = (
        (promedio_general - dia_obj["transacciones_prom"]) / promedio_general * 100
        if promedio_general > 0
        else 0.0
    )

    return {
        "dow": dia_obj["dow"],
        "nombre_es": NOMBRES_DIA_ES.get(dia_obj["dow"], f"día_{dia_obj['dow']}"),
        "transacciones_promedio_dia": round(dia_obj["transacciones_prom"], 1),
        "monto_promedio_dia": round(dia_obj["monto_prom"], 0),
        "pct_bajo_promedio": round(pct_bajo, 1),
        "promedio_general_transacciones": round(promedio_general, 1),
    }


# ─── Bloque de salida para el JSON del ETL ────────────────────────────────


def armar_bloque_ventas_flash(
    dia_objetivo: dict | None,
    candidato: dict | None,
) -> dict | None:
    """Ensambla el bloque final 'ventas_flash' para el JSON del ETL.

    Combina el día objetivo (calcular_dia_objetivo) y el candidato
    (calcular_candidato_flash) en el dict con la estructura exacta del schema.
    Formatea precios como strings colombianos y genera la guía de medición.

    Args:
        dia_objetivo: Resultado de calcular_dia_objetivo.
        candidato: Resultado de calcular_candidato_flash.

    Returns:
        Dict listo para la key ``ventas_flash`` del payload, o None si no hay
        datos suficientes para armar una sugerencia coherente.
    """
    if not dia_objetivo or not candidato:
        return None

    nombre_dia = dia_objetivo["nombre_es"]
    txn_prom = dia_objetivo["transacciones_promedio_dia"]

    como_medir = (
        f"Compara las ventas del {nombre_dia} en las 2 semanas posteriores "
        f"a la promo contra el promedio base de {txn_prom} transacciones por {nombre_dia}. "
        f"Un incremento ≥20% en ese día indica que la venta flash activó el tráfico; "
        f"si no hay cambio, revisar el canal de comunicación o el producto elegido."
    )

    return {
        "dia_objetivo": {
            "nombre_es": nombre_dia,
            "indice_dow": dia_objetivo["dow"],
        },
        "transacciones_promedio_dia": txn_prom,
        "pct_bajo_promedio": dia_objetivo["pct_bajo_promedio"],
        "producto": {
            "id_producto": candidato["id_producto"],
            "nombre": candidato["nombre"],
            "categoria": candidato["categoria"],
            "precio_normal": _fmt_cop_precio(candidato["precio_normal"]),
            "precio_flash": _fmt_cop_precio(candidato["precio_flash"]),
            "descuento_pct": candidato["descuento_pct"],
            "margen_tras_descuento": candidato["margen_tras_descuento"],
            "stock_actual": candidato["stock_actual"],
            "es_perecedero": candidato["es_perecedero"],
            "dias_para_vencer": candidato["dias_para_vencer"],
        },
        "impacto_estimado_cop": candidato["impacto_estimado_cop"],
        "como_medir": como_medir,
    }


async def get_flash_sales_data(
    db: AsyncSession,
    empresa_id: int,
    fecha_desde: date,
    fecha_hasta: date,
) -> dict:
    """Punto de entrada: ejecuta ambas queries y devuelve los datos crudos.

    Args:
        db: Sesión async a la DB del POS (read-only).
        empresa_id: ID de la empresa.
        fecha_desde: Inicio del período (inclusive).
        fecha_hasta: Fin del período (inclusive).

    Returns:
        Dict con ``dia_debil_crudo`` y ``pool_productos_crudo``.
    """
    dia_debil = await get_dia_debil_crudo(db, empresa_id, fecha_desde, fecha_hasta)
    pool = await get_pool_productos_crudo(db, empresa_id, fecha_desde, fecha_hasta)
    return {
        "dia_debil_crudo": dia_debil,
        "pool_productos_crudo": pool,
    }
