import click
from flask import Flask, request, render_template, send_from_directory, url_for
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import ImageUploadField, thumbgen_filename
from flask_login import current_user
from flask_migrate import Migrate
from flask_security import UserMixin, RoleMixin, Security, SQLAlchemyUserDatastore
from flask_sqlalchemy import SQLAlchemy
import datetime, os

# config db
from markupsafe import Markup
from sqlalchemy.event import listens_for
from werkzeug.utils import redirect
from wtforms import TextAreaField
from wtforms.widgets import TextArea


class Config:
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:postgres@localhost/flask-blog"
    SECRET_KEY = "ini rahasia"
    SECURITY_PASSWORD_SALT = "ini juga rahasia"
    SECURITY_POST_LOGIN_VIEW = "/admin"

# starting some apps
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
admin = Admin(app, "blog", base_template='admin/master_admin.html', template_mode='bootstrap3') #register flask app

# role for security
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary= roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def __repr__(self):
        return self.email

# Setup Flask Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


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

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user = db.relationship("User", backref=db.backref("posts", lazy=True))

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
class LoginRequiredModelView(ModelView):
    def is_accessible(self):
        return current_user.is_active and current_user.is_authenticated and current_user.has_role("superuser")

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            if current_user.is_authenticated:
                os.abort(403)
            else:
                return redirect(url_for("security.login", next=request.url))

class CKTextAreaWidget(TextArea):
    def __call__(self, field, **kwargs):
        if kwargs.get('class'):
            kwargs['class'] += ' ckeditor'
        else:
            kwargs.setdefault('class', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)

class CKTextAreaField(TextAreaField):
    widget = CKTextAreaWidget()


class PostModelView(LoginRequiredModelView):
    extra_js = ['//cdn.ckeditor.com/4.6.0/standard/ckeditor.js']

    # to exclude some fields from built-in/standard view
    form_excluded_columns = ['user','created_at', 'updated_at']

    # will be stored in path like media/featured_images/filename
    form_extra_fields = dict(
        featured_image= ImageUploadField(
            base_path="media/",
            relative_path="featured_images/",
            endpoint="media", # "static"
            thumbnail_size=(200, 200, True)
        )
    )

    form_overrides = {
        'content' : CKTextAreaField
    }

    def _featured_image_column_formatter(self, context, model,name):
        if not model.featured_image:
            return ""
        return Markup(f"<img src='{url_for('media', filename=thumbgen_filename(model.featured_image))}'>")

    column_formatters = {"featured_image": _featured_image_column_formatter}

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.user = current_user
            db.session.add(model)
            db.session.commit()



admin.add_view(PostModelView(Post, db.session))
admin.add_view(LoginRequiredModelView(Category,db.session))
admin.add_view(LoginRequiredModelView(Tag, db.session))

# Routing URL for flask
@app.route('/')
def home():
    posts = Post.query.all()
    categories = Category.query.all()
    return render_template("index.html", categories=categories,posts=posts)

@app.route("/posts/<pk>/")
def post(pk):
    post = Post.query.get(pk)
    return render_template("post.html",post=post)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('PageNotFound.html')

@app.errorhandler(403)
def page_forbidden(e):
    return render_template('forbidden.html')

@app.route("/media/<path:filename>")
def media(filename):
    return send_from_directory("media", filename)

@app.cli.command("createsuperuser")
@click.argument("email")
@click.argument("password")
def createsuperuser(email,password):
    superuser = user_datastore.find_or_create_role("superuser")
    user = user_datastore.create_user(email=email, password=password, roles=[superuser])
    db.session.add(superuser)
    db.session.add(user)
    db.session.commit()

if __name__ == "__main__":
    app.run(debug=True,port=7989)