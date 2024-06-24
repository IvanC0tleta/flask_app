from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, url_for, request, redirect, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import json
from models.forms import LoginForm, RegisterForm
from models.UserLogin import UserLogin
from models.models import Users, Categories, Products, ShoppingCarts, ShoppingCartLines, Favorites, Ratings, db
from admin.admin import admin
from flask_uploads import UploadSet, IMAGES, configure_uploads
import os
from surprise import Dataset, Reader
from surprise.model_selection import train_test_split
from surprise import SVD, KNNBasic
from surprise.accuracy import rmse
import pandas as pd
import random
from sqlalchemy import func

SECRET_KEY = os.urandom(32)

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop_db?charset=utf8mb4'
app.config['UPLOADED_IMAGES_DEST'] = 'uploads/images/'
app.config['JSON_AS_ASCII'] = False
app.config['SQLALCHEMY_DATABASE_CHARSET'] = 'utf8mb4'
images = UploadSet('images', IMAGES)
configure_uploads(app, images)
app.register_blueprint(admin, url_prefix='/admin')
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Авторизируйтесь для доступа к закрытым страницам"
login_manager.login_message_category = "success"

users_df, favorites_df, ratings_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def initialization_df():
    # Получаем данные из таблицы Users
    users_query = db.session.query(Users)
    users_list = [u.__dict__ for u in users_query]
    global users_df
    users_df = pd.DataFrame(users_list)

    # Получаем данные из таблицы Favorites
    favorites_query = db.session.query(Favorites)
    favorites_list = [f.__dict__ for f in favorites_query]
    global favorites_df
    favorites_df = pd.DataFrame(favorites_list)

    # Получаем данные из таблицы Ratings
    ratings_query = db.session.query(Ratings)
    ratings_list = [r.__dict__ for r in ratings_query]
    global ratings_df
    ratings_df = pd.DataFrame(ratings_list)
    if len(users_df) and len(favorites_df) and len(ratings_df):
        users_df.drop('_sa_instance_state', axis=1, inplace=True)
        favorites_df.drop('_sa_instance_state', axis=1, inplace=True)
        ratings_df.drop('_sa_instance_state', axis=1, inplace=True)


# Функция для обучения модели и оценки ее производительности
def train_and_evaluate(model, train_data, test_data):
    model.fit(train_data)
    predictions = model.test(test_data)
    accuracy = rmse(predictions)
    return accuracy


def get_recommendations_ratings(model, user_id):
    # Получаем список всех товаров
    all_products = ratings_df['product_id'].unique()

    # Формируем список товаров, которые пользователь еще не оценил
    user_products = ratings_df[ratings_df['user_id'] == user_id]['product_id']
    not_rated_products = [product for product in all_products if product not in user_products]

    # Предсказываем рейтинги для всех непросмотренных товаров
    predictions = [model.predict(user_id, product) for product in not_rated_products]

    # Сортируем предсказания по убыванию рейтинга и выводим топ-5 рекомендаций
    top_recommendations = sorted(predictions, key=lambda x: x.est, reverse=True)[:5]

    # Выводим рекомендации
    # print("Рекомендации для пользователя с ID", user_id)
    # for i, recommendation in enumerate(top_recommendations, 1):
    #     print(f"Рекомендация {i}: Товар ID {recommendation.iid}, Предсказанный рейтинг: {recommendation.est}")
    # print()
    return [rec.iid for rec in top_recommendations]


def get_recommendations_favorites(model, user_id):
    all_products = favorites_df['product_id'].unique()

    user_products = favorites_df[favorites_df['user_id'] == user_id]['product_id']
    not_rated_products = [product for product in all_products if product not in user_products]
    predictions = [model.predict(user_id, product) for product in not_rated_products]
    top_recommendations = sorted(predictions, key=lambda x: x.est, reverse=True)[:5]
    return [rec.iid for rec in top_recommendations]


@login_manager.user_loader
def load_user(user_id):
    return UserLogin().fromDB(user_id, Users)


