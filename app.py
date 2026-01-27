import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app) # 基本的なCORS設定

# 【最強のCORS対策】
# どんなレスポンスにも強制的にCORS許可ヘッダーを付与する設定
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def search_knowledge_base(query):
    # ダミーの検索機能
    return [
        "マニュアル: 電源が入らない場合は、コンセントの抜き差しを試してください。",
        "マニュアル: それでも直らない場合は、リセットボタンを5秒長押ししてください。"
    ]

@app.route('/', methods=['GET'])
def home():
    return "Hello, Zendesk RAG Server is running!"

# OPTIONSメソッドも明示的に受け付けるように指定
@app.route('/generate', methods=['POST', 'OPTIONS'])
def generate_reply():
    # プリフライトリクエスト(OPTIONS)が来たら、中身なしで即OKを返す
    # (after_requestがヘッダーをつけてくれるので200だけでOK)
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    try:
        if not GEMINI_API_KEY:
            return jsonify({"error": "API Key not found"}), 500
            
        data = request.json
        ticket_description = data.get('description', '')
        ticket_subject = data.get('subject', '')
        
        # 1. RAG検索
        search_query = f"{ticket_subject} {ticket_description}"
        retrieved_docs = search_knowledge_base(search_query)
        context_text = "\n".join(retrieved_docs)
        
        # 2. プロンプト作成
        prompt = f"""
        あなたはカスタマーサポートです。以下の参考情報を使って、問い合わせへの返信を作成してください。
        [問い合わせ]
        {ticket_description}
        [参考情報]
        {context_text}
        """
        
        # 3. Gemini生成
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        return jsonify({
            "reply_body": response.text,
            "sources": retrieved_docs
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
