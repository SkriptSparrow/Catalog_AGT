from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask import redirect, session, url_for, current_app
from markupsafe import Markup
from .models import CarBrand, Products, Blog, Subscriber, User, Order
from wtforms.validators import DataRequired
from wtforms.fields import TextAreaField
from wtforms import FileField
from . import db
import uuid
import os


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
admin = Admin(name='AGROTEK', template_mode='bootstrap4', index_view=MyAdminIndexView())


class CarBrandAdmin(ModelView):
    """
    Admin view for managing car brands.
    """
    form_columns = ['name']
    column_default_sort = ('name', False)
    column_sortable_list = ['name']


class ProductsView(ModelView):
    """
    Base admin view for filters with custom form widgets.
    """
    form_overrides = {
        'description': TextAreaField
    }
    form_widget_args = {
        'description': {
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
        'name', 'article', 'full_marking',
        'type', 'category', 'brand', 'price',
        'description', 'in_stock', 'is_main',
        'photo_upload'
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
        'type': 'Тип техники',
        'category': 'Категория фильтра',
        'brand': 'Марка авто',
        'price': 'Цена',
        'description': 'Описание',
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
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(path)

        product = Products(
            name=form.name.data,
            article=form.article.data,
            full_marking=form.full_marking.data,
            type=form.type.data,
            category=form.category.data,
            brand=form.brand.data,
            price=form.price.data,
            description=form.description.data,
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
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
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


class UserAdmin(ModelView):
    column_list = ['id', 'email', 'name', 'phone', 'user_type', 'job_title']
    column_searchable_list = ['email', 'name']
    column_filters = ['user_type']
    form_excluded_columns = ['orders', 'password_hash']


class OrderAdmin(ModelView):
    column_list = ['id', 'user_email', 'created_at', 'status']
    column_filters = ['status', 'created_at']
    column_searchable_list = ['user.email']
    form_columns = ['user', 'status']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email клиента'


# Registering all models in the admin interface
admin.add_view(CarBrandAdmin(CarBrand, db.session, name='Brands'))
admin.add_view(ProductsAdmin(Products, db.session, name='Products'))
admin.add_view(BlogAdmin(Blog, db.session, name='Blog'))
admin.add_view(SubscriberAdmin(Subscriber, db.session))
admin.add_view(UserAdmin(User, db.session, name='User'))
admin.add_view(OrderAdmin(Order, db.session, name='Order'))
