"""Etapa 3: foto de inicio de jornada (RF-01 del modelo de diseño).

Solo agrega columnas que aceptan NULL: las jornadas anteriores se conservan
sin foto. Antes de aplicarla en SQL Server, scripts/respaldar_y_migrar.py
hace un respaldo (BACKUP DATABASE).

Revision ID: e3a1f0c2b7d4
Revises: c87399dedb00
Create Date: 2026-11-09 20:35:00
"""
from alembic import op
import sqlalchemy as sa


revision = 'e3a1f0c2b7d4'
down_revision = 'c87399dedb00'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('Jornada', schema=None) as batch_op:
        batch_op.add_column(sa.Column('Foto_Inicio_Ruta', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('Foto_Inicio_Hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('Foto_Inicio_Metadatos', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('Jornada', schema=None) as batch_op:
        batch_op.drop_column('Foto_Inicio_Metadatos')
        batch_op.drop_column('Foto_Inicio_Hash')
        batch_op.drop_column('Foto_Inicio_Ruta')
