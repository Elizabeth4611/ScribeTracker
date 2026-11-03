from flask import Flask

from app.extensions import db, migrate
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "Falta SECRET_KEY en backend/.env. Genera una con: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models  # noqa: F401  (para que Flask-Migrate vea las tablas)

    from app.cli import register_cli
    register_cli(app)

    from app.routes.health import bp as health_bp
    app.register_blueprint(health_bp)

    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.inicio import bp as inicio_bp
    app.register_blueprint(inicio_bp)

    from app.routes import (
        evidencias, parametros, promotor, reportes, rutas, supervision, tiendas, usuarios,
    )
    for modulo in (usuarios, parametros, tiendas, rutas, promotor, evidencias, supervision, reportes):
        app.register_blueprint(modulo.bp)

    @app.errorhandler(413)
    def _demasiado_grande(_e):
        from flask import jsonify
        return jsonify(error="El archivo es demasiado grande (máximo 5 MB por fotografía)."), 413

    return app
