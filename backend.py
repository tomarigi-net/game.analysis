import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def home():
    if request.method == 'OPTIONS':
        return '', 200
    if request.method == 'GET':
        return jsonify({"status": "online", "message": "Psychology Analyzer is ready!"})

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    # 最新の Gemini 3 Flash Preview 用 URL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"

    try:
        raw_data = request.data.decode('utf-8')
        data = json.loads(raw_data) if raw_data else {}
        thought = data.get('thought', '').strip()

        if not thought:
            return jsonify({"error": "Empty input", "detail": "内容を入力してください。"}), 200

        prompt = f"以下の相談内容を心理学（交流分析）の『心理ゲーム』として分析し、JSON形式で出力してください。回答は日本語でお願いします。\n内容: {thought}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code != 200:
            return jsonify({"error": "API Error", "detail": f"AI接続エラー({response.status_code})"}), 200

        result = response.json()
        ai_text = result['candidates'][0]['content']['parts'][0]['text']
        
        return jsonify(json.loads(ai_text))

    except Exception as e:
        return jsonify({"error": "System error", "detail": str(e)}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)