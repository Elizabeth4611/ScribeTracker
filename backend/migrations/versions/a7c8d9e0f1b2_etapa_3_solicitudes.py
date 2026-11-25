"""Etapa 3: tabla Solicitud_Ajuste (RF-15 del modelo de diseño).

Solo crea una tabla nueva; no modifica datos existentes.

Revision ID: a7c8d9e0f1b2
Revises: f4b2c3d5e6a7
Create Date: 2026-11-09 21:10:00
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7c8d9e0f1b2'
down_revision = 'f4b2c3d5e6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('Solicitud_Ajuste',
        sa.Column('ID_Solicitud', sa.Integer(), nullable=False),
        sa.Column('ID_Promotor', sa.Integer(), nullable=False),
        sa.Column('Fecha', sa.Date(), nullable=False),
        sa.Column('Tipo', sa.String(length=30), nullable=False),
        sa.Column('Motivo', sa.String(length=300), nullable=False),
        sa.Column('ID_Asignacion', sa.Integer(), nullable=True),
        sa.Column('ID_Jornada', sa.Integer(), nullable=True),
        sa.Column('Estado', sa.String(length=20), server_default='Pendiente', nullable=False),
        sa.Column('FechaHora_Solicitud', sa.DateTime(), nullable=False),
        sa.Column('ID_Revisor', sa.Integer(), nullable=True),
        sa.Column('FechaHora_Respuesta', sa.DateTime(), nullable=True),
        sa.Column('Comentario_Respuesta', sa.String(length=300), nullable=True),
        sa.CheckConstraint("Tipo IN ('Tienda no visitada', 'Check-out olvidado', 'Corrección de horario', 'Otro')",
                           name='CK_Solicitud_Tipo'),
        sa.CheckConstraint("Estado IN ('Pendiente', 'Aprobada', 'Rechazada')", name='CK_Solicitud_Estado'),
        sa.ForeignKeyConstraint(['ID_Asignacion'], ['Asignacion.ID_Asignacion']),
        sa.ForeignKeyConstraint(['ID_Jornada'], ['Jornada.ID_Jornada']),
        sa.ForeignKeyConstraint(['ID_Promotor'], ['Usuario.ID_Usuario']),
        sa.ForeignKeyConstraint(['ID_Revisor'], ['Usuario.ID_Usuario']),
        sa.PrimaryKeyConstraint('ID_Solicitud'),
    )
    op.create_index('IX_Solicitud_Promotor_Fecha', 'Solicitud_Ajuste', ['ID_Promotor', 'Fecha'], unique=False)


def downgrade():
    op.drop_index('IX_Solicitud_Promotor_Fecha', table_name='Solicitud_Ajuste')
    op.drop_table('Solicitud_Ajuste')
