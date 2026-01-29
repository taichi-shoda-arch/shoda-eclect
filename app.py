import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# APIキー設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 手動CORSヘッダー付与関数（これが最強のCORS対策です）
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
        # キーがない場合のエラー
        if not GEMINI_API_KEY:
            return build_cors_response({"error": "API Key not found in server settings"}, 500)

        data = request.json
        if not data:
            return build_cors_response({"error": "No JSON data received"}, 400)

        ticket_description = data.get('description', '')
        ticket_subject = data.get('subject', '')

        # --- ここからRAG検索ロジック ---
        # ※今はダミーですが、将来ここをPineconeなどの検索コードに置き換えます
        def search_knowledge_base(query):
            return [
                "返品ポリシー: 商品到着後30日以内であれば、未使用に限り全額返金可能です。",
                "返金処理: 通常、返品受領から5営業日以内に完了します。",
                "送料: お客様都合の返品の場合、送料はお客様負担となります。"
            ]
        # ---------------------------

        search_query = f"{ticket_subject} {ticket_description}"
        retrieved_docs = search_knowledge_base(search_query)
        context_text = "\n".join(retrieved_docs)

        # AIへの指示（プロンプト）
        prompt = f"""
        あなたはカスタマーサポートの担当者です。
        以下の「参考情報」を元に、ユーザーの問い合わせに対する丁寧な返信メールを作成してください。

        [ユーザーの問い合わせ]
        件名: {ticket_subject}
        本文: {ticket_description}

        [参考情報]
        {context_text}

        [制約]
        - 挨拶から始めてください。
        - 参考情報にないことは捏造しないでください。
        - 簡潔かつ丁寧な日本語で書いてください。
        """

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)

        # 成功レスポンス
        return build_cors_response({
            "reply_body": response.text,
            "sources": retrieved_docs
        })

    except Exception as e:
        print(f"Error: {e}")
        return build_cors_response({"error": str(e)}, 500)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
