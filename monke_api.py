#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC,abstractmethod
import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler
import re
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
        if self.required and not value:
            raise ValueError('Value required')
        if not self.nullable and not bool(value):
            raise ValueError('Value is empty')

# Field sublasses with validation 
class CharField(Field):
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, str):
            raise ValueError('String expected')

class ArgumentsField(Field):
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, dict):
            raise ValueError('Dictionary expected')

class GenderField(Field):
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, int):
            raise ValueError('Integer expected')
        if value not in [0,1,2]:
            raise ValueError('Wrong gender value')

class EmailField(CharField):
    def validate(self, value):
        super().validate(value)
        if not (re.search('^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$',value)):
            raise ValueError('Wrong email')

class PhoneField(Field):
    def validate(self, value):
        super().validate(value)
        if len(value) != 11:
            raise ValueError('Phone should contain 11 digits')
        if not value.startswith('7'):
            raise ValueError('Phone should starts with 7')

class ClientIDsField(Field):
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, list):
            raise ValueError('List expected')

class DateField(Field):
    def validate(self, value):
        super().validate(value)
        if not (re.search(r'\d{2}.\d{2}.\d{4}',value)):
            raise ValueError('Wrong date')

class BirthDayField(DateField):
    def validate(self, value):
        super().validate(value)
        value = int(value.split('.')[-1])
        d = datetime.datetime.now()
        if (d.year - value) > 70:
            raise ValueError('Date after 70 years ago expected')
        

# Request class
class Request():
    def __init__(self, **kwargs):
        self.field_classes = {}
        for field in kwargs:
            value = getattr(self, field, None)
            if isinstance(value, Field):
                self.field_classes[field] = value

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
    return False


def method_handler(request, ctx, store):
    response, code = ERRORS.get(FORBIDDEN), FORBIDDEN
    try:
        data = MethodRequest(**request['body'])
        if check_auth(data):
        # request method checking
            if data.method == 'online_score':
                data1 = OnlineScoreRequest(**data.arguments)
                score = get_score(store, data1.phone, data1.email, data1.birthday, data1.gender, data1.first_name, data1.last_name) if not data.is_admin else 42
                ctx['has'] = [f for f, v in data1.field_classes.items()]
                response, code = {"score": score}, OK
            elif data.method == 'clients_interests':
                data1 = ClientsInterestsRequest(**data.arguments)
                interests = dict((client_id, get_interests(store, client_id)) for client_id in data.arguments['client_ids'])
                ctx['nclients'] = len(data1.client_ids)
                response, code = interests, OK
            else:
             response, code = ERRORS.get(INVALID_REQUEST), INVALID_REQUEST
    except ValueError as err:
        return str(err), INVALID_REQUEST
    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode())
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
