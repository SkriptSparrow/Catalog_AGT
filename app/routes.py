from flask import Blueprint, render_template, redirect, request, session, url_for, flash, jsonify
from flask_login import login_required, current_user
from markupsafe import Markup
from app.models import Subscriber, Blog, Products, CarBrand, CartItem
from flask_mail import Message
from app import db, mail
from datetime import datetime, timezone
import re
import os


main_bp = Blueprint('main', __name__)


@main_bp.app_template_filter('nl2br')
def nl2br_filter(s):
    """
    Converts newlines to <br> HTML tags.

    Args:
        s (str): Input string.

    Returns:
        Markup: String with <br> tags replacing newlines.
    """
    return Markup(s.replace('\n', '<br>\n'))


@main_bp.route('/subscribe', methods=['POST'])
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


@main_bp.route('/copy_link', methods=['POST'])
def copy_link():
    """
    Dummy route to flash a 'link copied' message.
    Useful when JS clipboard copy triggers a POST.

    Returns:
        Response: Redirect to the referring page.
    """
    flash("Ссылка скопирована!", "success")
    return redirect(request.form.get('return_url') or request.referrer or url_for('index'))


@main_bp.route('/')
@main_bp.route('/home')
def index():
    """
    Renders the homepage with recent blog posts and main products.

    Returns:
        str: Rendered HTML of the index page.
    """
    posts = Blog.query.order_by(Blog.date.desc()).limit(3).all()
    main_products = Products.query.filter_by(is_main=True).limit(3).all()
    return render_template('index.html', posts=posts, main_products=main_products)


@main_bp.route('/contacts')
def contacts():
    """
    Renders the contacts page.

    Returns:
        str: Rendered HTML of the contacts page.
    """
    return render_template("contacts.html")


@main_bp.app_errorhandler(404)
def page_not_found(e):
    """
    Custom handler for 404 errors.

    Args:
        e (Exception): The error object.

    Returns:
        tuple: Rendered 404 template and status code.
    """
    return render_template("404.html"), 404



@main_bp.route('/about')
def about():
    """
    Renders the about page.

    Returns:
        str: Rendered HTML of the about page.
    """
    return render_template("about.html")


@main_bp.route('/thank_you')
def thank_you():
    """
    Renders the thank-you page after form submission.

    Returns:
        str: Rendered HTML of the thank-you page.
    """
    return render_template("thank_you.html")


@main_bp.route('/apply', methods=['GET', 'POST'])
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


@main_bp.route('/catalog')
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

    user_cart_items = {
        item.product_id: item
        for item in CartItem.query.filter_by(user_id=current_user.id).all()
    }

    return render_template(
        "catalog.html",
        products=products,
        current_sort_label=current_sort_label,
        types=types,
        categories=categories,
        brands=brands, user_cart_items=user_cart_items
    )


@main_bp.route('/product_card/<int:product_id>')
def product_card(product_id):
    """
    Renders the product detail page.

    Args:
        product_id (int): ID of the product.

    Returns:
        str: Rendered product card page.
    """
    product = Products.query.get_or_404(product_id)
    user_cart_items = {
        item.product_id: item
        for item in CartItem.query.filter_by(user_id=current_user.id).all()
    }
    return render_template('product_card.html', product=product, user_cart_items=user_cart_items)


@main_bp.route("/blog")
def blog():
    """
    Renders the list of blog posts sorted by date descending.

    Returns:
        str: Rendered blog list page.
    """
    blogs = Blog.query.order_by(Blog.date.desc()).all()
    return render_template("blog.html", blogs=blogs)


@main_bp.route("/blog_card/<int:blog_id>")
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


@main_bp.route('/admin-login', methods=['GET', 'POST'])
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


@main_bp.route('/admin-logout')
def admin_logout():
    """
    Logs out the admin user by removing the session flag.

    Returns:
        Response: Redirect to login page.
    """
    session.pop('admin', None)
    return redirect(url_for('admin_login'))


cart_bp = Blueprint('cart', __name__, url_prefix='/cart')

@cart_bp.route('/add', methods=['POST'])
@login_required
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')

    if not product_id:
        return jsonify(success=False, message="Нет product_id"), 400

    product = Products.query.get(product_id)
    if not product:
        return jsonify(success=False, message="Товар не найден"), 404

    # Проверка, есть ли уже такой товар в корзине
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()

    if item:
        item.quantity += 1
    else:
        item = CartItem(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(item)

    print("data from JS:", data)

    db.session.commit()
    return jsonify(success=True, quantity=item.quantity)


@cart_bp.route('/update', methods=['POST'])
@login_required
def update_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity')

    if not product_id or quantity is None:
        return jsonify(success=False, message="Некорректные данные"), 400

    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if not item:
        return jsonify(success=False, message="Товар не найден в корзине"), 404

    if quantity <= 0:
        db.session.delete(item)
    else:
        item.quantity = quantity

    db.session.commit()
    return jsonify(success=True, quantity=quantity)


@cart_bp.route('/remove', methods=['POST'])
@login_required
def remove_from_cart():
    if request.is_json:
        data = request.get_json()
        product_id = data.get('product_id')
    else:
        product_id = request.form.get('product_id')

    if not product_id:
        message = "Некорректный запрос"
        if request.is_json:
            return jsonify({"success": False, "message": message}), 400
        flash(message, "danger")
        return redirect(url_for('prof.profile'))

    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        message = "Товар удалён из корзины"
    else:
        # ✨ Вот тут важный момент:
        message = "Товар уже отсутствует в корзине"

    if request.is_json:
        # Всегда success: True — потому что цель достигнута
        return jsonify({"success": True, "message": message})

    flash(message, "success")
    return redirect(url_for('prof.profile'))

