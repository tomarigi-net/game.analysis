import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# CORS設定：すべてのオリジンからのアクセスを許可
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

        # AIがJSONのみを返すようプロンプトで念押しします
        prompt = (
            "以下の相談内容を心理学（交流分析）の『心理ゲーム』として分析し、必ず純粋なJSON形式のみで出力してください。余計な解説文は不要です。回答は日本語でお願いします。\n"
            f"内容: {thought}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "max_output_tokens": 1000
            }
        }

        # タイムアウトを60秒に設定
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code != 200:
            return jsonify({"error": "API Error", "detail": f"AI接続エラー({response.status_code}): {response.text}"}), 200

        result = response.json()
        ai_text = result['candidates'][0]['content']['parts'][0]['text']
        
        # 【重要】AIが返してくるマークダウンの飾り（```json ... ```）を剥ぎ取ります
        clean_text = ai_text.strip()
        if clean_text.startswith("```"):
            # 最初と最後の ``` を探し、その間だけを抽出
            lines = clean_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_text = "\n".join(lines).strip()
        
        # 最終的にJSONとしてパースしてフロントに返します
        return jsonify(json.loads(clean_text))

    except Exception as e:
        # エラー発生時も200で返し、詳細をフロントに伝えてフリーズを防ぎます
        return jsonify({"error": "System error", "detail": str(e)}), 200

if __name__ == '__main__':
    # Render環境用のポート設定
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)