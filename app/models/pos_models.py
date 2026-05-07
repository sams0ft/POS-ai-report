"""Modelos SQLAlchemy — reflejo read-only de las tablas del POS.

Estos modelos NO crean tablas. Son un reflejo para queries type-safe.
La DB del POS ya existe y se conecta en modo read-only.
"""

# TODO: definir modelos SQLAlchemy para las tablas principales del POS
# Usar __table_args__ = {"autoload_with": engine} para reflejo automático
# o definir explícitamente para mejor control de tipos
