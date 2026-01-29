import os
import json
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# APIキー設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 手動CORSヘッダー
def build_cors_response(data, status_code=200):
    response = jsonify(data)
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response, status_code

# 知識データの読み込み
def load_knowledge():
    try:
        with open('knowledge.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading knowledge: {e}")
        return []

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

        # ■■■ 修正ポイント：検索ロジックを廃止し、全データをAIに渡す ■■■
        # データの量が少ないうちは、Pythonで検索するより
        # AIに全部読ませて判断させたほうが圧倒的に精度が高いです。
        
        knowledge_data = load_knowledge()
        
        # 全データをテキスト化してコンテキストにする
        all_knowledge_text = ""
        if knowledge_data:
            for item in knowledge_data:
                all_knowledge_text += f"【{item['title']}】\n{item['content']}\n\n"
        else:
            all_knowledge_text = "（マニュアルデータが見つかりませんでした）"

        # AIへの指示（プロンプト）
        prompt = f"""
        あなたはカスタマーサポート担当者です。
        以下の[社内マニュアル]全体を読み、ユーザーの問い合わせに該当する情報があれば、それを使って返信を作成してください。

        [ユーザーの問い合わせ]
        件名: {ticket_subject}
        本文: {ticket_description}

        [社内マニュアル]
        {all_knowledge_text}

        [制約]
        - マニュアルの中に質問の答えがある場合のみ、その手順を案内してください。
        - マニュアルに全く関係のない質問の場合は、「担当者に確認します」と答えてください。
        - 日本語のビジネスメール形式で作成してください。
        """

        model = genai.GenerativeModel(target_model_name)
        response = model.generate_content(prompt)

        return build_cors_response({
            "reply_body": response.text,
            "sources": ["全マニュアルデータを参照しました"] 
        })

    except Exception as e:
        print(f"Error: {e}")
        return build_cors_response({"error": str(e)}, 500)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
