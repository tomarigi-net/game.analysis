import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def home():
    if request.method == 'OPTIONS': return '', 200
    if request.method == 'GET': return "Backend Online"

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    # モデル名は指定の gemini-3-flash-preview
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"

    try:
        raw_data = request.data.decode('utf-8')
        data = json.loads(raw_data) if raw_data else {}
        thought = data.get('thought', '').strip()

        if not thought:
             return jsonify({"error": "Empty input", "detail": "内容を入力してください。"}), 200

        prompt = f"""
        あなたは心理カウンセラーです。以下の内容を心理学の「心理ゲーム」として客観的に分析し、JSON形式で出力してください。
        
        内容: {thought}
        """

        # 【修正ポイント】BLOCK_NONE を避け、BLOCK_ONLY_HIGH に変更
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
            ]
        }

        response = requests.post(url, json=payload, timeout=30)
        
        # もし400エラーが出た場合、設定が原因の可能性が高い
        if response.status_code != 200:
            print(f"Gemini API Error: {response.status_code} - {response.text}")
            return jsonify({"error": "API Error", "detail": "API設定エラーが発生しました。"}), 200

        result = response.json()
        
        candidates = result.get('candidates', [])
        if not candidates or 'content' not in candidates[0]:
            return jsonify({"error": "Safety", "detail": "AIが内容の分析を制限しました。別の表現でお試しください。"}), 200

        ai_text = candidates[0]['content']['parts'][0]['text']
        
        # JSON抽出処理
        start_idx = ai_text.find('{')
        end_idx = ai_text.rfind('}') + 1
        if start_idx != -1:
            return jsonify(json.loads(ai_text[start_idx:end_idx]))
        
        return jsonify({"error": "Format error", "detail": "回答形式が正しくありません。"}), 200

    except Exception as e:
        return jsonify({"error": "System error", "detail": str(e)}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)