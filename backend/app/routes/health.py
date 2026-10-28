from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    try:
        row = db.session.execute(
            text(
                "SELECT DB_NAME() AS db, "
                "CAST(SERVERPROPERTY('ProductVersion') AS VARCHAR(50)) AS ver"
            )
        ).one()
        return jsonify(status="ok", database=row.db, sql_server_version=row.ver)
    except Exception as exc:
        # No devolvemos el mensaje completo: puede incluir datos del servidor.
        return jsonify(status="error", detail=type(exc).__name__), 503