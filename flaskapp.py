from flask import Flask,request, render_template
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


class Config:
    SQLALCHEMY_DATABASE_URI = "sqlite:///coba.db"

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app)

class Post(db.Model):
    title = db.Column(db.String(250))
    content = db.Column(db.Text())
    created_at = db.Column(db.DateTime(), default="")
    updated_at = db.Column(db.DateTime())

@app.route('/')
def home():
    method = request.method
    get_requests = request.args
    author = "Erwin"
    return render_template("index.html", method=method, arguments=get_requests, author=author)

@app.route("/hello")
def hello():
    return render_template("hello.html")

@app.route("/posts/<pk>/")
def post(pk):
    return render_template("post.html",pk=pk)

@app.route("/course/<name>/<subtitle>")
def course(name, subtitle):
    return f"ini adalah halaman course {name} dengan subtitle {subtitle}"

if __name__ == "__main__":
    app.run(debug=True,port=7989)