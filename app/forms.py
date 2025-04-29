from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, URL

class RegistrationForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('パスワード再入力', validators=[DataRequired(), EqualTo('password', message='パスワードが一致しません')])
    submit = SubmitField('登録')

class LoginForm(FlaskForm):
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[DataRequired()])
    submit = SubmitField('ログイン')

class SiteForm(FlaskForm):  # 追加！
    url = StringField('WordPressサイトURL', validators=[DataRequired(), URL()])
    username = StringField('WordPressユーザー名', validators=[DataRequired()])
    app_password = StringField('アプリケーションパスワード', validators=[DataRequired()])
    submit = SubmitField('サイトを登録')

class KeywordForm(FlaskForm):
    keywords = TextAreaField('キーワードを1行ずつ入力（最大40件）', validators=[DataRequired()])
    prompt_id = SelectField('使用するプロンプト', coerce=int)  # ← 追加！（プロンプト選択用）
    submit = SubmitField('記事を生成')   

class PromptForm(FlaskForm):
    genre = StringField('ジャンル名', validators=[DataRequired(), Length(min=2, max=100)])
    title_prompt = TextAreaField('タイトル生成用プロンプト', validators=[DataRequired()])
    body_prompt = TextAreaField('本文生成用プロンプト', validators=[DataRequired()])
    submit = SubmitField('プロンプトを保存')    