@app.route('/')
@app.route('/home')
def index():
    products = recommenders()
    ratings_dict = get_ratings(products)
    favorites = get_favorites()
    return render_template("index.html", products=products, favorites=favorites, ratings=ratings_dict)


def get_ratings(products):
    ratings_dict = {}
    for product in products:
        ratings = Ratings.query.filter_by(product_id=product.id).all()
        if ratings:
            average_rating = sum([rating.rating for rating in ratings]) / len(ratings)
            ratings_dict[product.id] = [round(average_rating), len(ratings)]
        else:
            ratings_dict[product.id] = [0, 0]
    return ratings_dict


def get_favorites():
    favorites = []
    if current_user.is_authenticated:
        favorites = Products.query.filter(
            (Products.id == Favorites.product_id) & (Favorites.user_id == current_user.get_id())).all()
    return favorites


@app.route('/login_admin')
def login_admin():
    if current_user.is_authenticated:
        logout_user()
    return redirect("/admin")


@app.route('/loguot')
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта", "success")
    return redirect(url_for('login'))


@app.route('/profile/', defaults={'parameter': 'fav'})
@app.route('/profile/<parameter>', methods=['POST', 'GET'])
@login_required
def profile(parameter):
    favorites = get_favorites()
    ratings_query = Ratings.query.filter_by(user_id=current_user.get_id()).all()
    ratings = {}
    for rating in ratings_query:
        ratings[rating.product_id] = rating.rating
    products_rat = Products.query.filter(Products.id.in_(ratings.keys())).all()
    if parameter == 'rat':
        return render_template("profile.html", products=products_rat, favorites=favorites,
                               ratings=ratings)
    else:
        return render_template("profile.html", products=favorites, favorites=favorites,
                               ratings=ratings)


@app.route('/profile_content/<parameter>', methods=['POST', 'GET'])
@login_required
def profile_content(parameter):
    favorites = get_favorites()
    ratings_query = Ratings.query.filter_by(user_id=current_user.get_id()).all()
    ratings = {}
    for rating in ratings_query:
        ratings[rating.product_id] = rating.rating
    products_rat = Products.query.filter(Products.id.in_(ratings.keys())).all()
    if parameter == 'rat':
        return render_template("profile_content.html", products=products_rat, favorites=favorites,
                               ratings=ratings)
    else:
        return render_template("profile_content.html", products=favorites, favorites=favorites,
                               ratings=ratings)


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter(Users.email == form.email.data).first()
        if user and check_password_hash(user.psw, form.psw.data):
            userLogin = UserLogin().create(user)
            rm = form.remember.data
            login_user(userLogin, remember=rm)
            return redirect(request.args.get('next') or url_for('profile'))
        flash("Неверная пара логин/пароль", "error")
    return render_template("login.html", title="Авторизация", form=form)


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        check_email = Users.query.filter(Users.email == form.email.data).all()
        if len(check_email) == 0:
            psw = generate_password_hash(form.psw.data)
            user = Users(name=form.name.data, email=form.email.data, psw=psw, birth=form.birth.data,
                         city=form.city.data)
            try:
                db.session.add(user)
                db.session.commit()
                shop_cart = ShoppingCarts(user_id=user.id)
                db.session.add(shop_cart)
                db.session.commit()
                flash("Вы успешно зарегестрировались", "success")
                return redirect('/login')
            except:
                db.session.rollback()
                flash("При регистрации пользователя произошла ошибка", "error")
        else:
            flash("Пользователь с таким email уже существует", "error")

    return render_template("register.html", title="Регистрация", form=form)


@app.route('/get_category_desc', methods=['POST'])
def get_category_desc():
    cat_id = request.json.get('cat_id')
    cat = Categories.query.filter(Categories.id == cat_id).all()
    desc = list(json.loads(cat[0].desc))
    return desc


