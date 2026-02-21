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
    # モデル名をご指定の「gemini-3-flash-preview」に戻しました
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"

    try:
        data = request.get_json()
        thought = data.get('thought', '').strip() if data else ""

        if not thought:
            return jsonify({"error": "Empty input"}), 200

        # プロンプト：主体の自動判別（subject_name）を含めた最新版
        prompt = (
            "あなたはエリック・バーンの交流分析（Transactional Analysis）の世界的権威です。\n"
            "入力内容から、分析の主体（書き手）を「自分」、対人相手を「他者」として同定してください。\n"
            "文脈から判断できる場合は、「自分」と「他者」にふさわしい呼称（例：私、上司、妻、Aさん等）を特定してください。\n"
            "必ず以下のJSON形式のみで回答してください。\n\n"
            "【厳守するJSON構造】\n"
            "{\n"
            '  "subject_name": "自分に当たる人物の呼称",\n'
            '  "target_name": "相手に当たる人物の呼称",\n'
            '  "game_name": "名称",\n'
            '  "definition": "定義（100文字程度）",\n'
            '  "position_start": {"self": "I\'m OK または I\'m NOT OK", "others": "You\'re OK または You\'re NOT OK", "description": "開始時の表面的な心理状態"},\n'
            '  "position_end": {"self": "I\'m OK または I\'m NOT OK", "others": "You\'re OK または You\'re NOT OK", "description": "結末で味わう真の感情"},\n'
            '  "prediction": "このまま進んだ場合の最悪の結末",\n'
            '  "hidden_motive": "無意識に得ようとしている報酬",\n'
            '  "advice": "ゲームを降りるための具体的なヒント"\n'
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
            
            clean_text = re.sub(r'```json\s*|```', '', ai_text)
            start_idx = clean_text.find('{')
            end_idx = clean_text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                clean_text = clean_text[start_idx:end_idx+1]
            
            try:
                parsed_json = json.loads(clean_text)
                return jsonify(parsed_json)
            except json.JSONDecodeError:
                return jsonify({
                    "game_name": "解析成功（整形のみ失敗）",
                    "definition": "JSONパースに失敗しました。",
                    "prediction": clean_text[:500],
                    "hidden_motive": "抽出失敗",
                    "advice": "内容を少し変えてお試しください。"
                })
        else:
            return jsonify({"error": "No response from AI"}), 200

    except Exception as e:
        return jsonify({"error": "System error", "detail": str(e)}), 200

# ポート設定（Render用）
port = int(os.environ.get("PORT", 10000))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)