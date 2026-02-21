import os
import json
import requests
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# GitHub Pages からのアクセスのみを許可
CORS(app, resources={r"/*": {"origins": "https://tomarigi-net.github.io"}})

@app.route('/', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def home():
    if request.method == 'OPTIONS':
        return '', 200
    if request.method == 'GET':
        return jsonify({"status": "online", "message": "Gemini 3 Flash Ready!"})

    # 環境変数からAPIキーを取得
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    # モデル名をご指定の gemini-3-flash-preview に固定
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"

    try:
        # フロントエンドからのJSONを取得
        data = request.get_json()
        thought = data.get('thought', '').strip() if data else ""

        if not thought:
            return jsonify({"error": "Empty input"}), 200

        # AIへの指示（プロンプト）
        prompt = (
            "交流分析のエキスパートとして、以下の内容を分析し、必ずJSON形式で回答してください。\n"
            "【出力形式】\n"
            '{"game_name": "名称", "definition": "定義", "position_start": {"self": "OK or NOT OK", "others": "OK or NOT OK", "description": "解説"}, "position_end": {"self": "OK or NOT OK", "others": "OK or NOT OK", "description": "解説"}, "prediction": "予測", "hidden_motive": "利得", "advice": "回避策"}\n'
            f"【分析対象】: {thought}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        # Google APIへリクエスト送信
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code != 200:
            return jsonify({"error": "API Error", "detail": response.text}), 200

        result = response.json()
        
        # AIの回答テキストを取り出し
        if 'candidates' in result and result['candidates']:
            ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # JSON部分のクリーニング（余計な装飾を消す）
            clean_text = re.sub(r'^```json\s*|```$', '', ai_text, flags=re.MULTILINE).strip()
            
            try:
                parsed_json = json.loads(clean_text)
                return jsonify(parsed_json)
            except json.JSONDecodeError:
                # パース失敗時の救済措置
                return jsonify({
                    "game_name": "分析完了",
                    "definition": "解析結果の整形に失敗しましたが、内容は以下の通りです。",
                    "prediction": clean_text[:300]
                })
        else:
            return jsonify({"error": "No response from AI"}), 200

    except Exception as e:
        return jsonify({"error": "System error", "detail": str(e)}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)