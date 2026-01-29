import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# APIキー設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 手動CORSヘッダー付与関数
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
    if request.method == 'OPTIONS':
        return build_cors_response({'status': 'ok'})

    try:
        if not GEMINI_API_KEY:
            return build_cors_response({"error": "API Key not found"}, 500)

        data = request.json
        if not data:
            return build_cors_response({"error": "No JSON data received"}, 400)

        ticket_description = data.get('description', '')
        ticket_subject = data.get('subject', '')

        # ■■■ ここが修正ポイント：モデルの自動検出 ■■■
        # 「文章生成(generateContent)」に対応しているモデルをリストアップして、
        # 最初に見つかったものを自動で使います。
        target_model_name = 'gemini-pro' # フォールバック用
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    target_model_name = m.name
                    print(f"DEBUG: Found available model: {target_model_name}") # ログ確認用
                    break
        except Exception as e:
            print(f"Warning: Could not list models. Using default. {e}")

        # RAG検索（ダミー）
        search_query = f"{ticket_subject} {ticket_description}"
        # search_knowledge_base関数をインライン定義
        docs = [
            "返品ポリシー: 到着後30日以内なら返品可能です。",
            "返金: 5営業日以内に処理されます。"
        ]
        context_text = "\n".join(docs)

        prompt = f"""
        あなたはカスタマーサポートです。以下の参考情報を使って返信を作成してください。
        [問い合わせ]
        {ticket_description}
        [参考情報]
        {context_text}
        """

        # 自動検出したモデル名で生成する
        model = genai.GenerativeModel(target_model_name)
        response = model.generate_content(prompt)

        return build_cors_response({
            "reply_body": response.text,
            "sources": docs
        })

    except Exception as e:
        print(f"Error: {e}")
        return build_cors_response({"error": str(e)}, 500)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
