from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app.forms import RegistrationForm, LoginForm, SiteForm, KeywordForm, PromptForm
from app.models import User, Site, ScheduledPost, Prompt
from app import db
from app.wp_client import post_to_wordpress
from app.image_search import search_image
import os
import openai
import pytz
from datetime import datetime, timedelta
import random

openai.api_key = os.getenv("OPENAI_API_KEY")

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('main.register'))
    return render_template('index.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('登録が完了しました！ログインしてください。')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('メールアドレスまたはパスワードが違います。')
            return redirect(url_for('main.login'))
        login_user(user)
        flash('ログインに成功しました！')
        return redirect(url_for('main.index'))
    return render_template('login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ログアウトしました。')
    return redirect(url_for('main.index'))

@bp.route('/dashboard')
@login_required
def dashboard():
    article_count = ScheduledPost.query.filter_by(user_id=current_user.id).count()
    api_usage_tokens = db.session.query(db.func.sum(ScheduledPost.api_tokens_used)).filter_by(user_id=current_user.id).scalar() or 0
    return render_template('dashboard.html', article_count=article_count, api_usage_tokens=api_usage_tokens)

@bp.route('/manage-sites', methods=['GET', 'POST'])
@login_required
def manage_sites():
    form = SiteForm()
    if form.validate_on_submit():
        site = Site(
            url=form.url.data,
            username=form.username.data,
            app_password=form.app_password.data,
            owner=current_user
        )
        db.session.add(site)
        db.session.commit()
        flash('サイトが登録されました！')
        return redirect(url_for('main.manage_sites'))
    sites = current_user.sites
    return render_template('manage_sites.html', form=form, sites=sites)

@bp.route('/generate-articles', methods=['GET', 'POST'])
@login_required
def generate_articles():
    form = KeywordForm()
    prompts = Prompt.query.filter_by(user_id=current_user.id).all()
    form.prompt_id.choices = [(p.id, p.genre) for p in prompts]

    if form.validate_on_submit():
        raw_keywords = form.keywords.data.strip().splitlines()
        keywords = [kw.strip() for kw in raw_keywords if kw.strip()]
        if len(keywords) > 40:
            flash('キーワードは最大40件までです。')
            return redirect(url_for('main.generate_articles'))

        selected_prompt = Prompt.query.get(form.prompt_id.data)
        posts_to_schedule = []

        for keyword in keywords:
            title, title_tokens = generate_article_from_prompt(selected_prompt.title_prompt, keyword)
            body, body_tokens = generate_article_from_prompt(selected_prompt.body_prompt, keyword)
            image_url = search_image(keyword)
            total_tokens = title_tokens + body_tokens

            if title and body:
                post = ScheduledPost(
                    keyword=keyword,
                    title=title,
                    body=body,
                    featured_image=image_url,
                    user_id=current_user.id,
                    site_id=current_user.sites[0].id,
                    api_tokens_used=total_tokens
                )
                posts_to_schedule.append(post)
            else:
                flash(f"キーワード「{keyword}」の記事生成に失敗しました。")

        # スケジュール設定
        now = datetime.now(pytz.timezone('Asia/Tokyo'))
        tomorrow = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

        scheduled_posts = []
        current_time = tomorrow
        post_counter = 0
        daily_post_count = random.randint(3, 5)

        for post in posts_to_schedule:
            if post_counter >= daily_post_count:
                current_time += timedelta(days=1)
                daily_post_count = random.randint(3, 5)
                post_counter = 0
                current_time = current_time.replace(hour=10, minute=0)

            min_minutes = 120
            max_minutes = 240
            random_minutes = random.randint(min_minutes, max_minutes)
            current_time += timedelta(minutes=random_minutes)

            if current_time.hour >= 22:
                current_time = (current_time + timedelta(days=1)).replace(hour=10, minute=0)
                daily_post_count = random.randint(3, 5)
                post_counter = 0

            post.scheduled_time = current_time
            scheduled_posts.append(post)
            post_counter += 1

        db.session.add_all(scheduled_posts)
        db.session.commit()

        flash(f"{len(scheduled_posts)}件の記事が保存され、スケジュール設定されました！")
        return redirect(url_for('main.admin_log'))

    return render_template('generate_articles.html', form=form)

@bp.route('/admin-log')
@login_required
def admin_log():
    site_id = request.args.get('site_id', type=int)
    user_sites = current_user.sites

    if not site_id and user_sites:
        site_id = user_sites[0].id

    current_site = Site.query.get(site_id)
    posts = ScheduledPost.query.filter_by(user_id=current_user.id, site_id=site_id).order_by(ScheduledPost.scheduled_time.asc()).all()

    return render_template('admin_log.html', posts=posts, user_sites=user_sites, current_site=current_site)

@bp.route('/view-post/<int:post_id>')
@login_required
def view_post(post_id):
    post = ScheduledPost.query.get_or_404(post_id)
    return f"<h1>{post.title}</h1><p>{post.body}</p>"

@bp.route('/edit-post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = ScheduledPost.query.get_or_404(post_id)
    if request.method == 'POST':
        post.title = request.form['title']
        post.body = request.form['body']
        db.session.commit()
        flash('記事を更新しました！')
        return redirect(url_for('main.admin_log'))
    return render_template('edit_post.html', post=post)

@bp.route('/delete-post/<int:post_id>')
@login_required
def delete_post(post_id):
    post = ScheduledPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('記事を削除しました！')
    return redirect(url_for('main.admin_log'))

@bp.route('/post-now/<int:post_id>')
@login_required
def post_now(post_id):
    post = ScheduledPost.query.get_or_404(post_id)
    site = current_user.sites[0]

    success = post_to_wordpress(
        site_url=site.url,
        username=site.username,
        app_password=site.app_password,
        title=post.title,
        content=post.body,
        featured_image_url=post.featured_image
    )

    if success:
        db.session.delete(post)
        db.session.commit()
        flash(f'記事「{post.title}」をWordPressに投稿しました！')
    else:
        flash(f'記事「{post.title}」の投稿に失敗しました。')

    return redirect(url_for('main.admin_log'))

@bp.route('/manage-prompts', methods=['GET', 'POST'])
@login_required
def manage_prompts():
    form = PromptForm()
    if form.validate_on_submit():
        prompt = Prompt(
            genre=form.genre.data,
            title_prompt=form.title_prompt.data,
            body_prompt=form.body_prompt.data,
            user_id=current_user.id
        )
        db.session.add(prompt)
        db.session.commit()
        flash('プロンプトが保存されました！')
        return redirect(url_for('main.manage_prompts'))

    prompts = Prompt.query.filter_by(user_id=current_user.id).all()
    return render_template('manage_prompts.html', form=form, prompts=prompts)

@bp.route('/delete-prompt/<int:prompt_id>')
@login_required
def delete_prompt(prompt_id):
    prompt = Prompt.query.get_or_404(prompt_id)
    db.session.delete(prompt)
    db.session.commit()
    flash('プロンプトを削除しました！')
    return redirect(url_for('main.manage_prompts'))

def generate_article_from_prompt(prompt_text, keyword):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": prompt_text},
                {"role": "user", "content": f"キーワード：「{keyword}」"}
            ],
            temperature=0.5,
            max_tokens=1500,
            top_p=0.9,
            frequency_penalty=0.3,
            presence_penalty=0.2,
            timeout=20,
        )
        result = response['choices'][0]['message']['content']
        tokens_used = response['usage']['total_tokens']
        return result.strip(), tokens_used
    except Exception as e:
        current_app.logger.error(f"プロンプト生成エラー: {e}")
        return None, 0

