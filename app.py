import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# APIキー設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def search_knowledge_base(query):
    return [
        "マニュアル: 電源が入らない場合は、コンセントの抜き差しを試してください。",
        "マニュアル: それでも直らない場合は、リセットボタンを5秒長押ししてください。"
    ]

# ■■■ ここが修正ポイント：手動でCORSヘッダーを付ける関数 ■■■
def build_cors_response(data, status_code=200):
    response = jsonify(data)
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response, status_code

@app.route('/', methods=['GET'])
def home():
    return "Hello, Zendesk RAG Server is running!"

@app.route('/generate', methods=['POST', 'OPTIONS'])
def generate_reply():
    # 1. プリフライトリクエスト(OPTIONS)への対応
    if request.method == 'OPTIONS':
        return build_cors_response({'status': 'ok'})

    # 2. 本番リクエスト(POST)の処理
    try:
        if not GEMINI_API_KEY:
            return build_cors_response({"error": "API Key not found"}, 500)

        data = request.json
        # データが空の場合の対策
        if not data:
            return build_cors_response({"error": "No JSON data received"}, 400)

        ticket_description = data.get('description', '')
        ticket_subject = data.get('subject', '')

        # RAG検索 & Gemini生成
        search_query = f"{ticket_subject} {ticket_description}"
        retrieved_docs = search_knowledge_base(search_query)
        context_text = "\n".join(retrieved_docs)

        prompt = f"""
        あなたはカスタマーサポートです。以下の参考情報を使って、問い合わせへの返信を作成してください。
        [問い合わせ]
        {ticket_description}
        [参考情報]
        {context_text}
        """

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)

        # 成功レスポンス（CORS付き）
        return build_cors_response({
            "reply_body": response.text,
            "sources": retrieved_docs
        })

    except Exception as e:
        print(f"Error: {e}")
        # エラーレスポンス（CORS付き）
        return build_cors_response({"error": str(e)}, 500)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
