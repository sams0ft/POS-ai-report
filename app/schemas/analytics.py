"""Schemas para datos analíticos intermedios."""

from datetime import date, datetime

from pydantic import BaseModel


class ProductRanking(BaseModel):
    """Producto con su ranking de ventas."""

    producto_id: int
    nombre: str
    categoria: str
    total_vendido: int
    ingresos: float
    margen_porcentaje: float
    tendencia: str  # "subiendo", "estable", "bajando"


class HoraMagica(BaseModel):
    """Franja horaria con datos de venta."""

    hora: int
    dia_semana: int  # 0=lunes, 6=domingo
    promedio_ventas: float
    total_transacciones: int
    es_pico: bool


class ProductoPerecible(BaseModel):
    """Producto perecedero con riesgo de desperdicio."""

    producto_id: int
    nombre: str
    stock_actual: int
    fecha_vencimiento: date
    dias_restantes: int
    velocidad_venta_diaria: float
    unidades_en_riesgo: int


class SugerenciaPromocion(BaseModel):
    """Sugerencia de promoción generada por análisis."""

    tipo: str  # "combo_afinidad", "estancado_estrella", "proximo_vencer"
    productos: list[dict]
    razon: str
    descuento_sugerido: float | None = None


class ScoreSalud(BaseModel):
    """Indicador compuesto de salud del negocio."""

    score_total: float  # 0-100
    margen_score: float
    rotacion_score: float
    desperdicio_score: float
    tendencia_score: float
    detalles: dict
