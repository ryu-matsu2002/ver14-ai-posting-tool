import os
import openai
from flask import current_app

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_article_from_keyword(keyword):
    system_prompt = (
        "あなたはプロのSEOライターです。与えられたキーワードについて、"
        "SEOに最適化された日本語の記事を2000文字程度で書いてください。"
        "記事には適切にh2タグを使い、導入文、本文、まとめの構成にしてください。"
        "です・ます調で丁寧に書いてください。"
    )

    user_prompt = f"キーワード：「{keyword}」についてSEO記事を書いてください。"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=2500,
            top_p=0.9,
            frequency_penalty=0.3,
            presence_penalty=0.2,
            timeout=20,
        )
        article_content = response['choices'][0]['message']['content']
        tokens_used = response['usage']['total_tokens']
        return article_content.strip(), tokens_used

    except Exception as e:
        current_app.logger.error(f"記事生成エラー: {e}")
        return None
