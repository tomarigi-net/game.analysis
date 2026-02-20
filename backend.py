import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def get_prompt():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "prompt.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        print(f"Prompt loading error: {e}")
    return "あなたは優秀な交流分析カウンセラーです。必ずJSON形式で回答してください。"

SYSTEM_PROMPT = get_prompt()

@app.route('/', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def home():
    if request.method == 'OPTIONS':
        return '', 200
    
    if request.method == 'GET':
        return "CBT Backend is Online (Gemini 3 Mode)"

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    
    # 【最重要】スクリーンショットで確認した最新モデル名を指定
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent"

    try:
        data = request.get_json()
        thought = data.get('thought', '入力なし')

        payload = {
            "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nユーザーの思考: {thought}"}]}]
        }

        response = requests.post(url, params={"key": api_key}, json=payload, timeout=25)
        
        if response.status_code != 200:
            return jsonify({"error": "Gemini API Error", "detail": response.text}), response.status_code

        result = response.json()
        ai_text = result['candidates'][0]['content']['parts'][0]['text']
        
        # Markdown（```json ... ```）を安全に除去
        clean_json = ai_text.replace('```json', '').replace('```', '').strip()
        return jsonify(json.loads(clean_json))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Renderは環境変数 PORT を指定してくるので、それに従いつつ
    # 0.0.0.0 (外部からの接続許可) で起動します
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)