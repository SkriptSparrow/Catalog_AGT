from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from dotenv import load_dotenv
from flask_login import LoginManager
from flask_wtf import CSRFProtect
import os
from datetime import timedelta

db = SQLAlchemy()
mail = Mail()

login_manager = LoginManager()

def create_app():
    load_dotenv()

    app = Flask(__name__)
    csrf = CSRFProtect(app)

    # DB config
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Uploads
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

    # Email
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = os.getenv('DEL_EMAIL')
    app.config['MAIL_PASSWORD'] = os.getenv('PASSWORD')

    app.secret_key = os.getenv('SECRET_KEY') or 'verysecret'

    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

    # Инициализация расширений
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # 🔽 Настройка login_manager
    from .models import User  # импортируем здесь, чтобы избежать циклического импорта
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 🔽 Инициализация админки
    from .admin import admin
    admin.init_app(app)

    # 🔽 Регистрация blueprint'ов
    from .routes import main_bp
    from .auth import auth_bp
    from app.profile import prof_bp
    from app.routes import cart_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(prof_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(cart_bp)

    return app
