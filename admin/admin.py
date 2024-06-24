from flask import Blueprint, render_template, url_for, redirect, flash, session, request, g, current_app
from models.models import Users, Categories, Products, Orders, OrderLines, db
import json
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os


admin = Blueprint('admin', __name__, template_folder='templates', static_folder='static')

MAX_CONTENT_LENGTH = 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_admin():
    session['admin_logged'] = 1


def isLogged():
    return True if session.get('admin_logged') else False


def logout_admin():
    session.pop('admin_logged', None)


def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not isLogged():
            return redirect(url_for('.index'))
        return func(*args, **kwargs)

    return decorated_view


@admin.route('/')
def index():
    if not isLogged():
        return redirect(url_for('.login'))

    counts_dict = {'Пользователей': Users.query.count(),
                   'Категорий': Categories.query.count(),
                   'Товаров': Products.query.count()}
    return render_template('admin/index.html', title='Админ-панель', counts_dict=counts_dict)


@admin.route('/login', methods=["POST", "GET"])
def login():
    if isLogged():
        return redirect(url_for('.index'))

    if request.method == "POST":
        if request.form['user'] == "admin" and request.form['psw'] == "12345":
            login_admin()
            return redirect(url_for('.index'))
        else:
            flash("Неверно")

    return render_template('admin/login.html', title='Админ-панель')


@admin.route('/logout', methods=["POST", "GET"])
@admin_required
def logout():
    if not isLogged():
        return redirect(url_for('.login'))

    logout_admin()

    return redirect(url_for('.login'))


@admin.route('/category_create', methods=['POST', 'GET'])
@admin_required
def category_create():
    if request.method == "POST":
        name = request.form['name']
        desc = request.form.to_dict()
        desc.pop('name')
        if len(desc) > 0:
            desc = json.dumps(list(desc.values()), sort_keys=False, ensure_ascii=False)
            category = Categories(name=name, desc=desc)
            try:
                db.session.add(category)
                db.session.commit()
                flash("Категория добалена", category='success')
            except:
                db.session.rollback()
                flash("Ошибка при добавлении категории", category='error')
        else:
            flash("Должна быть хотя бы одна характеристика", category='error')
    return render_template("admin/category_create.html")


@admin.route('/category_update/<int:cat_id>', methods=['POST', 'GET'])
@admin_required
def category_update(cat_id):
    current_cat = Categories.query.get(cat_id)
    if request.method == "POST":
        # корректность данных
        current_cat.name = request.form['name']
        desc = request.form.to_dict()
        desc.pop('name')
        if len(desc) > 0:
            current_cat.desc = json.dumps(list(desc.values()), sort_keys=False, ensure_ascii=False)
            try:
                db.session.commit()
                flash("Категория обновлена", category='success')
                return redirect(url_for('.categories'))
            except:
                db.session.rollback()
                flash("Ошибка при обновлении категории", category='error')
        else:
            flash("Должна быть хотя бы одна характеристика", category='error')
    current_cat.desc = json.loads(current_cat.desc)
    return render_template("admin/category_update.html", cat=current_cat)


@admin.route('/category_delete/<int:cat_id>', methods=['POST', 'GET'])
@admin_required
def category_delete(cat_id):
    current_cat = Categories.query.get(cat_id)
    try:
        db.session.delete(current_cat)
        db.session.commit()
        flash("Категория удалена", category='success')
    except:
        db.session.rollback()
        flash("Категория не может быть удалена", category='error')
    return redirect(url_for('.categories'))


@admin.route('/categories', methods=['POST', 'GET'])
@admin_required
def categories():
    categories = Categories.query.order_by(Categories.id).all()
    for i in range(len(categories)):
        categories[i].desc = json.loads(categories[i].desc)
    return render_template("admin/categories.html", title='Категории', categories=categories)


@admin.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST' and 'photo' in request.files:
        photo = request.files['photo']
        if photo.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo.save(os.path.join('uploads/images/', filename))
            flash('File uploaded successfully')
            return redirect(url_for('admin.upload_file'))
    return render_template('admin/upload.html')


@admin.route('/product_create', methods=['POST', 'GET'])
@admin_required
def product_create():
    if request.method == "POST" and 'img' in request.files:
        # корректность данных
        cat_id = request.form['category']
        title = request.form['title']
        price = request.form['price']
        img = request.files['img']
        if img.filename == '':
            flash('Не выбран файл')
            return redirect(request.url)
        if img and allowed_file(img.filename):
            desc = request.form.to_dict()
            desc.pop('category')
            desc.pop('title')
            desc.pop('price')
            desc = json.dumps(desc, sort_keys=False, ensure_ascii=False)
            product = Products(title=title, price=price, desc=desc, cat_id=cat_id)
            try:
                db.session.add(product)
                db.session.commit()
                filename = current_app.config['UPLOADED_IMAGES_DEST']\
                    + str(product.id) + '.' + secure_filename(img.filename).split(".")[-1]
                img.save(os.path.join('static', filename))
                product.img = filename
                db.session.commit()
                flash("Товар добален", category='success')
            except:
                db.session.rollback()
                flash("Ошибка при добавлении товара", category='error')
    categories = Categories.query.all()
    return render_template("admin/product_create.html", categories=categories)