@bp.route('/dashboard-graph')
@login_required
def dashboard_graph():
    from sqlalchemy import func
    from datetime import datetime, timedelta

    today = datetime.utcnow().date()
    start_date = today - timedelta(days=29)

    user_sites = current_user.sites
    site_id = request.args.get('site_id', type=int)
    view = request.args.get('view', 'daily')  # 追加！viewパラメータ取得（デフォルトはdaily）

    # 初期表示（site_id指定なし）の場合は最初のサイト
    if not site_id and user_sites:
        site_id = user_sites[0].id

    current_site = Site.query.get(site_id)

    # クエリ基本
    query = db.session.query(
        func.date(ScheduledPost.created_at).label('day'),
        func.count().label('article_count')
    ).filter(
        ScheduledPost.user_id == current_user.id,
        ScheduledPost.site_id == site_id,
        ScheduledPost.created_at >= start_date
    )

    # 集計粒度を変更（日別 or 週別 or 月別）
    if view == 'weekly':
        # 週番号でグループ化
        query = db.session.query(
            func.strftime('%Y-%W', ScheduledPost.created_at).label('week'),
            func.count().label('article_count')
        ).filter(
            ScheduledPost.user_id == current_user.id,
            ScheduledPost.site_id == site_id,
            ScheduledPost.created_at >= start_date
        ).group_by('week')

        labels_counts = query.all()
        labels = [w.week for w in labels_counts]
        counts = [w.article_count for w in labels_counts]

    elif view == 'monthly':
        # 月でグループ化
        query = db.session.query(
            func.strftime('%Y-%m', ScheduledPost.created_at).label('month'),
            func.count().label('article_count')
        ).filter(
            ScheduledPost.user_id == current_user.id,
            ScheduledPost.site_id == site_id,
            ScheduledPost.created_at >= start_date
        ).group_by('month')

        labels_counts = query.all()
        labels = [m.month for m in labels_counts]
        counts = [m.article_count for m in labels_counts]

    else:
        # デフォルト（日別）
        query = query.group_by(func.date(ScheduledPost.created_at))

        labels_counts = query.all()

        # 30日分の日付を全て作る
        date_labels = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
        article_data = {p.day.strftime('%Y-%m-%d'): p.article_count for p in labels_counts}
        labels = date_labels
        counts = [article_data.get(date, 0) for date in labels]

    return render_template('dashboard_graph.html',
                           labels=labels,
                           counts=counts,
                           user_sites=user_sites,
                           current_site=current_site)


