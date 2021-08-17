from flask import Flask, request, render_template, send_from_directory, url_for
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import ImageUploadField, thumbgen_filename
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import datetime, os

# config db
from markupsafe import Markup
from sqlalchemy.event import listens_for


class Config:
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:postgres@localhost/flask-blog"
    SECRET_KEY = "ini rahasia"

# starting some apps
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
admin = Admin(app, "blog") #register flask app

# Make an example table for Post
class PostTag(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(250))
    content = db.Column(db.Text())
    featured_image = db.Column(db.String(500), nullable=True)

    # Connecting to Category
    category_id = db.Column(db.Integer, db.ForeignKey('category.id')) # just take category_id from category
    category = db.relationship('Category', backref=db.backref('posts', lazy=True)) # this one is relationship between category and post

    created_at = db.Column(db.DateTime(), default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime(), default=datetime.datetime.now, onupdate=datetime.datetime.now)

    # Connecting to Tag
    tags = db.relationship("Tag", secondary=PostTag.__tablename__ , backref=db.backref("posts", lazy=True))

    def __repr__(self):
        return self.title

    @property
    def featured_image_url(self):
        if self.featured_image :
            return url_for("media", filename=self.featured_image)
        return ""

@listens_for(Post, "after_delete")
def delete_featured_image(mapper, connection, instance):
    if not instance.featured_image:
        return

    featured_image_path = instance.featured_image
    images = [featured_image_path, thumbgen_filename(featured_image_path)]
    for image in images:
        try:
            os.remove(os.path.join("media", image))
        except:
            pass



class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255))

    def __repr__(self):
        return self.name

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255))

    def __repr__(self):
        return self.name

#register model view admin

class PostModelView(ModelView):

    # will be stored in path like media/featured_images/filename
    form_extra_fields = dict(
        featured_image= ImageUploadField(
            base_path="media/",
            relative_path="featured_images/",
            endpoint="media", # "static"
            thumbnail_size=(200, 200, True)
        )
    )

    def _featured_image_column_formatter(self, context, model,name):
        if not model.featured_image:
            return ""
        return Markup(f"<img src='{url_for('media', filename=thumbgen_filename(model.featured_image))}'>")

    column_formatters = {"featured_image": _featured_image_column_formatter}

admin.add_view(PostModelView(Post, db.session))
admin.add_view(ModelView(Category,db.session))
admin.add_view(ModelView(Tag, db.session))

# Routing URL for flask
@app.route('/')
def home():
    posts = Post.query.all()
    categories = Category.query.all()
    return render_template("index.html", categories=categories,posts=posts)

@app.route("/hello")
def hello():
    return render_template("hello.html")

@app.route("/posts/<pk>/")
def post(pk):
    post = Post.query.get(pk)
    return render_template("post.html",post=post)

@app.route("/course/<name>/<subtitle>")
def course(name, subtitle):
    return f"ini adalah halaman course {name} dengan subtitle {subtitle}"

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html')

@app.route("/media/<path:filename>")
def media(filename):
    return send_from_directory("media", filename)

if __name__ == "__main__":
    app.run(debug=True,port=7989)