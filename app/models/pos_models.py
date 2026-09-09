"""Modelos SQLAlchemy — reflejo del esquema system_pos del POS.

Fuente de verdad: db/POS-AI-scriptdb.sql. Si algo acá no coincide con ese DDL,
manda el DDL.

Acceso:
- Tablas operacionales: solo lectura (venta, producto, gasto, inventario, etc.)
- Tablas IA: lectura y escritura (reporte_ia, ejecucion_ia, insight_ia,
  recomendacion_ia)

CONVENCIONES
- Todas las tablas usan schema="system_pos"
- Los PKs siguen el patrón id_<tabla>, nunca "id" genérico
- El email es `correo`, nunca `email`
- El nombre del proveedor es `razon_social`, nunca `nombre`

MODELO DE INVENTARIO (cambió — leer antes de escribir queries)
La tabla `inventario` YA NO EXISTE. El inventario está partido en tres:
- `saldo_inventario_producto_sucursal_base` → stock por (empresa, producto,
  sucursal), en UNIDAD BASE del producto.
- `lote_inventario_producto`               → lotes; acá vive `fecha_vencimiento`.
- `movimiento_inventario_producto`         → historial; reemplaza a
  `movimiento_inventario`. La cantidad viene firmada (`cantidad_base_firmada`).
Un producto es perecedero si tiene algún lote con `fecha_vencimiento IS NOT NULL`.

MODELO DE UNIDADES (ojo al mezclar)
`producto` define la unidad base (`unidad_base`, `escala_unidad_base`) y
`producto_paquete` las presentaciones vendibles, cada una con su
`unidades_por_item` (factor a unidad base), su `codigo_barras` y sus propios
precios. El stock está en unidad base; `detalle_venta.cantidad` está en items de
la presentación y su factor es `unidades_por_item_usadas`. Para comparar stock
contra ventas hay que llevar ambos a la misma unidad.

OTRAS TRAMPAS
- `producto.codigo_barras` ya no existe → el código de barras vive en
  `producto_paquete.codigo_barras`; en `producto` el identificador es `referencia`.
- `producto.stock_actual` y `producto.fecha_vencimiento` no existen (ver arriba).
- `es_perecedero` no existe.
- `movimiento_financiero` no existe: usar `gasto` (egresos), `ingreso` (ingresos)
  y `movimiento_caja` (flujo de caja).
- `categoria_gasto` SÍ tiene columna `tipo` ('mercancia'|'servicio'|'impuesto'|'otro').
- `detalle_compra` usa `costo_unitario`, no `precio_unitario`.
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase

POS_SCHEMA = "system_pos"


class POSBase(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Tablas de referencia / catálogo
# ---------------------------------------------------------------------------


class Empresa(POSBase):
    __tablename__ = "empresa"
    __table_args__ = {"schema": POS_SCHEMA}

    id_empresa = Column(BigInteger, primary_key=True)
    nombre = Column(String(150), nullable=False)
    nit = Column(String(30))
    correo = Column(String(150))  # campo "correo", NO "email"
    telefono = Column(String(20))
    direccion = Column(String(200))
    sector_economico = Column(String(120))
    estado = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())


class Sucursal(POSBase):
    __tablename__ = "sucursal"
    __table_args__ = {"schema": POS_SCHEMA}

    id_sucursal = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    nombre = Column(String(100), nullable=False)
    direccion = Column(String(200))
    telefono = Column(String(20))
    estado = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime)
    tipo_negocio = Column(String(50), nullable=False)
    ancho_comprobante = Column(SmallInteger, default=80, nullable=False)  # 58 u 80


class Usuario(POSBase):
    """Usuario del POS.

    Las credenciales viven en `usuario_credencial` (password_hash, salt), no acá.
    Nunca leer credenciales en queries de análisis.
    """

    __tablename__ = "usuario"
    __table_args__ = {"schema": POS_SCHEMA}

    id_usuario = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100))
    correo = Column(String(150))
    username = Column(String(50), nullable=False)
    rol = Column(String(50), nullable=False)
    estado = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime)
    token_version = Column(BigInteger, default=0, nullable=False)
    ultimo_cambio_rol = Column(DateTime(timezone=True))
    actualizado_en = Column(DateTime(timezone=True))


class Cliente(POSBase):
    __tablename__ = "cliente"
    __table_args__ = {"schema": POS_SCHEMA}

    id_cliente = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100))
    tipo_documento = Column(String(20))
    numero_documento = Column(String(30))
    correo = Column(String(150))
    telefono = Column(String(20))
    direccion = Column(String(200))
    estado = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    nota = Column(String(200))
    fecha_registro = Column(DateTime, server_default=func.now(), nullable=False)


class MetodoPago(POSBase):
    __tablename__ = "metodo_pago"
    __table_args__ = {"schema": POS_SCHEMA}

    id_metodo_pago = Column(BigInteger, primary_key=True)
    nombre = Column(String(50), nullable=False)
    estado = Column(Boolean, default=True, nullable=False)
    descripcion = Column(String(200))
    afecta_caja = Column(Boolean, default=False, nullable=False)


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------


class Marca(POSBase):
    __tablename__ = "marca"
    __table_args__ = {"schema": POS_SCHEMA}

    id_marca = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(250))
    estado = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime)


class Categoria(POSBase):
    __tablename__ = "categoria"
    __table_args__ = {"schema": POS_SCHEMA}

    id_categoria = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(250))
    estado = Column(Boolean, default=True, nullable=False)
    color = Column(String(20), default="#64748b", nullable=False)
    icono = Column(String(40), default="circle", nullable=False)


class Familia(POSBase):
    """Agrupador de productos por encima de categoría."""

    __tablename__ = "familia"
    __table_args__ = {"schema": POS_SCHEMA}

    id_familia = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    nombre = Column(String(160), nullable=False)
    descripcion = Column(Text)
    estado = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True))


class Proveedor(POSBase):
    __tablename__ = "proveedor"
    __table_args__ = {"schema": POS_SCHEMA}

    id_proveedor = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    razon_social = Column(String(150), nullable=False)  # nombre del proveedor
    nit = Column(String(30))
    nombre_contacto = Column(String(100))
    correo = Column(String(150))
    telefono = Column(String(20))
    direccion = Column(String(200))
    estado = Column(Boolean, default=True, nullable=False)
    notas = Column(Text)


class Producto(POSBase):
    """Producto maestro.

    IMPORTANTE:
    - `codigo_barras` NO está acá: está en producto_paquete. El identificador
      propio del producto es `referencia`.
    - `stock_actual` NO está acá: está en
      saldo_inventario_producto_sucursal_base.stock_base_disponible.
    - `fecha_vencimiento` NO está acá: está en lote_inventario_producto.
    - `es_perecedero` no existe — es perecedero si tiene lotes con vencimiento.
    - Los precios de acá son los del producto base. La presentación vendible
      (producto_paquete) tiene sus propios precios e IVA, que son los que
      realmente se cobran en el mostrador.
    - Para márgenes: el IVA no es utilidad. Si precio_incluye_iva es true hay
      que descontar iva_porcentaje antes de calcular margen.
    """

    __tablename__ = "producto"
    __table_args__ = {"schema": POS_SCHEMA}

    id_producto = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_categoria = Column(BigInteger, nullable=False)
    id_marca = Column(BigInteger, nullable=False)
    id_proveedor = Column(BigInteger)  # nullable
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(250))
    referencia = Column(String(80))  # reemplaza al viejo codigo_barras
    slug = Column(String(80))

    # Precios e impuestos
    precio_compra = Column(Numeric(12, 2), default=0, nullable=False)
    porcentaje_ganancia = Column(Numeric(7, 2), default=0, nullable=False)
    precio_venta = Column(Numeric(12, 2), default=0, nullable=False)
    iva_porcentaje = Column(Numeric(5, 2), default=19)
    retencion_fuente_porcentaje = Column(Numeric(5, 2))
    retencion_iva_porcentaje = Column(Numeric(5, 2))
    precio_incluye_iva = Column(Boolean, default=False, nullable=False)

    # Inventario y unidades
    stock_minimo = Column(Numeric(12, 2), default=0, nullable=False)
    stock_minimo_base = Column(Numeric(18, 6), default=0, nullable=False)
    controla_inventario = Column(Boolean, default=True, nullable=False)
    unidad = Column(String(40), default="unidad", nullable=False)
    unidad_base = Column(String(40), default="unit", nullable=False)
    escala_unidad_base = Column(Integer, default=1, nullable=False)

    estado = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime)
    actualizado_en = Column(DateTime(timezone=True))


class ProductoPaquete(POSBase):
    """Presentación vendible de un producto (la unidad real de mostrador).

    Acá vive el `codigo_barras` y los precios que se cobran. `unidades_por_item`
    es el factor de conversión a la unidad base del producto.
    """

    __tablename__ = "producto_paquete"
    __table_args__ = {"schema": POS_SCHEMA}

    id_producto_paquete = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_producto = Column(BigInteger, nullable=False)
    referencia = Column(String(80), nullable=False)
    nombre = Column(String(120), nullable=False)
    descripcion = Column(Text)
    codigo_barras = Column(String(80), nullable=False)

    unidades_por_paquete = Column(Numeric(12, 2), nullable=False)
    unidades_por_item = Column(Numeric(18, 6), default=1, nullable=False)
    unidad = Column(String(40), default="unidad", nullable=False)
    stock_minimo = Column(Numeric(12, 2), default=0, nullable=False)

    precio_paquete = Column(Numeric(12, 2))
    precio_compra = Column(Numeric(12, 2), default=0, nullable=False)
    porcentaje_ganancia = Column(Numeric(7, 2), default=0, nullable=False)
    precio_venta = Column(Numeric(12, 2), default=0, nullable=False)
    iva_porcentaje = Column(Numeric(5, 2))
    retencion_fuente_porcentaje = Column(Numeric(5, 2))
    retencion_iva_porcentaje = Column(Numeric(5, 2))
    precio_incluye_iva = Column(Boolean, default=False, nullable=False)

    estado = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Inventario — reemplaza a la vieja tabla `inventario`
# ---------------------------------------------------------------------------


class SaldoInventarioProductoSucursalBase(POSBase):
    """Stock actual por producto y sucursal, en UNIDAD BASE.

    Reemplaza a `inventario`. Una fila por (empresa, producto, sucursal), así
    que un join directo contra detalle_venta produce fan-out: agregar primero.
    """

    __tablename__ = "saldo_inventario_producto_sucursal_base"
    __table_args__ = {"schema": POS_SCHEMA}

    id_saldo_inventario_producto_base = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_producto = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    stock_base_disponible = Column(Numeric(18, 6), default=0, nullable=False)
    stock_base_reservado = Column(Numeric(18, 6), default=0, nullable=False)
    version = Column(Integer, default=0, nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True))


class LoteInventarioProducto(POSBase):
    """Lote de inventario. Acá vive `fecha_vencimiento`.

    Un producto es perecedero si tiene lotes con fecha_vencimiento no nula.
    Para el vencimiento más próximo (FEFO) filtrar por estado='activo' y
    cantidad_base_disponible > 0.

    OJO: un lote puede seguir en estado 'activo' con la fecha de vencimiento ya
    pasada — nada lo marca 'vencido' automáticamente.
    """

    __tablename__ = "lote_inventario_producto"
    __table_args__ = {"schema": POS_SCHEMA}

    id_lote_inventario_producto = Column(BigInteger, primary_key=True)
    id_saldo_inventario_producto_base = Column(BigInteger, nullable=False)
    id_empresa = Column(BigInteger, nullable=False)
    id_producto = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    id_producto_paquete_recepcion = Column(BigInteger)
    codigo_lote = Column(String(80), nullable=False)
    fecha_vencimiento = Column(Date)  # null si no es perecedero
    cantidad_base_inicial = Column(Numeric(18, 6), nullable=False)
    cantidad_base_disponible = Column(Numeric(18, 6), nullable=False)
    costo_unitario_base = Column(Numeric(18, 6), default=0, nullable=False)
    # activo | agotado | vencido | bloqueado | anulado
    estado = Column(String(30), default="activo", nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True))


class MovimientoInventarioProducto(POSBase):
    """Historial de movimientos de inventario.

    Reemplaza a `movimiento_inventario`. Diferencias:
    - `cantidad_base_firmada` viene CON SIGNO y en unidad base (no hay
      `cantidad` a secas).
    - `cantidad_anterior`, `cantidad_nueva` y `es_automatico` ya no existen;
      el saldo resultante se consulta en saldo_inventario_producto_sucursal_base.
    """

    __tablename__ = "movimiento_inventario_producto"
    __table_args__ = {"schema": POS_SCHEMA}

    id_movimiento_inventario_producto = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_producto = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    id_usuario = Column(BigInteger)
    id_producto_paquete_presentacion = Column(BigInteger)
    id_lote_inventario_producto = Column(BigInteger)
    # entrada|salida|ajuste|compra|venta|devolucion|anulacion|conversion
    tipo_movimiento = Column(String(40), nullable=False)
    cantidad_base_firmada = Column(Numeric(18, 6), nullable=False)
    unidades_por_item_usadas = Column(Numeric(18, 6), nullable=False)
    referencia_tipo = Column(String(60))
    referencia_id = Column(BigInteger)
    motivo = Column(String(200))
    fecha_movimiento = Column(DateTime(timezone=True), server_default=func.now())
    creado_en = Column(DateTime(timezone=True), server_default=func.now())


class StockNotificationRule(POSBase):
    __tablename__ = "stock_notification_rule"
    __table_args__ = {"schema": POS_SCHEMA}

    id_stock_notification_rule = Column(BigInteger, primary_key=True)
    id_producto = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    min_stock = Column(Numeric(12, 2), nullable=False)
    cooldown_minutes = Column(Integer, default=60, nullable=False)
    last_triggered_at = Column(DateTime(timezone=True))
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------------


class Venta(POSBase):
    """Cabecera de venta.

    IMPORTANTE:
    - El monto total es `total`, NO `monto_total`
    - `fecha_venta` es timestamp SIN zona horaria
    - estado: 'registrada' | 'completada' | 'anulada' | 'cancelada'
    - Para ingresos reales del período: estado = 'completada'
    - Hay ventas a crédito: `condicion_pago`, `estado_pago`, `saldo_pendiente`.
      El `total` se registra al vender aunque no se haya cobrado todavía.
    """

    __tablename__ = "venta"
    __table_args__ = {"schema": POS_SCHEMA}

    id_venta = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    id_cliente = Column(BigInteger)  # nullable — venta sin cliente
    id_usuario = Column(BigInteger, nullable=False)
    id_metodo_pago = Column(BigInteger)  # nullable en ventas a crédito
    id_sesion_caja = Column(BigInteger)
    numero_venta = Column(String(50), nullable=False)
    numero_factura = Column(String(100))
    factura_emitida_en = Column(DateTime(timezone=True))
    fecha_venta = Column(DateTime, nullable=False)  # timestamp sin tz

    subtotal = Column(Numeric(14, 2), default=0, nullable=False)
    descuento = Column(Numeric(14, 2), default=0, nullable=False)
    impuesto = Column(Numeric(14, 2), default=0, nullable=False)
    total = Column(Numeric(14, 2), default=0, nullable=False)  # NO monto_total
    monto_recibido = Column(Numeric(14, 2))

    estado = Column(String(30), default="completada", nullable=False)
    # sin_devolucion | parcial | total
    estado_devolucion = Column(String(30), default="sin_devolucion", nullable=False)
    condicion_pago = Column(String(20), default="contado", nullable=False)  # contado|credito
    estado_pago = Column(String(20), default="pagada", nullable=False)  # pagada|pendiente|abonada
    monto_abonado = Column(Numeric(14, 2), default=0, nullable=False)
    saldo_pendiente = Column(Numeric(14, 2), default=0, nullable=False)
    monto_devuelto_credito = Column(Numeric(14, 2), default=0, nullable=False)

    observacion = Column(Text)
    client_sale_id = Column(UUID(as_uuid=True))
    venta_offline = Column(Boolean, default=False, nullable=False)
    sincronizada_en = Column(DateTime(timezone=True))


class DetalleVenta(POSBase):
    """Línea de venta.

    `cantidad` está en items de la presentación vendida, no en unidad base.
    Para llevarla a unidad base: cantidad * COALESCE(unidades_por_item_usadas, 1).
    """

    __tablename__ = "detalle_venta"
    __table_args__ = {"schema": POS_SCHEMA}

    id_detalle_venta = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_venta = Column(BigInteger, nullable=False)
    id_producto = Column(BigInteger, nullable=False)
    id_paquete_producto = Column(BigInteger)  # presentación vendida (nullable)
    cantidad = Column(Numeric(12, 2), nullable=False)
    precio_unitario = Column(Numeric(12, 2), nullable=False)
    descuento = Column(Numeric(12, 2), default=0, nullable=False)
    subtotal = Column(Numeric(14, 2), nullable=False)
    sku_escaneado = Column(String(160))
    # Snapshot histórico: el nombre del producto al momento de la venta
    nombre_producto_historico = Column(String(120))
    unidad_base_producto_historica = Column(String(40))
    unidades_por_item_usadas = Column(Numeric(18, 6))


class ComprobanteVenta(POSBase):
    __tablename__ = "comprobante_venta"
    __table_args__ = {"schema": POS_SCHEMA}

    id_comprobante_venta = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_venta = Column(BigInteger, nullable=False)
    numero_comprobante = Column(String(80), nullable=False)
    tipo_comprobante = Column(String(40), default="venta", nullable=False)
    contenido = Column(JSONB, default=dict, nullable=False)
    fecha_emision = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Compras
# ---------------------------------------------------------------------------


class Compra(POSBase):
    """Cabecera de compra.

    OJO con el estado: los valores válidos son 'pendiente', 'pagada', 'abonada'
    y 'cancelada'. NO existe 'registrada' — filtrar por ese valor devuelve cero
    filas siempre.
    """

    __tablename__ = "compra"
    __table_args__ = {"schema": POS_SCHEMA}

    id_compra = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    id_proveedor = Column(BigInteger)  # nullable — compra a tercero ocasional
    id_usuario = Column(BigInteger, nullable=False)
    id_sesion_caja = Column(BigInteger)
    numero_factura = Column(String(50))
    fecha_compra = Column(DateTime)  # timestamp sin tz
    subtotal = Column(Numeric(14, 2), default=0, nullable=False)
    impuesto = Column(Numeric(14, 2), default=0, nullable=False)
    total = Column(Numeric(14, 2), default=0, nullable=False)
    # pendiente | pagada | abonada | cancelada
    estado = Column(String(30), default="pendiente", nullable=False)
    observacion = Column(Text)
    # Nombre libre cuando la compra no tiene proveedor registrado
    proveedor_nombre = Column(String(180))
    monto_abonado = Column(Numeric(14, 2), default=0, nullable=False)
    saldo_pendiente = Column(Numeric(14, 2), default=0, nullable=False)
    client_purchase_id = Column(UUID(as_uuid=True))


class DetalleCompra(POSBase):
    """Línea de compra.

    `cantidad` está en unidad base; `cantidad_compra` en la unidad en que se
    compró, y `factor_conversion` las relaciona.
    """

    __tablename__ = "detalle_compra"
    __table_args__ = {"schema": POS_SCHEMA}

    id_detalle_compra = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_compra = Column(BigInteger, nullable=False)
    id_producto = Column(BigInteger, nullable=False)
    id_producto_paquete = Column(BigInteger, nullable=False)
    cantidad = Column(Numeric(12, 2), nullable=False)
    costo_unitario = Column(Numeric(12, 2), nullable=False)  # NO precio_unitario
    subtotal = Column(Numeric(14, 2), nullable=False)
    cantidad_compra = Column(Numeric(14, 3), nullable=False)
    unidad_compra = Column(String(20), nullable=False)
    factor_conversion = Column(Numeric(18, 8), nullable=False)


# ---------------------------------------------------------------------------
# Financiero
# ---------------------------------------------------------------------------


class CategoriaGasto(POSBase):
    """Categoría de gasto.

    SÍ tiene columna `tipo`: 'mercancia' | 'servicio' | 'impuesto' | 'otro'.
    Sirve para separar costo de mercancía de gasto operativo.
    """

    __tablename__ = "categoria_gasto"
    __table_args__ = {"schema": POS_SCHEMA}

    id_categoria_gasto = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(250))
    estado = Column(Boolean, default=True, nullable=False)
    tipo = Column(String(30), default="otro", nullable=False)
    color = Column(String(20), default="#64748b", nullable=False)
    icono = Column(String(80), default="Receipt", nullable=False)
    codigo = Column(String(40))
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True))


class Gasto(POSBase):
    """Egresos del negocio. Reemplaza a movimiento_financiero (que NO existe).

    Para análisis de ingresos vs egresos:
    - Ingresos: venta.total WHERE estado = 'completada' (o la tabla `ingreso`)
    - Egresos:  gasto.monto WHERE estado = 'registrado'

    `iva_monto` está separado del `monto` cuando `iva_incluido` es true.
    """

    __tablename__ = "gasto"
    __table_args__ = {"schema": POS_SCHEMA}

    id_gasto = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger)  # nullable
    id_categoria_gasto = Column(BigInteger, nullable=False)
    id_usuario = Column(BigInteger, nullable=False)
    descripcion = Column(Text, nullable=False)
    monto = Column(Numeric(14, 2), nullable=False)
    fecha_gasto = Column(DateTime(timezone=True), server_default=func.now())
    referencia = Column(String(120))
    estado = Column(String(30), default="registrado", nullable=False)  # registrado|anulado
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True))

    # efectivo | tarjeta | transferencia | credito
    metodo_pago = Column(String(30))
    proveedor_id = Column(BigInteger)
    proveedor_nombre = Column(String(150))
    tercero_nombre = Column(Text)
    tercero_nit = Column(Text)

    iva_incluido = Column(Boolean, default=False, nullable=False)
    iva_monto = Column(Numeric(14, 2), default=0, nullable=False)
    adjuntos = Column(JSONB, default=list, nullable=False)

    id_compra = Column(BigInteger)  # gasto originado por una compra
    id_gasto_recurrente = Column(BigInteger)
    fecha_programada = Column(Date)
    id_movimiento_inventario_producto = Column(BigInteger)


class Ingreso(POSBase):
    """Ingresos del negocio (contraparte de `gasto`).

    origen: 'venta_pos' | 'manual' | 'ajuste' | 'abono_venta'.
    Las ventas del POS generan una fila acá, así que sumar `venta.total` Y
    `ingreso.monto` duplica los ingresos. Elegir una sola fuente.
    """

    __tablename__ = "ingreso"
    __table_args__ = {"schema": POS_SCHEMA}

    id_ingreso = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger)
    id_venta = Column(BigInteger)
    id_usuario = Column(BigInteger, nullable=False)
    id_metodo_pago = Column(BigInteger)
    id_abono_venta = Column(BigInteger)
    descripcion = Column(Text, nullable=False)
    monto = Column(Numeric(14, 2), nullable=False)
    fecha_ingreso = Column(DateTime(timezone=True), server_default=func.now())
    referencia = Column(String(120))
    origen = Column(String(40), default="venta_pos", nullable=False)
    estado = Column(String(30), default="registrado", nullable=False)  # registrado|anulado
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True))


class Caja(POSBase):
    __tablename__ = "caja"
    __table_args__ = {"schema": POS_SCHEMA}

    id_caja = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    nombre = Column(String(100), nullable=False)
    estado = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    default_opening_amount = Column(Numeric(14, 2), default=0, nullable=False)


class SesionCaja(POSBase):
    __tablename__ = "sesion_caja"
    __table_args__ = {"schema": POS_SCHEMA}

    id_sesion_caja = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_caja = Column(BigInteger, nullable=False)
    id_usuario_apertura = Column(BigInteger, nullable=False)
    id_usuario_cierre = Column(BigInteger)  # nullable
    fecha_apertura = Column(DateTime(timezone=True), server_default=func.now())
    fecha_cierre = Column(DateTime(timezone=True))  # nullable
    monto_apertura = Column(Numeric(14, 2), default=0, nullable=False)
    monto_cierre = Column(Numeric(14, 2))  # nullable
    estado = Column(String(30), default="abierta", nullable=False)  # abierta|cerrada|anulada
    observacion = Column(Text)
    actualizado_en = Column(DateTime(timezone=True))


class MovimientoCaja(POSBase):
    """Flujo de caja por sesión. Complementa a gasto/ingreso.

    `monto` es siempre positivo; la dirección la da `sentido` ('entrada' o
    'salida'), no el signo. `afecta_caja` marca si el movimiento realmente
    mueve efectivo (una venta con tarjeta no lo hace).
    """

    __tablename__ = "movimiento_caja"
    __table_args__ = {"schema": POS_SCHEMA}

    id_movimiento_caja = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sesion_caja = Column(BigInteger, nullable=False)
    id_usuario = Column(BigInteger, nullable=False)
    # ingreso|egreso|ajuste|apertura|cierre|traslado
    tipo_movimiento = Column(String(30), nullable=False)
    origen = Column(String(40), default="manual", nullable=False)
    referencia_tipo = Column(String(60))
    referencia_id = Column(BigInteger)
    monto = Column(Numeric(14, 2), nullable=False)  # siempre >= 0
    descripcion = Column(Text)
    fecha_movimiento = Column(DateTime(timezone=True), server_default=func.now())
    sentido = Column(String(10), default="entrada", nullable=False)  # entrada|salida
    metodo_pago = Column(String(30))
    referencia = Column(String(100))
    venta_offline = Column(Boolean, default=False, nullable=False)
    requiere_revision_caja = Column(Boolean, default=False, nullable=False)
    id_abono_venta = Column(BigInteger)
    id_pago_compra = Column(BigInteger)
    afecta_caja = Column(Boolean, default=True, nullable=False)


class PeriodoFinanciero(POSBase):
    __tablename__ = "periodo_financiero"
    __table_args__ = {"schema": POS_SCHEMA}

    id_periodo_financiero = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    tipo_periodo = Column(String(20), default="mensual", nullable=False)
    estado = Column(String(30), default="abierto", nullable=False)  # abierto|cerrado
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())


class ResumenFinanciero(POSBase):
    """Resumen financiero pre-calculado por período.

    Trae el desglose de gastos ya separado por tipo — útil para no recalcular
    ingresos vs egresos desde cero.
    """

    __tablename__ = "resumen_financiero"
    __table_args__ = {"schema": POS_SCHEMA}

    id_resumen_financiero = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_periodo_financiero = Column(BigInteger, nullable=False)
    total_ingresos = Column(Numeric(14, 2), default=0, nullable=False)
    total_egresos = Column(Numeric(14, 2), default=0, nullable=False)
    utilidad_bruta = Column(Numeric(14, 2), default=0, nullable=False)
    utilidad_operativa = Column(Numeric(14, 2), default=0, nullable=False)
    impuestos = Column(Numeric(14, 2), default=0, nullable=False)
    utilidad_neta = Column(Numeric(14, 2), default=0, nullable=False)
    total_gastos_mercancia = Column(Numeric(14, 2), default=0, nullable=False)
    total_gastos_servicios = Column(Numeric(14, 2), default=0, nullable=False)
    total_gastos_impuestos = Column(Numeric(14, 2), default=0, nullable=False)
    total_gastos_otros = Column(Numeric(14, 2), default=0, nullable=False)
    impuestos_registro_neto = Column(Numeric(14, 2), default=0, nullable=False)
    balance = Column(Numeric(14, 2), default=0, nullable=False)
    margen_neto = Column(Numeric(9, 4), default=0, nullable=False)
    # ganancia | perdida | equilibrio
    resultado = Column(String(20), default="equilibrio", nullable=False)
    datos = Column(JSONB, default=dict, nullable=False)
    fecha_calculo = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True))


class Impuesto(POSBase):
    __tablename__ = "impuesto"
    __table_args__ = {"schema": POS_SCHEMA}

    id_impuesto = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    nombre = Column(String(80), nullable=False)
    # iva | retencion_fuente | retencion_iva | otro
    tipo = Column(String(40), nullable=False)
    porcentaje = Column(Numeric(7, 4), default=0, nullable=False)
    estado = Column(Boolean, default=True, nullable=False)
    codigo = Column(String(50))
    descripcion = Column(String(250))
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True))


class RegistroImpuesto(POSBase):
    """Impuestos efectivamente causados, por origen."""

    __tablename__ = "registro_impuesto"
    __table_args__ = {"schema": POS_SCHEMA}

    id_registro_impuesto = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_impuesto = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger)
    origen = Column(String(40), nullable=False)  # venta|compra|gasto|ajuste
    referencia_id = Column(BigInteger, nullable=False)
    base_gravable = Column(Numeric(14, 2), default=0, nullable=False)
    valor_impuesto = Column(Numeric(14, 2), default=0, nullable=False)
    porcentaje = Column(Numeric(7, 4), default=0, nullable=False)
    # debito | credito | retencion
    naturaleza = Column(String(20), default="debito", nullable=False)
    estado = Column(String(30), default="registrado", nullable=False)  # registrado|anulado
    es_automatico = Column(Boolean, default=False, nullable=False)
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)
    creado_por = Column(BigInteger)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Métricas pre-calculadas
# ---------------------------------------------------------------------------


class KpiResumen(POSBase):
    """KPIs pre-calculados por período y sucursal. Usar cuando estén disponibles."""

    __tablename__ = "kpi_resumen"
    __table_args__ = {"schema": POS_SCHEMA}

    id_kpi_resumen = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger)  # null = todas las sucursales
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    total_ventas = Column(Numeric(14, 2), default=0, nullable=False)
    cantidad_ventas = Column(BigInteger, default=0, nullable=False)
    ticket_promedio = Column(Numeric(14, 2), default=0, nullable=False)
    margen_estimado = Column(Numeric(14, 2), default=0, nullable=False)
    rotacion_inventario = Column(Numeric(14, 4), default=0, nullable=False)
    productos_bajo_stock = Column(BigInteger, default=0, nullable=False)
    datos = Column(JSONB, default=dict, nullable=False)
    fecha_calculo = Column(DateTime(timezone=True), server_default=func.now())


class MetricaVentaSemanal(POSBase):
    __tablename__ = "metrica_venta_semanal"
    __table_args__ = {"schema": POS_SCHEMA}

    id_metrica_venta_semanal = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger)
    semana_inicio = Column(Date, nullable=False)
    semana_fin = Column(Date, nullable=False)
    total_ventas = Column(Numeric(14, 2), default=0, nullable=False)
    cantidad_ventas = Column(BigInteger, default=0, nullable=False)
    ticket_promedio = Column(Numeric(14, 2), default=0, nullable=False)
    hora_pico = Column(SmallInteger)  # 0-23, null si no hay datos
    dia_pico = Column(SmallInteger)   # 1-7 acá (OJO: no es el DOW 0=domingo del proyecto)
    datos = Column(JSONB, default=dict, nullable=False)
    fecha_calculo = Column(DateTime(timezone=True), server_default=func.now())


class MetricaProductoSemanal(POSBase):
    __tablename__ = "metrica_producto_semanal"
    __table_args__ = {"schema": POS_SCHEMA}

    id_metrica_producto_semanal = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_producto = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger)
    semana_inicio = Column(Date, nullable=False)
    semana_fin = Column(Date, nullable=False)
    unidades_vendidas = Column(Numeric(14, 2), default=0, nullable=False)
    ingresos = Column(Numeric(14, 2), default=0, nullable=False)
    margen_estimado = Column(Numeric(14, 2), default=0, nullable=False)
    stock_promedio = Column(Numeric(14, 2), default=0, nullable=False)
    dias_sin_rotacion = Column(Integer, default=0, nullable=False)
    clasificacion = Column(String(40))
    fecha_calculo = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Tablas IA — lectura y escritura permitida desde este servicio
#
# Hay DOS generaciones conviviendo en el esquema:
#   1. reporte_ia / insight_ia / recomendacion_ia / ejecucion_ia  (las de siempre)
#   2. ai_reports / ai_report_suggestions                          (nuevas)
# Confirmar con el equipo del POS cuál consume el dashboard antes de escribir.
# ---------------------------------------------------------------------------


class EjecucionIA(POSBase):
    __tablename__ = "ejecucion_ia"
    __table_args__ = {"schema": POS_SCHEMA}

    id_ejecucion_ia = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    tipo_ejecucion = Column(String(40), default="semanal", nullable=False)  # manual|semanal|mensual
    estado = Column(String(30), default="pendiente", nullable=False)
    fecha_inicio = Column(DateTime(timezone=True))
    fecha_fin = Column(DateTime(timezone=True))
    parametros = Column(JSONB, default=dict, nullable=False)
    error = Column(Text)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())


class ReporteIA(POSBase):
    __tablename__ = "reporte_ia"
    __table_args__ = {"schema": POS_SCHEMA}

    id_reporte_ia = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_ejecucion_ia = Column(BigInteger)  # nullable
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    titulo = Column(String(180), nullable=False)
    resumen = Column(Text)
    estado = Column(String(30), default="generado", nullable=False)  # generado|publicado|archivado
    contenido = Column(JSONB, default=dict, nullable=False)
    fecha_generacion = Column(DateTime(timezone=True), server_default=func.now())


class InsightIA(POSBase):
    __tablename__ = "insight_ia"
    __table_args__ = {"schema": POS_SCHEMA}

    id_insight_ia = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_reporte_ia = Column(BigInteger, nullable=False)
    tipo_insight = Column(String(60), nullable=False)
    titulo = Column(String(180), nullable=False)
    descripcion = Column(Text, nullable=False)
    severidad = Column(String(30), default="info", nullable=False)
    datos = Column(JSONB, default=dict, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())


class RecomendacionIA(POSBase):
    __tablename__ = "recomendacion_ia"
    __table_args__ = {"schema": POS_SCHEMA}

    id_recomendacion_ia = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_reporte_ia = Column(BigInteger, nullable=False)
    tipo_recomendacion = Column(String(60), nullable=False)
    titulo = Column(String(180), nullable=False)
    descripcion = Column(Text, nullable=False)
    accion_sugerida = Column(Text, nullable=False)
    prioridad = Column(String(20), default="media", nullable=False)  # baja|media|alta|critica
    impacto_estimado = Column(Numeric(14, 2))  # nullable
    estado = Column(String(30), default="pendiente", nullable=False)
    entidad_tipo = Column(String(80))
    entidad_id = Column(BigInteger)
    datos = Column(JSONB, default=dict, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_resolucion = Column(DateTime(timezone=True))


class AiReport(POSBase):
    """Reporte IA — tabla nueva, en inglés, paralela a `reporte_ia`.

    `source_report_id` es el id externo del servicio que lo generó (este), y es
    único por empresa: sirve como llave de idempotencia.
    """

    __tablename__ = "ai_reports"
    __table_args__ = {"schema": POS_SCHEMA}

    id_ai_report = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    source_report_id = Column(String(120))
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    prompt_version = Column(String(80))
    # pending | processing | completed | failed
    status = Column(String(30), default="completed", nullable=False)
    summary = Column(Text)
    raw_output = Column(JSONB, default=dict, nullable=False)
    parsed_sections = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True))


class AiReportSuggestion(POSBase):
    """Sugerencia de un AiReport. Paralela a `recomendacion_ia`.

    OJO: la prioridad acá va en inglés ('low'|'medium'|'high'|'urgent'), no como
    en recomendacion_ia ('baja'|'media'|'alta'|'critica').
    """

    __tablename__ = "ai_report_suggestions"
    __table_args__ = {"schema": POS_SCHEMA}

    id_ai_report_suggestion = Column(BigInteger, primary_key=True)
    id_ai_report = Column(BigInteger, nullable=False)
    id_empresa = Column(BigInteger, nullable=False)
    type = Column("type", String(80), nullable=False)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=False)
    affected_products = Column(JSONB, default=list, nullable=False)
    priority = Column(String(30), default="medium", nullable=False)
    action_suggested = Column(Text)
    impact_estimate = Column(Text)
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
