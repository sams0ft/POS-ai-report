"""Modelos SQLAlchemy — reflejo del esquema system_pos del POS.

Acceso:
- Tablas operacionales: solo lectura (venta, producto, inventario, gasto, etc.)
- Tablas IA: lectura y escritura (reporte_ia, ejecucion_ia, insight_ia, recomendacion_ia)

IMPORTANTE:
- Todas las tablas usan schema="system_pos"
- Los PKs siguen el patrón id_<tabla>, nunca "id" genérico
- fecha_vencimiento e is_perecedero están en inventario, NO en producto
- movimiento_financiero NO existe: usar gasto + movimiento_caja
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
from sqlalchemy.dialects.postgresql import JSONB
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
    tipo_negocio = Column(String(50), nullable=False)
    direccion = Column(String(200))
    telefono = Column(String(20))
    estado = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime)


class Usuario(POSBase):
    __tablename__ = "usuario"
    __table_args__ = {"schema": POS_SCHEMA}

    id_usuario = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100))
    correo = Column(String(150))
    username = Column(String(50), nullable=False)
    # password_hash: nunca incluir en queries de análisis
    rol = Column(String(50), nullable=False)
    estado = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime)


class Cliente(POSBase):
    __tablename__ = "cliente"
    __table_args__ = {"schema": POS_SCHEMA}

    id_cliente = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    tipo_documento = Column(String(20))
    numero_documento = Column(String(30))
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100))
    telefono = Column(String(20))
    correo = Column(String(150))
    direccion = Column(String(200))
    fecha_registro = Column(DateTime, server_default=func.now())
    estado = Column(Boolean, default=True, nullable=False)


class MetodoPago(POSBase):
    __tablename__ = "metodo_pago"
    __table_args__ = {"schema": POS_SCHEMA}

    id_metodo_pago = Column(BigInteger, primary_key=True)
    nombre = Column(String(50), nullable=False)
    descripcion = Column(String(200))
    estado = Column(Boolean, default=True, nullable=False)


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
    color = Column(String(20), default="#64748b")
    icono = Column(String(40), default="circle")
    estado = Column(Boolean, default=True, nullable=False)


class Proveedor(POSBase):
    __tablename__ = "proveedor"
    __table_args__ = {"schema": POS_SCHEMA}

    id_proveedor = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    nit = Column(String(30))
    razon_social = Column(String(150), nullable=False)  # nombre del proveedor
    nombre_contacto = Column(String(100))
    telefono = Column(String(20))
    correo = Column(String(150))
    direccion = Column(String(200))
    estado = Column(Boolean, default=True, nullable=False)
    notas = Column(Text)


class Producto(POSBase):
    """Tabla de productos.

    IMPORTANTE:
    - stock_actual NO está aquí, está en inventario
    - fecha_vencimiento NO está aquí, está en inventario
    - es_perecedero NO existe — detectar via inventario.fecha_vencimiento IS NOT NULL
    - El proveedor principal está en id_proveedor
    """

    __tablename__ = "producto"
    __table_args__ = {"schema": POS_SCHEMA}

    id_producto = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_categoria = Column(BigInteger, nullable=False)
    id_proveedor = Column(BigInteger, nullable=False)
    id_marca = Column(BigInteger, nullable=False)
    codigo_barras = Column(String(50))
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(250))
    precio_compra = Column(Numeric(12, 2), default=0, nullable=False)
    precio_venta = Column(Numeric(12, 2), default=0, nullable=False)
    stock_minimo = Column(Numeric(12, 2), default=0, nullable=False)
    controla_inventario = Column(Boolean, default=True, nullable=False)
    unidad = Column(String(40), default="unidad")
    estado = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime)
    actualizado_en = Column(DateTime(timezone=True))


class Inventario(POSBase):
    """Inventario por producto y sucursal.

    IMPORTANTE:
    - fecha_vencimiento está aquí (no en producto)
    - Para perecederos: WHERE fecha_vencimiento IS NOT NULL
    - Un producto puede tener múltiples registros (uno por sucursal)
    """

    __tablename__ = "inventario"
    __table_args__ = {"schema": POS_SCHEMA}

    id_inventario = Column(BigInteger, primary_key=True)
    id_producto = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    id_empresa = Column(BigInteger, nullable=False)
    stock_actual = Column(Numeric(12, 2), default=0, nullable=False)
    stock_reservado = Column(Numeric(12, 2), default=0, nullable=False)
    ubicacion = Column(String(100))
    fecha_vencimiento = Column(Date)  # null si no es perecedero
    ultima_actualizacion = Column(DateTime)


class MovimientoInventario(POSBase):
    """Movimientos de inventario (antes llamado movimientos_cap)."""

    __tablename__ = "movimiento_inventario"
    __table_args__ = {"schema": POS_SCHEMA}

    id_movimiento = Column(BigInteger, primary_key=True)
    id_producto = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    id_usuario = Column(BigInteger, nullable=False)
    id_empresa = Column(BigInteger, nullable=False)
    tipo_movimiento = Column(String(30), nullable=False)
    cantidad = Column(Numeric(12, 2), nullable=False)
    cantidad_anterior = Column(Numeric(12, 2))
    cantidad_nueva = Column(Numeric(12, 2))
    motivo = Column(String(200))
    referencia = Column(String(100))
    fecha_movimiento = Column(DateTime)
    es_automatico = Column(Boolean, default=False, nullable=False)


class StockNotificationRule(POSBase):
    __tablename__ = "stock_notification_rule"
    __table_args__ = {"schema": POS_SCHEMA}

    id_stock_notification_rule = Column(BigInteger, primary_key=True)
    id_producto = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    min_stock = Column(Numeric(12, 2), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    cooldown_minutes = Column(Integer, default=60)
    last_triggered_at = Column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------------


class Venta(POSBase):
    """Cabecera de venta.

    IMPORTANTE:
    - El monto total es 'total', NO 'monto_total'
    - El método de pago es FK 'id_metodo_pago', no string
    - No tiene campo 'cantidad' ni 'id_producto' directo (están en detalle_venta)
    """

    __tablename__ = "venta"
    __table_args__ = {"schema": POS_SCHEMA}

    id_venta = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    id_cliente = Column(BigInteger)  # nullable — venta sin cliente
    id_usuario = Column(BigInteger, nullable=False)
    id_metodo_pago = Column(BigInteger, nullable=False)
    numero_venta = Column(String(50), nullable=False)
    fecha_venta = Column(DateTime, nullable=False)
    subtotal = Column(Numeric(14, 2), default=0, nullable=False)
    descuento = Column(Numeric(14, 2), default=0, nullable=False)
    impuesto = Column(Numeric(14, 2), default=0, nullable=False)
    total = Column(Numeric(14, 2), default=0, nullable=False)  # NO monto_total
    estado = Column(String(30), default="completada", nullable=False)


class DetalleVenta(POSBase):
    __tablename__ = "detalle_venta"
    __table_args__ = {"schema": POS_SCHEMA}

    id_detalle_venta = Column(BigInteger, primary_key=True)
    id_venta = Column(BigInteger, nullable=False)
    id_producto = Column(BigInteger, nullable=False)
    id_empresa = Column(BigInteger, nullable=False)
    cantidad = Column(Numeric(12, 2), nullable=False)
    precio_unitario = Column(Numeric(12, 2), nullable=False)
    descuento = Column(Numeric(12, 2), default=0, nullable=False)
    subtotal = Column(Numeric(14, 2), nullable=False)


class ComprobanteVenta(POSBase):
    """Antes llamado comprobantes_pago."""

    __tablename__ = "comprobante_venta"
    __table_args__ = {"schema": POS_SCHEMA}

    id_comprobante_venta = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_venta = Column(BigInteger, nullable=False)
    numero_comprobante = Column(String(80), nullable=False)
    tipo_comprobante = Column(String(40), default="venta")
    contenido = Column(JSONB, default={})
    fecha_emision = Column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Compras
# ---------------------------------------------------------------------------


class Compra(POSBase):
    __tablename__ = "compra"
    __table_args__ = {"schema": POS_SCHEMA}

    id_compra = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    id_proveedor = Column(BigInteger, nullable=False)
    id_usuario = Column(BigInteger, nullable=False)
    numero_factura = Column(String(50), nullable=False)
    fecha_compra = Column(DateTime)
    subtotal = Column(Numeric(14, 2), default=0, nullable=False)
    impuesto = Column(Numeric(14, 2), default=0, nullable=False)
    total = Column(Numeric(14, 2), default=0, nullable=False)
    estado = Column(String(30), default="registrada")
    observacion = Column(Text)


class DetalleCompra(POSBase):
    __tablename__ = "detalle_compra"
    __table_args__ = {"schema": POS_SCHEMA}

    id_detalle_compra = Column(BigInteger, primary_key=True)
    id_compra = Column(BigInteger, nullable=False)
    id_producto = Column(BigInteger, nullable=False)
    id_empresa = Column(BigInteger, nullable=False)
    cantidad = Column(Numeric(12, 2), nullable=False)
    costo_unitario = Column(Numeric(12, 2), nullable=False)  # NO precio_unitario
    subtotal = Column(Numeric(14, 2), nullable=False)


# ---------------------------------------------------------------------------
# Financiero
# ---------------------------------------------------------------------------


class CategoriaGasto(POSBase):
    """IMPORTANTE: NO tiene campo 'tipo'."""

    __tablename__ = "categoria_gasto"
    __table_args__ = {"schema": POS_SCHEMA}

    id_categoria_gasto = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(250))
    estado = Column(Boolean, default=True, nullable=False)


class Gasto(POSBase):
    """Egresos del negocio. Reemplaza a movimiento_financiero (que NO existe).

    Para análisis de ingresos vs egresos:
    - Ingresos: venta.total WHERE estado = 'completada'
    - Egresos: gasto.monto WHERE estado = 'registrado'
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
    fecha_gasto = Column(DateTime(timezone=True))
    referencia = Column(String(120))
    estado = Column(String(30), default="registrado")  # 'registrado'|'anulado'