@admin.route('/product_update/<int:prod_id>', methods=['POST', 'GET'])
@admin_required
def product_update(prod_id):
    if request.method == "POST":
        # корректность данных
        product = Products.query.get(prod_id)
        product.cat_id = request.form['category']
        product.title = request.form['title']
        product.price = request.form['price']
        img = request.files['img']
        desc = request.form.to_dict()
        desc.pop('category')
        desc.pop('title')
        desc.pop('price')
        product.desc = json.dumps(desc, sort_keys=False, ensure_ascii=False)
        if img.filename != "" and allowed_file(img.filename):
            filename = current_app.config['UPLOADED_IMAGES_DEST'] \
                       + str(product.id) + '.' + secure_filename(img.filename).split(".")[-1]
            try:
                if os.path.exists('static/' + product.img):
                    os.remove('static/' + product.img)
                img.save('static/' + filename)
                product.img = filename
            except:
                flash("Ошибка при обновлении фотографии товара", category='error')
                return redirect(url_for('.products'))
        try:
            db.session.commit()
            flash("Товар обновлен", category='success')
            return redirect(url_for('.products'))
        except:
            db.session.rollback()
            flash("Ошибка при обновлении товара", category='error')

    current_product = Products.query.get(prod_id)
    desc = json.loads(current_product.desc)
    categories = Categories.query.all()
    return render_template("admin/product_update.html", product=current_product, categories=categories, desc=desc)


@admin.route('/product_delete/<int:prod_id>', methods=['POST', 'GET'])
@admin_required
def product_delete(prod_id):
    current_prod = Products.query.get(prod_id)
    try:
        db.session.delete(current_prod)
        db.session.commit()
        os.remove(os.path.join('static', current_prod.img))
        flash("Товар удален", category='success')
    except:
        db.session.rollback()
        flash("Ошибка при удалении товара", category='error')
    return redirect(url_for('.products'))


@admin.route('/products', methods=['POST', 'GET'])
@admin_required
def products():
    products = Products.query.all()
    # for i in range(len(products)):
    #     products[i].desc = json.loads(products[i].desc)
    return render_template('admin/products.html', title='Админ-панель', products=products)


@admin.route('/product/<int:prod_id>')
@admin_required
def product(prod_id):
    current_product = Products.query.get(prod_id)
    current_product.desc = json.loads(current_product.desc)
    return render_template("admin/product.html", product=current_product)


@admin.route('/users')
@admin_required
def users():
    users = Users.query.all()
    return render_template("admin/users.html", users=users)


@admin.route('/user_update/<int:user_id>', methods=['POST', 'GET'])
@admin_required
def user_update(user_id):
    user = Users.query.get(user_id)
    if request.method == "POST":
        check_email = []
        if user.email != request.form['email']:
            check_email = Users.query.filter(Users.email == request.form['email']).all()
        if len(check_email) == 0:
            psw = user.psw
            if psw != generate_password_hash(request.form['psw']):
                psw = generate_password_hash(request.form['psw'])
            user.name = request.form['name']
            user.email = request.form['email']
            user.psw = psw
            user.birth = datetime.datetime.strptime(request.form['birth'], "%Y-%m-%d").date()
            user.city = request.form['city']
            try:
                db.session.commit()
                flash("Пользователь обновлен", category='success')
                return redirect(url_for(".users"))
            except:
                db.session.rollback()
                flash("Ошибка при обновлении пользователя", category='error')
        else:
            flash("Пользователь с таким email уже существует", category="error")

    return render_template("admin/user_update.html", user=user)


@admin.route('/user_delete/<int:user_id>', methods=['POST', 'GET'])
@admin_required
def user_delete(user_id):
    user = Users.query.get(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash("Пользователь удален", category='success')
    except:
        db.session.rollback()
        flash("Ошибка при удалении пользователя", category='error')
    return redirect(url_for('.users'))


@admin.route('/get_category_desc', methods=['POST'])
@admin_required
def get_category_desc():
    req = request.json
    cat_id = req.get('cat_id')
    cat = Categories.query.filter(Categories.id == cat_id).all()
    desc = list(json.loads(cat[0].desc))
    return desc
