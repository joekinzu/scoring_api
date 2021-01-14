### Scoring API

Declarative description language and system for validating requests to the HTTP API of the scoring service. To get the result, the user sends a valid JSON of a certain format in a POST request to the location / method.

#### Request structure
```
{"account": "<company name>", "login": "<username>", "method": "<method name>", "token": "<auth token>", "arguments": {<dictionary with arguments for a given method>}}
```
* account - String
* login - String
* method - String
* token - String
* arguments - Dictionary

#### Validation
Request is valid once all fields are valid

#### Response
OK:
```
{"code": <HTTP code>, "response": {<error text>}}
```
Error:
```
{"code": <HTTP code>, "error": {<error text>}}
```

#### Authentication:
Check auth function. If not passed will return
```{"code": 403, "error": "Forbidden"}```

### Methods
#### online_score
Arguments
* phone - String, starts with 7, 11 length
* email - String, email with @
* first_name - String
* last_name - String
* birthday - date DD.MM.YYYY, not older 70
* gender - integer - 0, 1 or 2

#### Context
Dictionary "has" - list of fields

#### Response
Number from get_score function
```
{"score": <int>}
```
in case user is admin
```
{"score": 42}
```
Validation error
```
{"code": 422, "error": "<error text>"}
```

#### Example
```
$ curl -X POST  -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95", "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "Стансилав", "last_name": "Ступников", "birthday": "01.01.1990", "gender": 1}}' http://127.0.0.1:8080/method/
```
```
{"code": 200, "response": {"score": 5.0}}
```

#### clients_interests.
Arguments
* client_ids - List
* date - date DD.MM.YYYY

#### Context
Dictionary "nclients" - id count

#### Response
List from get_interests function
```
{"client_id1": ["interest1", "interest2" ...], "client2": [...] ...}
```
Validation error
```
{"code": 422, "error": "<error text>"}
```

#### Example
```
$ curl -X POST  -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "admin", "method": "clients_interests", "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f24091386050205c324687a0", "arguments": {"client_ids": [1,2,3,4], "date": "20.07.2017"}}' http://127.0.0.1:8080/method/
```
```
{"code": 200, "response": {"1": ["books", "hi-tech"], "2": ["pets", "tv"], "3": ["travel", "music"], "4": ["cinema", "geek"]}}
```
