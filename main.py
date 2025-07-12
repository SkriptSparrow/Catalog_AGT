from flask import Flask, render_template, redirect, request, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum
from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin, AdminIndexView, expose
from wtforms.validators import DataRequired
from wtforms.fields import TextAreaField
from wtforms import FileField
from datetime import datetime, timezone
from flask_mail import Mail, Message
from markupsafe import Markup
import dotenv
import uuid
import os
import re


# Load environment variables from .env file
dotenv.load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:246800@localhost/agrotek'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = os.getenv('DEL_EMAIL')
app.config['MAIL_PASSWORD'] = os.getenv('PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

# Initialize extensions
mail = Mail(app)
db = SQLAlchemy(app)
app.secret_key = os.getenv("SECRET_KEY") or "verysecret"


def generate_filename(product_id, file_data):
    """
    Generates a unique filename for uploaded product images.

    Args:
        product_id (int or None): The ID of the product, if known.
        file_data (FileStorage): The uploaded file.

    Returns:
        str: A unique filename based on the product ID and a UUID.
    """
    base = f"filter_{product_id}" if product_id else "photo"
    ext = file_data.filename.rsplit('.', 1)[-1]
    return f"{base}_{uuid.uuid4().hex}.{ext}"


class MyAdminIndexView(AdminIndexView):
    """
    Custom admin index view that requires an admin session to access.
    """
    @expose('/')
    def index(self):
        """
        Redirects to login page if not an admin. Otherwise shows the admin index.
        """
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return super().index()

# Initialize Flask-Admin with custom index view
admin = Admin(app, name='AGROTEK', template_mode='bootstrap4', index_view=MyAdminIndexView())


class CarBrand(db.Model):
    """
    Represents a car brand in the database.
    """
    __tablename__ = 'car_brands'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    def __str__(self):
        """
        Returns the name of the car brand or a fallback string with the ID.
        """
        return str(self.name or f"Марка #{self.id}")


class CarBrandAdmin(ModelView):
    """
    Admin view for managing car brands.
    """
    form_columns = ['name']
    column_default_sort = ('name', False)
    column_sortable_list = ['name']


class Products(db.Model):
    """
    Represents a filter product in the catalog.
    """
    __tablename__ = 'product'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    article = db.Column(db.Integer, nullable=False)
    full_marking = db.Column(db.String(100), nullable=False)
    complete_set = db.Column(db.String(100), nullable=False)
    type = db.Column(Enum(
        'Спец.техника', 'Сельхоз', 'Грузовики', 'Универсальный',
        name='product_type'
    ), nullable=False)
    category = db.Column(Enum(
        'Воздушный', 'Салонный', 'Топливный', 'Масляный', 'Гидравлический',
        name='product_category'
    ), nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey('car_brands.id'))
    brand = db.relationship('CarBrand', backref='filters')
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    our_opinion = db.Column(db.String(1000), nullable=False)
    in_stock = db.Column(db.Boolean, default=False)
    is_main = db.Column(db.Boolean, default=False)
    photo_filename = db.Column(db.String(128))


class ProductsView(ModelView):
    """
    Base admin view for filters with custom form widgets.
    """
    form_overrides = {
        'description': TextAreaField,
        'our_opinion': TextAreaField
    }
    form_widget_args = {
        'description': {
            'rows': 8,
            'style': 'resize: vertical;'
        },
        'our_opinion': {
            'rows': 8,
            'style': 'resize: vertical;'
        }
    }


class ProductsAdmin(ProductsView):
    """
    Admin view for managing product entries in the catalog.
    Allows uploading images, filtering, and customizing form display.
    """
    column_list = (
        'id', 'name', 'article', 'type', 'category',
        'brand', 'price', 'in_stock', 'is_main', 'preview'
    )
    form_columns = (
        'name', 'article', 'full_marking', 'complete_set',
        'type', 'category', 'brand', 'price',
        'description', 'our_opinion',
        'in_stock', 'is_main', 'photo_upload'
    )
    column_filters = ('brand', 'type', 'category', 'in_stock', 'is_main')
    form_args = dict(
        brand={
            'label': 'Марка авто',
            'query_factory': lambda: CarBrand.query.order_by(CarBrand.name),
            'get_label': 'name',
            'validators': [DataRequired(message='Пожалуйста, выберите марку автомобиля')]
        }
    )
    form_extra_fields = {
        'photo_upload': FileField('Фотография')
    }
    column_labels = {
        'name': 'Название',
        'article': 'Артикул',
        'full_marking': 'Полная маркировка',
        'complete_set': 'Комплектация',
        'type': 'Тип техники',
        'category': 'Категория фильтра',
        'brand': 'Марка авто',
        'price': 'Цена',
        'description': 'Описание',
        'our_opinion': 'Наше мнение',
        'in_stock': 'В наличии',
        'is_main': 'На главной',
        'preview': 'Фото'
    }

    def create_model(self, form):
        """
        Overrides default create behavior to save uploaded photo and persist the product.

        Args:
            form (Form): The submitted WTForm instance.

        Returns:
            Response: Redirect to the admin list view.
        """
        file = form.photo_upload.data
        filename = None

        if file and file.filename:
            filename = generate_filename(form.brand.data.id if form.brand.data else None, file)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(path)

        product = Products(
            name=form.name.data,
            article=form.article.data,
            full_marking=form.full_marking.data,
            complete_set=form.complete_set.data,
            type=form.type.data,
            category=form.category.data,
            brand=form.brand.data,
            price=form.price.data,
            description=form.description.data,
            our_opinion=form.our_opinion.data,
            is_main=form.is_main.data,
            in_stock=form.in_stock.data,
            photo_filename=filename
        )
        db.session.add(product)
        db.session.commit()
        return redirect(self.get_url('.index_view'))

    def _preview(view, context, model, name):
        """
        Renders a thumbnail preview of the uploaded product image.

        Args:
            view: The current admin view.
            context: The template context.
            model (Products): The product instance.
            name (str): The name of the field.

        Returns:
            Markup: HTML markup for image or empty string.
        """
        if model.photo_filename:
            return Markup(f'<img src="/static/uploads/{model.photo_filename}" style="max-height: 80px;">')
        return ''

    column_formatters = {
        'preview': _preview
    }


class Blog(db.Model):
    """
    Represents a blog post entry.
    """
    __tablename__ = 'blog'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False, unique=True)
    subtitle = db.Column(db.String(400), nullable=False)
    text = db.Column(db.String(1000), nullable=False)
    date = db.Column(db.Date, nullable=False)
    autor = db.Column(Enum('Константин', 'Сергей', name='blog_autor'), nullable=False)
    photo_filename = db.Column(db.String(128))


