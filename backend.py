import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# 外部（GitHub Pages）からのリクエストを許可
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def home():
    if request.method == 'OPTIONS':
        return '', 200
    if request.method == 'GET':
        return jsonify({"status": "online", "message": "Psychology Analyzer is ready!"})

    # APIキーの取得確認
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Config Error", "detail": "APIキーが設定されていません。"}), 200

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    try:
        raw_data = request.data.decode('utf-8')
        data = json.loads(raw_data) if raw_data else {}
        thought = data.get('thought', '').strip()

        if not thought:
             return jsonify({"error": "Empty input", "detail": "内容を入力してください。"}), 200

        # AIへの詳細なプロンプト（構造化出力を強制）
        prompt = f"""
        あなたは交流分析（Transactional Analysis）の専門家です。
        以下の「相談内容」を心理ゲームとして分析し、必ず指定のJSON形式で日本語で回答してください。

        相談内容: {thought}

        期待するJSON構造:
        {{
          "game_name": "心理ゲームの名称",
          "definition": "このゲームの定義",
          "position_start": {{"self": "OK or Not OK", "others": "OK or Not OK", "description": "開始時の心理的構え"}},
          "position_end": {{"self": "OK or Not OK", "others": "OK or Not OK", "description": "結末の心理的構え"}},
          "prediction": "このパターンを繰り返した場合の破綻の予測",
          "hidden_motive": "無意識に求めている心理的利得（ラケット感情など）",
          "advice": "ゲームを中断し、健康的な交流に切り替えるための助言"
        }}
        """

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
            ]
        }

        # Gemini APIへリクエスト
        response = requests.post(url, json=payload, timeout=30)
        
        # API自体がエラーを返した場合
        if response.status_code != 200:
            error_data = response.json()
            msg = error_data.get('error', {}).get('message', '不明なエラー')
            return jsonify({"error": "API Error", "detail": f"AI接続エラー({response.status_code}): {msg}"}), 200

        result = response.json()
        
        # 候補（candidates）があるかチェック
        candidates = result.get('candidates', [])
        if not candidates or 'content' not in candidates[0]:
            # 安全フィルター等でブロックされた場合
            return jsonify({"error": "Safety", "detail": "AIが内容の分析を制限しました。表現を和らげてみてください。"}), 200

        ai_text = candidates[0]['content']['parts'][0]['text']
        
        # JSONパースの試行
        try:
            analysis_data = json.loads(ai_text)
            return jsonify(analysis_data)
        except json.JSONDecodeError:
            # AIが不正なJSONを返した場合の抽出処理
            import re
            match = re.search(r'\{.*\}', ai_text, re.DOTALL)
            if match:
                return jsonify(json.loads(match.group()))
            raise Exception("AIの回答を解析できませんでした。")

    except Exception as e:
        print(f"Server Error: {str(e)}")
        return jsonify({"error": "System error", "detail": f"エラーが発生しました: {str(e)}"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)