class Caja(POSBase):
    __tablename__ = "caja"
    __table_args__ = {"schema": POS_SCHEMA}

    id_caja = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger, nullable=False)
    nombre = Column(String(100), nullable=False)
    estado = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True))


class SesionCaja(POSBase):
    __tablename__ = "sesion_caja"
    __table_args__ = {"schema": POS_SCHEMA}

    id_sesion_caja = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_caja = Column(BigInteger, nullable=False)
    id_usuario_apertura = Column(BigInteger, nullable=False)
    id_usuario_cierre = Column(BigInteger)  # nullable
    fecha_apertura = Column(DateTime(timezone=True))
    fecha_cierre = Column(DateTime(timezone=True))  # nullable
    monto_apertura = Column(Numeric(14, 2), default=0)
    monto_cierre = Column(Numeric(14, 2))  # nullable
    estado = Column(String(30), default="abierta")  # 'abierta'|'cerrada'|'anulada'
    observacion = Column(Text)


class MovimientoCaja(POSBase):
    """Flujo de caja por sesión. Complementa a gasto para análisis financiero."""

    __tablename__ = "movimiento_caja"
    __table_args__ = {"schema": POS_SCHEMA}

    id_movimiento_caja = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sesion_caja = Column(BigInteger, nullable=False)
    id_usuario = Column(BigInteger, nullable=False)
    tipo_movimiento = Column(String(30), nullable=False)  # ingreso|egreso|ajuste|apertura|cierre
    origen = Column(String(40), default="manual")
    referencia_tipo = Column(String(60))
    referencia_id = Column(BigInteger)
    monto = Column(Numeric(14, 2), nullable=False)
    descripcion = Column(Text)
    fecha_movimiento = Column(DateTime(timezone=True))