class BlogAdmin(ModelView):
    """
    Admin view for managing blog posts.
    Allows rich text input and image uploads.
    """
    column_list = ('id', 'title', 'subtitle', 'text', 'date', 'autor', 'preview')
    form_columns = ('title', 'subtitle', 'text', 'date', 'autor', 'photo_upload')
    form_extra_fields = {'photo_upload': FileField('Фотография')}
    column_default_sort = ('date', True)
    column_labels = {
        'title': 'Заголовок',
        'subtitle': 'Подзаголовок',
        'text': 'Текст',
        'date': 'Дата',
        'autor': 'Автор',
    }
    form_overrides = {
        'subtitle': TextAreaField,
        'text': TextAreaField
    }
    form_widget_args = {
        'subtitle': {'rows': 5, 'style': 'resize: vertical;'},
        'text': {'rows': 8, 'style': 'resize: vertical;'}
    }

    def create_model(self, form):
        """
        Saves a new blog post with an optional image.

        Args:
            form (Form): The submitted form.

        Returns:
            Response: Redirect to the blog admin index.
        """
        file = form.photo_upload.data
        filename = None

        if file and file.filename:
            filename = generate_filename(None, file)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(path)

        post = Blog(
            title=form.title.data,
            subtitle=form.subtitle.data,
            text=form.text.data,
            date=form.date.data,
            autor=form.autor.data,
            photo_filename=filename
        )
        db.session.add(post)
        db.session.commit()
        return redirect(self.get_url('.index_view'))

    def _preview(view, context, model, name):
        """
        Renders a thumbnail of the blog post image.

        Args:
            view: The admin view.
            context: The template context.
            model (Blog): The blog post.
            name (str): The field name.

        Returns:
            Markup: HTML with the image or empty string.
        """
        if model.photo_filename:
            return Markup(f'<img src="/static/uploads/{model.photo_filename}" style="max-height: 80px;">')
        return ''

    column_formatters = {
        'preview': _preview
    }


class Subscriber(db.Model):
    """
    Represents a newsletter subscriber.
    """
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    date_subscribed = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)


class SubscriberAdmin(ModelView):
    """
    Admin view for managing newsletter subscribers.
    """
    column_list = ['email', 'date_subscribed', 'is_active']
    column_filters = ['is_active']
    column_searchable_list = ['email']
    can_create = False
    can_edit = True
    can_delete = True


