"""Etapa 3: categorías de foto Entrada y Salida (RF-06 del modelo de diseño).

Reemplaza la restricción CK_Evidencia_Categoria para aceptar las seis
categorías. Las evidencias existentes (4 categorías) siguen siendo válidas.

Revision ID: f4b2c3d5e6a7
Revises: e3a1f0c2b7d4
Create Date: 2026-11-09 20:50:00
"""
from alembic import op


revision = 'f4b2c3d5e6a7'
down_revision = 'e3a1f0c2b7d4'
branch_labels = None
depends_on = None

NUEVA = "Categoria IN ('Entrada', 'Anaquel antes', 'Anaquel después', 'Precios', 'Promociones', 'Salida')"
ANTERIOR = "Categoria IN ('Anaquel antes', 'Anaquel después', 'Precios', 'Promociones')"


def _cambiar(condicion):
    if op.get_bind().dialect.name == "sqlite":
        # SQLite (solo desarrollo) no permite cambiar una restricción CHECK sin
        # recrear la tabla; las pruebas crean el esquema desde el modelo.
        return
    op.drop_constraint('CK_Evidencia_Categoria', 'Evidencia', type_='check')
    op.create_check_constraint('CK_Evidencia_Categoria', 'Evidencia', condicion)


def upgrade():
    _cambiar(NUEVA)


def downgrade():
    _cambiar(ANTERIOR)
