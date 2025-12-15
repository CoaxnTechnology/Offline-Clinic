from flask import Flask
from flask_migrate import Migrate
import click
from app.config import Config
from app.extensions.db import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)

    # Import models so Alembic/Flask-Migrate can discover tables
    with app.app_context():
        from app.models import patient, user  # noqa: F401

    register_cli(app)

    return app


def register_cli(app: Flask) -> None:
    """
    Adds small helper CLI commands:
    - flask create-db: create tables using the configured database
    - flask drop-db: drop all tables (use with caution)
    """

    @app.cli.command("create-db")
    def create_db_command():
        """Create database tables if they do not exist."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("drop-db")
    def drop_db_command():
        """Drop all database tables. This is destructive."""
        db.drop_all()
        click.echo("Database tables dropped.")