@app.route('/product/<int:prod>')
@login_required
def product(prod):
    current_product = Products.query.get(prod)
    current_product.desc = json.loads(current_product.desc)
    ratings = get_ratings(Products.query.all())
    favorites = get_favorites()
    recs = recommenders()
    if current_product in recs:
        recs.remove(current_product)
    return render_template("product.html", current_user=current_user, product=current_product, rec_products=recs,
                           ratings=ratings, favorites=favorites)


@app.route('/search', methods=['POST', 'GET'])
def search():
    products = []
    if request.method == 'POST':
        title = request.form['title']
        if len(title) > 0:
            products = db.session.query(Products).filter(Products.title.ilike(f'%{title}%')).all()
    ratings_dict = get_ratings(products)
    favorites = get_favorites()
    return render_template("search.html", products=products, ratings=ratings_dict, favorites=favorites)


@app.route('/shopping_cart')
@login_required
def shopping_cart():
    res = db.session.query(
        ShoppingCartLines, Products
    ).join(
        Products, ShoppingCartLines.product_id == Products.id
    ).join(
        ShoppingCarts, ShoppingCarts.id == ShoppingCartLines.shoppingCart_id).join(
        Users, Users.id == ShoppingCarts.user_id
    ).filter(
        Users.id == current_user.get_id()
    ).all()

    return render_template("shopping_cart.html", res=res)


@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    if request.method == 'POST':
        product_id = request.form['id']
        shop_cart = ShoppingCarts.query.filter(ShoppingCarts.user_id == current_user.get_id()).first()
        if shop_cart:
            shop_cart_line = ShoppingCartLines.query.filter((ShoppingCartLines.product_id == product_id) &
                                                            (ShoppingCartLines.shoppingCart_id == shop_cart.id)).first()
            if shop_cart_line:
                try:
                    shop_cart_line.quantity += 1
                    db.session.commit()
                    response = {'status': 'success', 'message': 'Товар добавлен', 'quantity': shop_cart_line.quantity}
                except:
                    db.session.rollback()
                    flash("Ошибка при добавлении товара в корзину", "error")
                    response = {'status': 'error', 'message': 'Ошибка добавления товара'}
            else:
                shop_cart_line = ShoppingCartLines(shoppingCart_id=shop_cart.id, product_id=product_id, quantity=1)
                try:
                    db.session.add(shop_cart_line)
                    db.session.commit()
                    response = {'status': 'success', 'message': 'Товар добавлен', 'quantity': 1}
                except:
                    db.session.rollback()
                    flash("Ошибка при добавлении товара в корзину", "error")
                    response = {'status': 'error', 'message': 'Ошибка добавления товара'}
        else:
            response = {'status': 'error', 'message': 'Ошибка корзины'}
        response['items_cart'] = get_cart_count()['message']
        return response


@app.route('/set_quantity', methods=['POST'])
@login_required
def set_quantity():
    response = {'status': 'error', 'message': 'None'}
    if request.method == 'POST':
        product_id = request.form['id']
        quantity = request.form['quantity']
        shop_cart = ShoppingCarts.query.filter(ShoppingCarts.user_id == current_user.get_id()).first()
        if shop_cart:
            shop_cart_line = ShoppingCartLines.query.filter((ShoppingCartLines.product_id == product_id) &
                                                            (ShoppingCartLines.shoppingCart_id == shop_cart.id)).first()
            if shop_cart_line:
                try:
                    shop_cart_line.quantity = quantity
                    db.session.commit()
                    response = {'status': 'success', 'message': 'Количество обновлено', 'quantity': shop_cart_line.quantity}
                except:
                    db.session.rollback()
                    flash("Ошибка при добавлении товара в корзину", "error")
                    response = {'status': 'error', 'message': 'Ошибка обновления количества товара'}
            else:
                shop_cart_line = ShoppingCartLines(shoppingCart_id=shop_cart.id, product_id=product_id,
                                                   quantity=quantity)
                try:
                    db.session.add(shop_cart_line)
                    db.session.commit()
                    response = {'status': 'success', 'message': 'Товар добавлен', 'quantity': quantity}
                except:
                    db.session.rollback()
                    flash("Ошибка при добавлении товара в корзину", "error")
                    response = {'status': 'error', 'message': 'Ошибка добавления товара'}
        return response


