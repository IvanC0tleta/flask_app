from flask_login import UserMixin


class UserLogin(UserMixin):
    def fromDB(self, user_id, db):
        self.__user = False
        try:
            self.__user = db.query.get(user_id)
        except:
            print("Пользователь не найден!")
        return self

    def create(self, user):
        self.__user = user
        return self

    def get_id(self):
        return self.__user.id

    def get_name(self):
        return self.__user.name if self.__user else "Без имени"

    def get_email(self):
        return self.__user.email if self.__user else "Без email"

    def get_birth(self):
        return self.__user.birth if self.__user else "Без дня рождения"

    def get_city(self):
        return self.__user.city if self.__user else "Без города"



