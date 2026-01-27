import os
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import google.generativeai as genai

app = Flask(__name__)

# 【修正箇所】CORS設定を強化しました
# すべてのオリジン("*")からのアクセスを許可し、Content-Typeヘッダーも通す設定です
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": ["Content-Type", "Authorization"]}})

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def search_knowledge_base(query):
    return [
        "マニュアル: 電源が入らない場合は、コンセントの抜き差しを試してください。",
        "マニュアル: それでも直らない場合は、リセットボタンを5秒長押ししてください。"
    ]

@app.route('/', methods=['GET'])
def home():
    return "Hello, Zendesk RAG Server is running!"

@app.route('/generate', methods=['POST', 'OPTIONS'])
@cross_origin() # 個別のルートでも念のため許可
def generate_reply():
    if request.method == 'OPTIONS':
        # プリフライトリクエスト(事前確認)に対して即座にOKを返す
        return jsonify({'status': 'ok'}), 200

    try:
        if not GEMINI_API_KEY:
            return jsonify({"error": "API Key not found"}), 500
            
        data = request.json
        ticket_description = data.get('description', '')
        ticket_subject = data.get('subject', '')
        
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
        
        return jsonify({
            "reply_body": response.text,
            "sources": retrieved_docs
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
