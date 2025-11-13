from app import create_app, db
from flask.cli import with_appcontext
from flask_migrate import Migrate, upgrade, migrate as run_migrate, init as run_init
from flask_login import current_user

app = create_app()

with app.app_context():
    db.create_all()

migrate = Migrate(app, db)


@app.cli.command("db_init")
@with_appcontext
def db_init():
    """Инициализирует миграции"""
    run_init()


@app.cli.command("db_migrate")
@with_appcontext
def db_migrate():
    """Создаёт миграцию"""
    run_migrate(message="Auto migration")


@app.cli.command("db_upgrade")
@with_appcontext
def db_upgrade():
    """Применяет миграции"""
    upgrade()


@app.context_processor
def inject_user():
    return dict(current_user=current_user)


if __name__ == "__main__":
    app.run(debug=True)