# Registering all models in the admin interface
admin.add_view(CarBrandAdmin(CarBrand, db.session, name='Brands'))
admin.add_view(ProductsAdmin(Products, db.session, name='Products'))
admin.add_view(BlogAdmin(Blog, db.session, name='Blog'))
admin.add_view(SubscriberAdmin(Subscriber, db.session))


@app.template_filter('nl2br')
def nl2br_filter(s):
    """
    Converts newlines to <br> HTML tags.

    Args:
        s (str): Input string.

    Returns:
        Markup: String with <br> tags replacing newlines.
    """
    return Markup(s.replace('\n', '<br>\n'))


@app.route('/subscribe', methods=['POST'])
def subscribe():
    """
    Handles email newsletter subscription via POST request.
    Validates email, prevents duplicates, and stores the subscriber.

    Returns:
        Response: Redirects to the referrer or homepage with a flash message.
    """
    email = request.form.get('email', '').strip().lower()

    # Basic email validation
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        flash("Пожалуйста, введите корректный email.", "error")
        return_url = request.form.get('return_url') or request.referrer or url_for('index') + '#footer'
        return redirect(return_url)

    # Check if already subscribed
    existing = Subscriber.query.filter_by(email=email).first()
    if existing:
        flash("Вы уже подписаны на рассылку.", "info")
        return_url = request.form.get('return_url') or request.referrer or url_for('index') + '#footer'
        return redirect(return_url)

    # Save new subscriber
    new_subscriber = Subscriber(email=email, date_subscribed=datetime.now(timezone.utc))
    db.session.add(new_subscriber)
    db.session.commit()

    flash("Спасибо за подписку!", "success")
    return_url = request.form.get('return_url') or request.referrer or url_for('index') + '#footer'
    return redirect(return_url)


@app.route('/copy_link', methods=['POST'])
def copy_link():
    """
    Dummy route to flash a 'link copied' message.
    Useful when JS clipboard copy triggers a POST.

    Returns:
        Response: Redirect to the referring page.
    """
    flash("Ссылка скопирована!", "success")
    return redirect(request.form.get('return_url') or request.referrer or url_for('index'))


@app.route('/')
@app.route('/home')
def index():
    """
    Renders the homepage with recent blog posts and main products.

    Returns:
        str: Rendered HTML of the index page.
    """
    posts = Blog.query.order_by(Blog.date.desc()).limit(3).all()
    main_products = Products.query.filter_by(is_main=True).limit(3).all()
    return render_template('index.html', posts=posts, main_products=main_products)


@app.route('/contacts')
def contacts():
    """
    Renders the contacts page.

    Returns:
        str: Rendered HTML of the contacts page.
    """
    return render_template("contacts.html")


@app.errorhandler(404)
def page_not_found(e):
    """
    Custom handler for 404 errors.

    Args:
        e (Exception): The error object.

    Returns:
        tuple: Rendered 404 template and status code.
    """
    return render_template("404.html"), 404


@app.route('/about')
def about():
    """
    Renders the about page.

    Returns:
        str: Rendered HTML of the about page.
    """
    return render_template("about.html")


@app.route('/thank_you')
def thank_you():
    """
    Renders the thank-you page after form submission.

    Returns:
        str: Rendered HTML of the thank-you page.
    """
    return render_template("thank_you.html")


@app.route('/apply', methods=['GET', 'POST'])
def apply():
    """
    Handles the catalog request form.

    On POST: Sends a notification email to the business address.
    On GET: Renders the application form.

    Returns:
        Response or str: Redirect to thank-you page or rendered HTML of form.
    """
    if request.method == 'POST':
        name = request.form.get('Name', '')
        telephone = request.form.get('Telephone', '')
        email = request.form.get('Email', '')
        articles = request.form.get('Articles', '')

        msg = Message(
            subject="📥 Новая заявка с сайта",
            sender=os.getenv('DEL_EMAIL'),
            recipients=[os.getenv('REC_EMAIL')],
            body=(
                f"Имя: {name}\n"
                f"Телефон: {telephone}\n"
                f"Email: {email}\n"
                f"Позиции из каталога: {articles}"
            ),
            html=f"""
                <h2>Новая заявка от клиента</h2>
                <ul>
                  <li><strong>Имя:</strong> {name}</li>
                  <li><strong>Телефон:</strong> {telephone}</li>
                  <li><strong>Email:</strong> {email}</li>
                  <li><strong>Позиции из каталога:</strong> {articles}</li>
                </ul>
            """
        )
        mail.send(msg)
        return redirect(url_for("thank_you"))

    return render_template("apply.html")


