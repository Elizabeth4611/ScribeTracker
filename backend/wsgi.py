"""Punto de entrada para servidores WSGI de producción (gunicorn en Azure App Service)."""
from app import create_app

app = create_app()