class PeriodoFinanciero(POSBase):
    __tablename__ = "periodo_financiero"
    __table_args__ = {"schema": POS_SCHEMA}

    id_periodo_financiero = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    tipo_periodo = Column(String(20), default="mensual")  # semanal|mensual|trimestral|anual
    estado = Column(String(30), default="abierto")  # abierto|cerrado
    fecha_creacion = Column(DateTime(timezone=True))


class ResumenFinanciero(POSBase):
    """Resumen financiero pre-calculado por período."""

    __tablename__ = "resumen_financiero"
    __table_args__ = {"schema": POS_SCHEMA}

    id_resumen_financiero = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_periodo_financiero = Column(BigInteger, nullable=False)
    total_ingresos = Column(Numeric(14, 2), default=0)
    total_egresos = Column(Numeric(14, 2), default=0)
    utilidad_bruta = Column(Numeric(14, 2), default=0)
    impuestos = Column(Numeric(14, 2), default=0)
    utilidad_neta = Column(Numeric(14, 2), default=0)
    datos = Column(JSONB, default={})
    fecha_calculo = Column(DateTime(timezone=True))


class Impuesto(POSBase):
    __tablename__ = "impuesto"
    __table_args__ = {"schema": POS_SCHEMA}

    id_impuesto = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    nombre = Column(String(80), nullable=False)
    tipo = Column(String(40), nullable=False)
    porcentaje = Column(Numeric(7, 4), default=0)
    estado = Column(Boolean, default=True)


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
    total_ventas = Column(Numeric(14, 2), default=0)
    cantidad_ventas = Column(BigInteger, default=0)
    ticket_promedio = Column(Numeric(14, 2), default=0)
    margen_estimado = Column(Numeric(14, 2), default=0)
    rotacion_inventario = Column(Numeric(14, 4), default=0)
    productos_bajo_stock = Column(BigInteger, default=0)
    datos = Column(JSONB, default={})
    fecha_calculo = Column(DateTime(timezone=True))


