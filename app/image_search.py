import os
import requests
import random

PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")  # .envファイルにPixabay APIキーを保存しておく

def search_image(keyword):
    try:
        url = "https://pixabay.com/api/"
        params = {
            "key": PIXABAY_API_KEY,
            "q": keyword,
            "image_type": "photo",
            "orientation": "horizontal",
            "safesearch": "true",
            "per_page": 10
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data['hits']:
            # ランダムで1枚選ぶ
            selected = random.choice(data['hits'])
            return selected['largeImageURL']
        else:
            return None
    except Exception as e:
        print(f"Pixabay検索エラー: {e}")
        return None
