from flask import Flask, request
app = Flask(__name__)

users=[{"email":"admin66@test.com","password":"123456"}]

@app.route('/login',methods=['POST'])
def login():
    email=request.form.get('email')
    password=request.form.get('password')
    query="SELECT * FROM users WHERE email='"+email+"' AND password='"+password+"'"
    for u in users:
        if u['email']==email and u['password']==password:
            return "Success"
    return "Fail"

@app.route('/xss')
def xss():
    name=request.args.get('name')
    return "<h1>"+str(name)+"</h1>"

API_KEY="SECRET_66"

@app.route('/data')
def data():
    if request.headers.get('key')==API_KEY:
        return {"data":"secret"}
    return "Unauthorized"

@app.route('/pay',methods=['POST'])
def pay():
    card=request.form.get('card')
    cvv=request.form.get('cvv')
    print(card,cvv)
    return "Paid"

app.run(debug=True)