class MetricaVentaSemanal(POSBase):
    __tablename__ = "metrica_venta_semanal"
    __table_args__ = {"schema": POS_SCHEMA}

    id_metrica_venta_semanal = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger)
    semana_inicio = Column(Date, nullable=False)
    semana_fin = Column(Date, nullable=False)
    total_ventas = Column(Numeric(14, 2), default=0)
    cantidad_ventas = Column(BigInteger, default=0)
    ticket_promedio = Column(Numeric(14, 2), default=0)
    hora_pico = Column(SmallInteger)  # 0-23, null si no hay datos
    dia_pico = Column(SmallInteger)   # 1-7, null si no hay datos
    datos = Column(JSONB, default={})
    fecha_calculo = Column(DateTime(timezone=True))


class MetricaProductoSemanal(POSBase):
    __tablename__ = "metrica_producto_semanal"
    __table_args__ = {"schema": POS_SCHEMA}

    id_metrica_producto_semanal = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    id_producto = Column(BigInteger, nullable=False)
    id_sucursal = Column(BigInteger)
    semana_inicio = Column(Date, nullable=False)
    semana_fin = Column(Date, nullable=False)
    unidades_vendidas = Column(Numeric(14, 2), default=0)
    ingresos = Column(Numeric(14, 2), default=0)
    margen_estimado = Column(Numeric(14, 2), default=0)
    stock_promedio = Column(Numeric(14, 2), default=0)
    dias_sin_rotacion = Column(Integer, default=0)
    clasificacion = Column(String(40))
    fecha_calculo = Column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Tablas IA — lectura y escritura permitida desde este servicio
# ---------------------------------------------------------------------------


class EjecucionIA(POSBase):
    __tablename__ = "ejecucion_ia"
    __table_args__ = {"schema": POS_SCHEMA}

    id_ejecucion_ia = Column(BigInteger, primary_key=True)
    id_empresa = Column(BigInteger, nullable=False)
    tipo_ejecucion = Column(String(40), default="semanal")  # manual|semanal|mensual
    estado = Column(String(30), default="pendiente")  # pendiente|procesando|completada|fallida
    fecha_inicio = Column(DateTime(timezone=True))
    fecha_fin = Column(DateTime(timezone=True))
    parametros = Column(JSONB, default={})
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
    estado = Column(String(30), default="generado")  # generado|publicado|archivado
    contenido = Column(JSONB, default={})
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
    severidad = Column(String(30), default="info")  # info|success|warning|error|critical
    datos = Column(JSONB, default={})
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
    prioridad = Column(String(20), default="media")  # baja|media|alta|critica
    impacto_estimado = Column(Numeric(14, 2))  # nullable
    estado = Column(String(30), default="pendiente")  # pendiente|aceptada|rechazada|aplicada|archivada
    entidad_tipo = Column(String(80))
    entidad_id = Column(BigInteger)
    datos = Column(JSONB, default={})
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_resolucion = Column(DateTime(timezone=True))
