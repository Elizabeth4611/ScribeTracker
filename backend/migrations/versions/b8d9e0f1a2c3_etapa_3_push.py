"""Etapa 3: tabla Suscripcion_Push (RF-11, notificaciones push).

Revision ID: b8d9e0f1a2c3
Revises: a7c8d9e0f1b2
Create Date: 2026-11-09 22:20:00
"""
from alembic import op
import sqlalchemy as sa


revision = 'b8d9e0f1a2c3'
down_revision = 'a7c8d9e0f1b2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('Suscripcion_Push',
        sa.Column('ID_Suscripcion', sa.Integer(), nullable=False),
        sa.Column('ID_Usuario', sa.Integer(), nullable=False),
        sa.Column('Endpoint', sa.String(length=500), nullable=False),
        sa.Column('Clave_P256dh', sa.String(length=200), nullable=False),
        sa.Column('Clave_Auth', sa.String(length=100), nullable=False),
        sa.Column('Agente', sa.String(length=200), nullable=True),
        sa.Column('Fecha_Alta', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ID_Usuario'], ['Usuario.ID_Usuario']),
        sa.PrimaryKeyConstraint('ID_Suscripcion'),
        sa.UniqueConstraint('Endpoint'),
    )


def downgrade():
    op.drop_table('Suscripcion_Push')
