from flask import Flask

from app.extensions import db, migrate
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models  # noqa: F401  (para que Flask-Migrate vea las tablas)

    from app.cli import register_cli
    register_cli(app)

    from app.routes.health import bp as health_bp
    app.register_blueprint(health_bp)

    return app