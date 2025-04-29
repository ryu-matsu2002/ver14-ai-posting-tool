from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import login
from sqlalchemy import ForeignKeyConstraint

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sites = db.relationship('Site', backref='owner', lazy=True)  # 追加！

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Site(db.Model):  # 追加！
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(64), nullable=False)
    app_password = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Site {self.url}>'

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class ScheduledPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=True)
    body = db.Column(db.Text, nullable=True)
    featured_image = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_time = db.Column(db.DateTime)
    posted = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id', name='fk_scheduled_post_site_id'), nullable=True)  # ←ここ修正  # ← サイト紐付け（後ほど追加対応）

    def __repr__(self):
        return f'<ScheduledPost {self.keyword}>'

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    genre = db.Column(db.String(100), nullable=False)  # ジャンル名
    title_prompt = db.Column(db.Text, nullable=False)  # タイトル用プロンプト
    body_prompt = db.Column(db.Text, nullable=False)   # 本文用プロンプト
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 作成者（ユーザー）

    def __repr__(self):
        return f'<Prompt {self.genre}>'    