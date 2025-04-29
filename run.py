from app import create_app, db
from app.models import ScheduledPost, Site
from app.wp_client import post_to_wordpress
from flask_apscheduler import APScheduler
from datetime import datetime
import pytz

app = create_app()

# ─────────────────────
# APSchedulerの設定
# ─────────────────────

class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# 投稿スケジュール監視ジョブ
@scheduler.task('interval', id='check_and_post_articles', seconds=60, misfire_grace_time=900)
def check_and_post_articles():
    with app.app_context():
        now = datetime.now(pytz.timezone('Asia/Tokyo'))

        # 投稿予定時刻 <= 現在時刻、かつ未投稿（posted=False）の記事を取得
        posts = ScheduledPost.query.filter(
            ScheduledPost.scheduled_time <= now,
            ScheduledPost.posted == False
        ).order_by(ScheduledPost.scheduled_time).all()

        for post in posts:
            site = Site.query.get(post.site_id)
            if not site:
                continue  # サイト情報がなければスキップ

            success = post_to_wordpress(
                site_url=site.url,
                username=site.username,
                app_password=site.app_password,
                title=post.title,
                content=post.body,
                featured_image_url=post.featured_image
            )

            if success:
                post.posted = True
                db.session.commit()
                print(f"✅ 投稿成功: {post.title}")
            else:
                print(f"❌ 投稿失敗: {post.title}")

# アプリ起動
if __name__ == "__main__":
    app.run(debug=True)
