from flask import Blueprint
from . import db
from flask import request, redirect, render_template, url_for, flash
from flask_login import login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/user_login', methods=['GET', 'POST'])
def user_login():
    from app.models import User, LoginForm, RegisterForm
    login_form = LoginForm()
    register_form = RegisterForm()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'Войти' and login_form.validate_on_submit():
            email = login_form.email.data
            password = login_form.password.data
            user = User.query.filter_by(email=email).first()

            if not user:
                # Пользователь не найден - предлагаем регистрацию
                flash('Пользователь с таким email не найден. Возможно, вы хотите зарегистрироваться?',
                      category='warning')
            elif not check_password_hash(user.password_hash, password):
                # Пароль неверный - даём подсказку
                flash('Неверный пароль. Проверьте правильность ввода', category='error')
            else:
                # Успешный вход
                login_user(user, remember=login_form.remember.data)
                return redirect(url_for('prof.profile'))

        elif action == 'Зарегистрироваться' and register_form.validate_on_submit():
            email = register_form.email.data
            password = register_form.password.data

            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Пользователь с таким email уже существует', category='error')
            else:
                new_user = User(email=email)
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                flash('Регистрация прошла успешно. Теперь вы можете войти.', category='success')
                return redirect(request.args.get("next") or url_for('prof.profile'))

    return render_template('user_login.html', login_form=login_form, register_form=register_form)


@auth_bp.route('/logout')
def user_logout():
    logout_user()
    flash('Вы вышли из аккаунта.', 'info')
    return redirect(url_for('main.index'))
