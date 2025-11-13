from . import db
from flask_login import UserMixin
from datetime import datetime, timezone
from sqlalchemy import Enum as SqlEnum
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class CarBrand(db.Model):
    """
    Represents a car brand in the database.
    """

    __tablename__ = "car_brands"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    def __str__(self):
        """
        Returns the name of the car brand or a fallback string with the ID.
        """
        return str(self.name or f"Марка #{self.id}")


class Products(db.Model):
    """
    Represents a filter product in the catalog.
    """

    __tablename__ = "product"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    article = db.Column(db.String(10), nullable=False)
    full_marking = db.Column(db.String(100), nullable=False)
    type = db.Column(
        SqlEnum(
            "Спец.техника", "Сельхоз", "Грузовики", "Универсальный", name="product_type"
        ),
        nullable=False,
    )
    category = db.Column(
        SqlEnum(
            "Воздушный",
            "Салонный",
            "Топливный",
            "Масляный",
            "Гидравлический",
            name="product_category",
        ),
        nullable=False,
    )
    brand_id = db.Column(db.Integer, db.ForeignKey("car_brands.id"))
    brand = db.relationship("CarBrand", backref="filters")
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    in_stock = db.Column(db.Boolean, default=False)
    is_main = db.Column(db.Boolean, default=False)
    photo_filename = db.Column(db.String(128))


class Blog(db.Model):
    """
    Represents a blog post-entry.
    """

    __tablename__ = "blog"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False, unique=True)
    subtitle = db.Column(db.String(400), nullable=False)
    text = db.Column(db.String(1000), nullable=False)
    date = db.Column(db.Date, nullable=False)
    autor = db.Column(
        SqlEnum("Константин", "Сергей", name="blog_autor"), nullable=False
    )
    photo_filename = db.Column(db.String(128))


class Subscriber(db.Model):
    """
    Represents a newsletter subscriber.
    """

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    date_subscribed = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)

    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    user_type = db.Column(db.String(20))  # 'Физ.лицо' или 'ИП'
    job_title = db.Column(db.String(40))
    photo_filename = db.Column(db.String(128))
    orders = db.relationship("Order", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="new")
    total_sum = db.Column(db.Numeric(10, 2), default=0)

    # Снэпшот данных пользователя на момент заказа
    full_name = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    company_name = db.Column(db.String(255))
    comment = db.Column(db.Text)

    items = db.relationship(
        "OrderItem", backref="order", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Order {self.order_number or self.id}>"


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)

    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=True)
    product_name = db.Column(db.String(255))
    article = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Numeric(10, 2), default=0)
    sum = db.Column(db.Numeric(10, 2), default=0)

    def __repr__(self):
        return f"<OrderItem {self.product_name} x{self.quantity}>"


def generate_order_number():
    """Генерирует уникальный человекочитаемый номер заказа, например AGT-20251109-0007"""
    date_part = datetime.utcnow().strftime("%Y%m%d")
    last_order = Order.query.order_by(Order.id.desc()).first()
    seq = (last_order.id + 1) if last_order else 1
    return f"AGT-{date_part}-{seq:04d}"


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)

    user = db.relationship("User", backref="cart_items")
    product = db.relationship("Products")


class LoginForm(FlaskForm):
    email = StringField(
        "Email:",
        validators=[
            DataRequired(message="Укажите email"),
            Email(message="Некорректный email"),
        ],
        render_kw={"placeholder": "Введите email"},
    )
    password = PasswordField(
        "Пароль:",
        validators=[
            DataRequired(message="Введите пароль"),
            Length(min=4, max=20, message="Пароль должен быть от 4 до 20 символов"),
        ],
        render_kw={"placeholder": "Введите пароль"},
    )
    remember = BooleanField("Запомнить меня", default=False)
    submit = SubmitField("Войти")


class RegisterForm(FlaskForm):
    email = StringField(
        label="Email:",
        validators=[
            DataRequired(message="Укажите email"),
            Email(message="Некорректный email"),
        ],
        render_kw={"placeholder": "Введите email"},
    )

    password = PasswordField(
        label="Пароль:",
        validators=[
            DataRequired(message="Придумайте пароль"),
            Length(min=4, max=20, message="Пароль должен быть от 4 до 20 символов"),
        ],
        render_kw={"placeholder": "Введите пароль"},
    )

    confirm_password = PasswordField(
        label="Повторите пароль:",
        validators=[
            DataRequired(message="Повторите пароль"),
            EqualTo("password", message="Пароли не совпадают"),
        ],
        render_kw={"placeholder": "Повторите пароль"},
    )

    submit = SubmitField("Зарегистрироваться")