@app.route('/catalog')
def catalog():
    """
    Renders the product catalog with search, filtering and sorting.

    Query Parameters:
        q (str): Search query.
        sort (str): Sort type ('name_asc', 'name_desc', 'price_asc', 'price_desc').
        type (str): Product type filter.
        category (str): Product category filter.
        brand (str): Brand ID filter.
        price_min (str): Minimum price filter.
        price_max (str): Maximum price filter.

    Returns:
        str: Rendered catalog page with filtered product list.
    """
    query = request.args.get('q', '').strip()
    sort = request.args.get('sort')
    type_filter = request.args.get('type')
    category_filter = request.args.get('category')
    brand_filter = request.args.get('brand')
    price_min = request.args.get('price_min')
    price_max = request.args.get('price_max')
    filters = Products.query

    # Search
    if query:
        filters = filters.filter(
            db.or_(
                Products.name.ilike(f'%{query}%'),
                Products.article.cast(db.String).ilike(f'%{query}%')
            )
        )

    # Filtering
    if type_filter:
        filters = filters.filter(Products.type == type_filter)
    if category_filter:
        filters = filters.filter(Products.category == category_filter)
    if brand_filter:
        filters = filters.filter(Products.brand_id == int(brand_filter))
    if price_min:
        filters = filters.filter(Products.price >= int(price_min))
    if price_max:
        filters = filters.filter(Products.price <= int(price_max))

    # Sorting
    if sort == 'name_asc':
        filters = filters.order_by(Products.name.asc())
    elif sort == 'name_desc':
        filters = filters.order_by(Products.name.desc())
    elif sort == 'price_asc':
        filters = filters.order_by(Products.price.asc())
    elif sort == 'price_desc':
        filters = filters.order_by(Products.price.desc())
    else:
        filters = filters.order_by(Products.name.asc())

    # Получаем данные
    products = filters.all()

    # Sort labels for UI
    sort_labels = {
        'name_asc': 'Имя: А → Я',
        'name_desc': 'Имя: Я → А',
        'price_asc': 'Цена ↑',
        'price_desc': 'Цена ↓',
    }
    current_sort_label = sort_labels.get(sort, 'По умолчанию')

    # Dropdown values (type/category/brand)
    type_query = db.session.query(Products.type).distinct()
    category_query = db.session.query(Products.category).distinct()

    if type_filter:
        category_query = category_query.filter(Products.type == type_filter)
    if category_filter:
        type_query = type_query.filter(Products.category == category_filter)

    types = [row[0] for row in type_query]
    categories = [row[0] for row in category_query]

    brand_query = db.session.query(Products.brand_id)

    if type_filter not in (None, ''):
        brand_query = brand_query.filter(Products.type == type_filter)

    brand_ids = [row[0] for row in brand_query.distinct() if row[0] is not None]

    if brand_ids:
        brands = CarBrand.query.filter(CarBrand.id.in_(brand_ids)).order_by(CarBrand.name).all()
    else:
        brands = []

    return render_template(
        "catalog.html",
        products=products,
        current_sort_label=current_sort_label,
        types=types,
        categories=categories,
        brands=brands
    )


@app.route('/product_card/<int:product_id>')
def product_card(product_id):
    """
    Renders the product detail page.

    Args:
        product_id (int): ID of the product.

    Returns:
        str: Rendered product card page.
    """
    product = Products.query.get_or_404(product_id)
    return render_template('product_card.html', product=product)


@app.route("/blog")
def blog():
    """
    Renders the list of blog posts sorted by date descending.

    Returns:
        str: Rendered blog list page.
    """
    blogs = Blog.query.order_by(Blog.date.desc()).all()
    return render_template("blog.html", blogs=blogs)


@app.route("/blog_card/<int:blog_id>")
def blog_card(blog_id):
    """
    Renders a single blog post page.

    Args:
        blog_id (int): ID of the blog post.

    Returns:
        str: Rendered blog post detail page.
    """
    post = Blog.query.get_or_404(blog_id)
    return render_template("blog_card.html", post=post)


@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """
    Renders the admin login page and validates the password on POST.

    Returns:
        str or Response: Rendered login page or redirect to admin panel.
    """
    error = None
    if request.method == 'POST':
        entered_password = request.form['password']
        if entered_password == os.getenv('ADMIN_PASSWORD'):
            session['admin'] = True
            return redirect('/admin')
        else:
            error = "Incorrect password."
    return render_template('admin_login.html', error=error)


@app.route('/admin-logout')
def admin_logout():
    """
    Logs out the admin user by removing the session flag.

    Returns:
        Response: Redirect to login page.
    """
    session.pop('admin', None)
    return redirect(url_for('admin_login'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
