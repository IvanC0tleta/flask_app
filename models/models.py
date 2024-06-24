from datetime import date, datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(session_options={"autoflush": False})


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    psw = db.Column(db.String(500), nullable=False)
    birth = db.Column(db.Date, default=date.today())
    city = db.Column(db.String(100))
    shopping_cart = db.relationship('ShoppingCarts', backref='user_cart', cascade='all,delete')
    favorites = db.relationship('Favorites', backref='user_favorite', cascade='all,delete')

    def __repr__(self):
        return f"<users {self.id}>"


class Categories(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    desc = db.Column(db.Text, nullable=False)
    products = db.relationship('Products', backref='category_product', cascade='all,delete')

    def __repr__(self):
        return f"<categories {self.id}>"


class Products(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    desc = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    img = db.Column(db.String(500))
    cat_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'))
    favorites = db.relationship('Favorites', backref='product_favorite', cascade='all,delete')

    def __repr__(self):
        return f"<products {self.id}>"


class Favorites(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'))

    def __repr__(self):
        return f"<favorites {self.id}>"


class Ratings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    rating = db.Column(db.Integer)

    def __repr__(self):
        return f"<ratings {self.id}>"


class ShoppingCarts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    shoppingCartLines = db.relationship('ShoppingCartLines', backref='shopping_cart_scl', cascade='all,delete')

    def __repr__(self):
        return f"<shoppingCarts {self.id}>"


class ShoppingCartLines(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shoppingCart_id = db.Column(db.Integer, db.ForeignKey('shopping_carts.id', ondelete='CASCADE'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    quantity = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<shoppingCartLines {self.id}>"


class Orders(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<orders {self.id}>"


class OrderLines(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    quantity = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<order_lines {self.id}>"