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
    # 最新の安定モデルを使用
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    try:
        raw_data = request.data.decode('utf-8')
        data = json.loads(raw_data) if raw_data else {}
        thought = data.get('thought', '').strip()

        if not thought:
             return jsonify({"error": "Empty input", "detail": "内容を入力してください。"}), 200

        # AIへの指示を「命令形」と「構造の定義」に特化
        prompt = f"""
        # Role
        You are an expert in Transactional Analysis (Psychology).
        
        # Task
        Analyze the following text as a "Psychological Game" and output ONLY in the specified JSON format.
        Input text: {thought}

        # JSON Format (Strict)
        {{
          "game_name": "Game Name",
          "definition": "Brief definition",
          "position_start": {{"self": "OK or Not OK", "others": "OK or Not OK", "description": "start state"}},
          "position_end": {{"self": "OK or Not OK", "others": "OK or Not OK", "description": "end state"}},
          "prediction": "Future prediction",
          "hidden_motive": "Hidden gain",
          "advice": "How to avoid"
        }}
        
        Answer in Japanese. Output only JSON.
        """

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,  # 回答を安定させる
                "response_mime_type": "application/json" # JSON出力を強制
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
            ]
        }

        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"API Error: {response.text}")
            return jsonify({"error": "API Error", "detail": "AIサーバー側でエラーが発生しました。"}), 200

        result = response.json()
        
        # 回答の取り出し
        if 'candidates' in result and len(result['candidates']) > 0:
            ai_text = result['candidates'][0]['content']['parts'][0]['text']
            # JSONとして解析してフロントにそのまま返す
            return jsonify(json.loads(ai_text))
        else:
            return jsonify({"error": "Safety", "detail": "AIが回答を生成できませんでした。表現を少し変えてみてください。"}), 200

    except Exception as e:
        print(f"System error: {e}")
        return jsonify({"error": "System error", "detail": str(e)}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)