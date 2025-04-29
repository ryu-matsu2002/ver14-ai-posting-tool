import base64
import requests
from flask import current_app


def post_to_wordpress(site_url, username, app_password, title, content, featured_image_url=None):
    credentials = f'{username}:{app_password}'
    token = base64.b64encode(credentials.encode()).decode('utf-8')

    headers = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json'
    }

    post_data = {
        'title': title,
        'content': content,
        'status': 'publish'
    }

    if featured_image_url:
        media_id = upload_image_to_wordpress(site_url, username, app_password, featured_image_url)
        if media_id:
            post_data['featured_media'] = media_id

    try:
        response = requests.post(
            f'{site_url.rstrip("/")}/wp-json/wp/v2/posts',
            headers=headers,
            json=post_data,
            timeout=15
        )
        response.raise_for_status()
        current_app.logger.info('WordPress投稿成功！')
        return True
    except Exception as e:
        current_app.logger.error(f'WordPress投稿エラー: {e}')
        return False


def upload_image_to_wordpress(site_url, username, app_password, image_url):
    credentials = f'{username}:{app_password}'
    token = base64.b64encode(credentials.encode()).decode('utf-8')

    # 画像を一時取得
    try:
        img_resp = requests.get(image_url, timeout=10)
        img_resp.raise_for_status()
    except Exception as e:
        current_app.logger.error(f"画像ダウンロードエラー: {e}")
        return None

    headers = {
        'Authorization': f'Basic {token}',
        'Content-Disposition': 'attachment; filename=image.jpg',
        'Content-Type': 'image/jpeg'
    }

    try:
        upload_resp = requests.post(
            f'{site_url.rstrip("/")}/wp-json/wp/v2/media',
            headers=headers,
            data=img_resp.content,
            timeout=15
        )
        upload_resp.raise_for_status()
        media_id = upload_resp.json()['id']
        current_app.logger.info(f"画像アップロード成功。Media ID: {media_id}")
        return media_id
    except Exception as e:
        current_app.logger.error(f"WordPress画像アップロードエラー: {e}")
        return None