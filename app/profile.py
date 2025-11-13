from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)
from flask_login import login_required, current_user
from app.models import CartItem
from app import db

prof_bp = Blueprint("prof", __name__)


@prof_bp.route("/profile")
@login_required
def profile():
    user = current_user
    cart_items = CartItem.query.filter_by(user_id=user.id).all()
    return render_template("profile.html", user=user, cart_items=cart_items)


@prof_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def profile_edit():
    if request.method == "POST":
        # Получаем данные из формы
        current_user.name = request.form.get("name")
        current_user.phone = request.form.get("phone")
        current_user.job_title = request.form.get("job_title")
        current_user.user_type = request.form.get("user_type")
        current_user.company_name = request.form.get("company_name")

        photo = request.files.get("photo")

        if photo and photo.filename != "":
            # Проверка расширения (по желанию)
            ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

            def allowed_file(filename):
                return (
                    "." in filename
                    and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
                )

            if allowed_file(photo.filename):
                from werkzeug.utils import secure_filename
                import os

                filename = secure_filename(photo.filename)
                upload_folder = os.path.join(current_app.root_path, "static", "uploads")
                os.makedirs(upload_folder, exist_ok=True)

                filepath = os.path.join(upload_folder, filename)
                photo.save(filepath)

                # Сохраняем имя файла в БД
                current_user.photo_filename = filename
            else:
                flash(
                    "Недопустимый формат файла. Разрешены: png, jpg, jpeg, gif", "error"
                )

        db.session.commit()
        flash("Профиль успешно обновлён", "success")
        return redirect(url_for("prof.profile"))

    return render_template("profile_edit.html", user=current_user)


@prof_bp.route("/orders")
@login_required
def order_list():
    user_orders = (
        current_user.orders
    )  # или Order.query.filter_by(user_id=current_user.id).all()
    return render_template("orders.html", orders=user_orders)
