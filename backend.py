import os
import json
import requests
import re  # 正規表現ライブラリを追加
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def home():
    if request.method == 'OPTIONS':
        return '', 200
    if request.method == 'GET':
        return jsonify({"status": "online", "message": "Ready!"})

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"

    try:
        raw_data = request.data.decode('utf-8')
        data = json.loads(raw_data) if raw_data else {}
        thought = data.get('thought', '').strip()

        if not thought:
            return jsonify({"error": "Empty input"}), 200

        prompt = (
            "以下の内容を心理学（交流分析）で分析し、必ずJSON形式で出力してください。JSONの各値の中で改行は使わず、1行の文字列にしてください。\n"
            f"内容: {thought}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1  # 数値を下げて出力を安定させます
            }
        }

        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code != 200:
            return jsonify({"error": "API Error"}), 200

        result = response.json()
        ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # --- 強力なJSONクリーニング処理 ---
        # 1. マークダウンの枠を除去
        clean_text = re.sub(r'^```json\s*|```$', '', ai_text, flags=re.MULTILINE).strip()
        
        # 2. JSON内部の不正な制御文字や改行を無理やり修正
        # (Unterminated stringの原因となる改行コードをスペースに置換)
        clean_text = clean_text.replace('\n', ' ').replace('\r', '')

        try:
            parsed_json = json.loads(clean_text)
            return jsonify(parsed_json)
        except json.JSONDecodeError:
            # もしJSONパースに失敗しても、テキストとしてフロントに送る
            return jsonify({
                "game_name": "分析完了（形式調整中）",
                "definition": "AIの回答形式を調整しています。もう一度お試しください。",
                "advice": clean_text[:200] # 念のため生データを一部表示
            })

    except Exception as e:
        return jsonify({"error": "System error", "detail": str(e)}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)