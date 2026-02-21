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

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"

    try:
        data = request.get_json()
        thought = data.get('thought', '').strip() if data else ""

        if not thought:
            return jsonify({"error": "Empty input"}), 200

        prompt = (
            "交流分析のエキスパートとして、以下の内容を分析し、必ず指定のJSON形式のみで回答してください。\n"
            "JSON以外の説明テキスト、Markdownの装飾（```jsonなど）は一切含めないでください。\n\n"
            "【厳守するJSON構造】\n"
            "{\n"
            '  "game_name": "名称",\n'
            '  "definition": "定義",\n'
            '  "position_start": {"self": "OK or NOT OK", "others": "OK or NOT OK", "description": "解説"},\n'
            '  "position_end": {"self": "OK or NOT OK", "others": "OK or NOT OK", "description": "解説"},\n'
            '  "prediction": "予測の内容",\n'
            '  "hidden_motive": "無意識の利得の内容",\n'
            '  "advice": "回避策の内容"\n'
            "}\n\n"
            f"【分析対象】: {thought}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code != 200:
            return jsonify({"error": "API Error", "detail": response.text}), 200

        result = response.json()
        
        if 'candidates' in result and result['candidates']:
            ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # --- 強化された抽出ロジック ---
            # 1. Markdownタグを削除
            clean_text = re.sub(r'```json\s*|```', '', ai_text)
            
            # 2. 最初と最後の波括弧 { } の範囲を強制抽出（余計な説明文をカット）
            start_idx = clean_text.find('{')
            end_idx = clean_text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                clean_text = clean_text[start_idx:end_idx+1]
            
            try:
                parsed_json = json.loads(clean_text)
                return jsonify(parsed_json)
            except json.JSONDecodeError:
                # パース失敗時も、ブラウザが落ちないようJSON形式でエラー内容を返す
                return jsonify({
                    "game_name": "解析成功（整形のみ失敗）",
                    "definition": "AIが特殊な形式で回答したため、一部表示を調整しました。",
                    "prediction": clean_text[:500],
                    "hidden_motive": "抽出失敗",
                    "advice": "もう一度送信するか、内容を簡潔にしてお試しください。"
                })
        else:
            return jsonify({"error": "No response from AI"}), 200

    except Exception as e:
        return jsonify({"error": "System error", "detail": str(e)}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000)) 
    app.run(host="0.0.0.0", port=port)