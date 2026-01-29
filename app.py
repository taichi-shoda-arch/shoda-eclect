import os
import json
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

# ■■■ 知識データを読み込む関数 ■■■
def load_knowledge():
    try:
        with open('knowledge.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading knowledge: {e}")
        return []

# ■■■ 検索ロジック（キーワード検索） ■■■
def search_knowledge_base(query):
    data = load_knowledge()
    results = []
    
    # クエリを単語に分解（簡易的な検索）
    keywords = query.replace("　", " ").split()
    
    for item in data:
        # タイトルか本文にキーワードが含まれていればヒットとする
        text_to_search = (item['title'] + item['content']).lower()
        
        # すべてのキーワードが含まれているかチェック（AND検索）
        # ※もっと緩くしたい場合はここを調整します
        match_count = 0
        for k in keywords:
            if k.lower() in text_to_search:
                match_count += 1
        
        # 1つでもキーワードがヒットしたら候補に入れる
        if match_count > 0:
            results.append(f"【{item['title']}】\n{item['content']}")

    if not results:
        # ヒットしなかった場合のデフォルトメッセージ
        return ["関連するマニュアルは見つかりませんでした。一般的な回答を作成します。"]
    
    return results

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

        # モデル自動検出
        target_model_name = 'gemini-pro'
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    target_model_name = m.name
                    break
        except:
            pass

        # 1. 検索実行
        search_query = f"{ticket_subject} {ticket_description}"
        retrieved_docs = search_knowledge_base(search_query)
        context_text = "\n\n".join(retrieved_docs)

        # 2. プロンプト作成
        prompt = f"""
        あなたはカスタマーサポート担当者です。
        以下の[社内マニュアル]を元に、ユーザーへの返信を作成してください。

        [ユーザーの問い合わせ]
        件名: {ticket_subject}
        本文: {ticket_description}

        [社内マニュアル]
        {context_text}

        [制約]
        - マニュアルに記載がある場合は、その手順を案内してください。
        - マニュアルに情報がない場合は、正直に「担当者に確認します」と伝えてください。
        - 丁寧なビジネスメールの形式で書いてください。
        """

        model = genai.GenerativeModel(target_model_name)
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