@app.route('/delete_product_from_cart', methods=['POST'])
@login_required
def delete_product_from_cart():
    if request.method == 'POST':
        shop_cart = ShoppingCarts.query.filter(ShoppingCarts.user_id == current_user.get_id()).first()
        scl = ShoppingCartLines.query.filter((ShoppingCartLines.product_id == request.form['id']) &
                                             (ShoppingCartLines.shoppingCart_id == shop_cart.id)).first()
        try:
            db.session.delete(scl)
            db.session.commit()
            response = {'status': 'success'}
        except:
            flash("Ошибка при удалении товара", category='error')
            response = {'status': 'error'}
        return response


@app.route('/add_fav', methods=['POST', 'GET'])
@login_required
def add_fav():
    if request.method == 'POST':
        prod_id = request.form['product_id']
        if Products.query.get(prod_id):
            fav = Favorites.query.filter((Favorites.product_id == prod_id) &
                                         (Favorites.user_id == current_user.get_id())).first()
            try:
                if fav:
                    db.session.delete(fav)
                    response = {'status': 'success', 'message': 'Товар добавлен в избранное', 'fav': False}
                else:
                    db.session.add(Favorites(user_id=current_user.get_id(), product_id=prod_id))
                    response = {'status': 'success', 'message': 'Товар добавлен в избранное', 'fav': True}
                db.session.commit()
            except:
                response = {'status': 'error', 'message': 'Ошибка добавления в избранное'}
        else:
            response = {'status': 'error', 'message': 'Товар не найден'}
        return response


@app.route('/send_star', methods=['POST'])
def send_star():
    if request.method == "POST":
        if current_user.is_authenticated:
            rating = request.form['rating']
            product_id = request.form['productId']
            existing_rating = Ratings.query.filter(
                (Ratings.product_id == product_id) & (Ratings.user_id == current_user.get_id())).first()
            if existing_rating:
                existing_rating.rating = rating
                db.session.commit()
            else:
                new_rating = Ratings(user_id=current_user.get_id(), product_id=product_id, rating=rating)
                db.session.add(new_rating)
            try:
                db.session.commit()
                response = {'status': 'success', 'message': 'Rating submitted successfuly'}
            except:
                flash("Ошибка при оценке товара", category='error')
                response = {'status': 'error', 'message': 'Error DB'}
            return response
    return {'status': 'error', 'message': 'You are not POST'}


@app.route('/clear_cart')
@login_required
def clear_cart():
    user_id = current_user.get_id()
    cart = ShoppingCarts.query.filter(ShoppingCarts.user_id == user_id).first()
    if cart:
        try:
            lines = ShoppingCartLines.query.filter_by(shoppingCart_id=cart.id).all()
            for line in lines:
                db.session.delete(line)
                db.session.commit()
        except:
            db.session.rollback()
            flash("Ошибка при очистке корзины", category="error")
    else:
        flash("Ошибка при очистке корзины", category="error")
    return redirect(url_for('shopping_cart'))


@app.route('/get_cart_count', methods=['POST'])
def get_cart_count():
    lines_count = 0
    if current_user.is_authenticated:
        user_id = current_user.get_id()
        cart = ShoppingCarts.query.filter(ShoppingCarts.user_id == user_id).first()
        if cart:
            lines = ShoppingCartLines.query.filter_by(shoppingCart_id=cart.id).all()
            for line in lines:
                lines_count += line.quantity
    return {'status': 'success', 'message': lines_count}


@app.route('/get_categories', methods=['POST'])
def get_categories():
    categories_query = Categories.query.all()
    categories_dict = {}
    for cat in categories_query:
        categories_dict[cat.id] = cat.name
    return categories_dict


