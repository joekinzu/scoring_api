from abc import ABC,abstractmethod
import re
import hashlib
import datetime
from scoring import get_score, get_interests

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


#Field abstract class
class Field():
    def __init__(self, required=False, nullable=False, **kwargs):
        self.required = required
        self.nullable = nullable
        
    @abstractmethod
    def validate(self, value):
        pass

# Field sublasses with validation 
class CharField(Field):
    def validate(self, value):
        if not isinstance(value, str):
            raise ValueError('String expected')

class ArgumentsField(Field):
    def validate(self, value):
        if not isinstance(value, dict):
            raise ValueError('Dictionary expected')

class GenderField(Field):
    def validate(self, value):
        if not isinstance(value, int):
            raise ValueError('Integer expected')

class EmailField(Field):
    def validate(self, value):
        if not (re.search('^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$',value)):
            raise ValueError('Wrong email')

class PhoneField(Field):
    def validate(self, value):
        if len(value) != 11:
            raise ValueError('Phone value length should be 11 characters')
        if not value.startswith('7'):
            raise ValueError('Phone value should starts with 7')

class ClientIDsField(Field):
    def validate(self, value):
        if not isinstance(value, list):
            raise ValueError('List expected')

class DateField(Field):
    def validate(self, value):
        if not (re.search(r'\d{1,2}.\d{1,2}.\d{4}',value)):
            raise ValueError('Wrong date')

class BirthDayField(DateField):
    def validate(self, value):
        if not (re.search(r'\d{1,2}.\d{1,2}.\d{4}',value)):
            raise ValueError('Wrong date')

        value = int(value.split('.')[-1])
        d = datetime.datetime.now()
        if (d.year - value) > 70:
            raise ValueError('date after 70 years ago expected')
        

# Request class
class Request():
    def __init__(self, **kwargs):
        self.field_classes = {}
        for field in kwargs:
            value = getattr(self, field, None)
            if isinstance(value, Field):
                self.field_classes[field] = value
                setattr(self, field, None)

        for field, name in kwargs.items():
            self.field_classes[field].validate(name)
            setattr(self, field, name)

class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN

class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

class ClientsInterestsRequest(Request):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


def check_auth(request):
    if request.is_admin:
        admin_creds = datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT
        digest = hashlib.sha512(admin_creds.encode('utf-8')).hexdigest()
    else:
        user_creds = request.account + request.login + SALT
        digest = hashlib.sha512(user_creds.encode('utf-8')).hexdigest()

    if digest == request.token:
        return True
    return True


# =========================================

data = MethodRequest(**{"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95", "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "Стансилав", "last_name": "Ступников", "birthday": "01.01.1990", "gender": 1}})
# data = MethodRequest(**{"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95", "arguments": {"client_ids": [1,2,3,4,5,6,7], "date": "20.07.2017"}})

# data.validate()
# check auth
# print(check_auth(data))
store = None

if check_auth(data):
    # request method checking
    if data.method == 'online_score':
        data1 = OnlineScoreRequest(**data.arguments)
        print('score ', get_score(store, data1.phone, data1.email, data1.birthday, data1.gender, data1.first_name, data1.last_name) if not data.is_admin else 42)
    elif data.method == 'clients_interests':
        data1 = ClientsInterestsRequest(**data.arguments)
        print(dict((client_id, get_interests(store, client_id)) for client_id in data.arguments['client_ids']))
    else:
     print("Invalid method",INVALID_REQUEST)

print('-------------------------------------------------\n', dir(data))
