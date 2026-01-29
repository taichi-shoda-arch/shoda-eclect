import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# ここでAPIキーを読み込みますが、読み込めなくてもエラーにせず進みます
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
        # ■■■ 診断ポイント ■■■
        # キーがない場合、サーバーが見えている環境変数の「名前リスト」を返します
        if not GEMINI_API_KEY:
            # 値(Value)は返さず、キー名(Key)だけをリストにします
            available_keys = list(os.environ.keys())
            print(f"DEBUG: Available keys: {available_keys}") # Renderログ用
            
            return build_cors_response({
                "error": "API Key not found",
                "message": "Renderの設定画面と名前が一致しているか確認してください。",
                "server_sees_these_keys": available_keys  # サーバーが見ているキー一覧
            }, 500)

        data = request.json
        if not data:
            return build_cors_response({"error": "No JSON data received"}, 400)

        ticket_description = data.get('description', '')
        ticket_subject = data.get('subject', '')

        # ダミーRAG検索
        # 本来のsearch_knowledge_base関数
        def search_knowledge_base(query):
             return ["マニュアル: 返品は購入後30日以内です。"]

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

        return build_cors_response({
            "reply_body": response.text,
            "sources": retrieved_docs
        })

    except Exception as e:
        print(f"Error: {e}")
        return build_cors_response({"error": str(e)}, 500)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