@app.route('/products/<parameter>', methods=['GET'])
def products(parameter):
    products_query = []
    title = "Товары"
    if parameter == 'all':
        products_query = Products.query.all()
        title = "Все товары"
    elif parameter == 'popular':
        fav_products = db.session.query(
            Products, func.count(Favorites.user_id).label('total_users')
        ).join(
            Favorites, Products.id == Favorites.product_id
        ).group_by(
            Products.id
        ).order_by(
            func.count(Favorites.user_id).desc()
        ).all()

        # Извлечение только товаров из результата запроса
        products_query = [product[0] for product in fav_products]
        # products_query = Products.query.filter(Products.id.in_([fav[0] for fav in db.session.query(Favorites.product_id).all()])).all()
        title = "Популярные"
    elif parameter != '':
        products_query = Products.query.filter_by(cat_id=parameter).all()
        title = "Категория: " + Categories.query.get(parameter).name
    ratings = get_ratings(products_query)
    favorites = get_favorites()
    return render_template("products.html", parameter=parameter, products=products_query, ratings=ratings,
                           favorites=favorites, title=title)


@app.route('/recommenders')
def recommenders():
    initialization_df()
    if not (len(users_df) or len(favorites_df) or len(ratings_df)):
        return []
    # Определяем оценочный диапазон для библиотеки Surprise
    reader = Reader(rating_scale=(1, 5))

    # Создаем объекты данных из DataFrame
    favorites_df['rating'] = 5
    favorites_data = Dataset.load_from_df(favorites_df[['user_id', 'product_id', 'rating']], reader)

    ratings_data = Dataset.load_from_df(ratings_df[['user_id', 'product_id', 'rating']], reader)

    # Разбиваем данные на обучающий и тестовый наборы
    favorites_train, favorites_test = train_test_split(favorites_data, test_size=0.2)
    ratings_train, ratings_test = train_test_split(ratings_data, test_size=0.2)

    # Рекомендательные системы на основе таблицы Favorites
    # Модель SVD
    svd_model = SVD()
    svd_accuracy = train_and_evaluate(svd_model, favorites_train, favorites_test)
    # print("RMSE для рекомендательной системы на основе Favorites (SVD):", svd_accuracy)

    # Модель KNN
    knn_model = KNNBasic()
    knn_accuracy = train_and_evaluate(knn_model, favorites_train, favorites_test)
    # print("RMSE для рекомендательной системы на основе Favorites (KNN):", knn_accuracy)

    # Рекомендательные системы на основе таблицы Ratings
    # Модель SVD
    svd_model2 = SVD()
    svd_accuracy = train_and_evaluate(svd_model2, ratings_train, ratings_test)
    # print("RMSE для рекомендательной системы на основе Ratings (SVD):", svd_accuracy)

    # Модель KNN
    knn_model2 = KNNBasic()
    knn_accuracy = train_and_evaluate(knn_model2, ratings_train, ratings_test)
    # print("RMSE для рекомендательной системы на основе Ratings (KNN):", knn_accuracy)
    user_id = current_user.get_id()
    # print("Рекомендации для модели SVD на основе Favorites:")
    recommendations = []
    recommendations += get_recommendations_favorites(svd_model, user_id)

    # print("\nРекомендации для модели KNN на основе Favorites:")
    recommendations += get_recommendations_favorites(knn_model, user_id)

    # print("\nРекомендации для модели SVD на основе Ratings:")
    recommendations += get_recommendations_ratings(svd_model2, user_id)

    # print("\nРекомендации для модели KNN на основе Ratings:")
    recommendations += get_recommendations_ratings(knn_model2, user_id)
    recommendations = [int(rec) for rec in list(set(recommendations))]
    recommendations_products = db.session.query(Products).filter(Products.id.in_(recommendations)).all()
    random.shuffle(recommendations_products)
    return recommendations_products


@app.errorhandler(Exception)
def handle_exception(err):
    return render_template('page404.html', title="Страница не найдена", error=err)


if __name__ == "__main__":
    app.run(debug=True)
