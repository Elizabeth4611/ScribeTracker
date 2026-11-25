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
    if app.config.get("DB_REINTENTAR_DESPERTAR"):
        from app.servicios import despertar_bd
        with app.app_context():
            despertar_bd.activar(db.engine)
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
        evidencias, notificaciones, parametros, promotor, reportes, rutas, solicitudes, supervision, tiendas, usuarios,
    )
    for modulo in (usuarios, parametros, tiendas, rutas, promotor, evidencias, supervision, reportes, solicitudes,
                   notificaciones):
        app.register_blueprint(modulo.bp)

    from app.servicios import push
    push.iniciar(app)

    from sqlalchemy.exc import DBAPIError, OperationalError

    @app.errorhandler(OperationalError)
    @app.errorhandler(DBAPIError)
    def _sin_base_de_datos(_e):
        app.logger.warning("Base de datos no disponible: %s", str(_e).splitlines()[0][:300])
        # Corrección F12: si SQL Server no responde, antes salía una página HTML
        # en inglés ("500 Internal Server Error"). Ahora es JSON en español con
        # 503: la app lo muestra y la cola del teléfono reintenta después.
        from flask import jsonify
        from app.extensions import db as _db
        _db.session.rollback()
        return jsonify(error="El servidor no puede conectarse a la base de datos en este momento. "
                             "Si estás en tienda, tus registros se guardan en el teléfono y se enviarán después."), 503

    @app.errorhandler(500)
    def _error_interno(_e):
        from flask import jsonify
        return jsonify(error="Ocurrió un error en el servidor. Inténtalo de nuevo en unos minutos."), 500

    # Etapa 3 · prueba beta: si FRONTEND_DIST apunta al build de Angular, Flask
    # sirve también la aplicación (un solo puerto, para publicarla con un túnel HTTPS).
    if app.config.get("FRONTEND_DIST"):
        import os as _os
        from flask import send_from_directory
        dist = _os.path.abspath(app.config["FRONTEND_DIST"])

        @app.get("/", defaults={"ruta": ""})
        @app.get("/<path:ruta>")
        def _spa(ruta):
            from flask import jsonify
            if ruta.startswith("api/"):
                return jsonify(error="No encontrado."), 404
            if ruta and _os.path.isfile(_os.path.join(dist, ruta)):
                resp = send_from_directory(dist, ruta)
                if ruta == "sw-push.js":
                    resp.headers["Cache-Control"] = "no-cache"
                return resp
            resp = send_from_directory(dist, "index.html")
            resp.headers["Cache-Control"] = "no-cache"
            return resp

    @app.errorhandler(413)
    def _demasiado_grande(_e):
        from flask import jsonify
        return jsonify(error="El archivo es demasiado grande (máximo 5 MB por fotografía)."), 413

    return app
