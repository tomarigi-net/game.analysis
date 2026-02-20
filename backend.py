import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
# GitHubからのアクセスを許可
CORS(app, resources={r"/*": {"origins": "https://tomarigi-net.github.io"}})

# 環境変数からAPIキーを取得
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "running"}), 200

@app.route('/', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        user_thought = data.get("thought", "")
        
        if not user_thought:
            return jsonify({"error": "input empty"}), 400

        # 最新のモデルを指定
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # AIへの指示（プロンプト）
        prompt = f"""
        以下の心理的なやり取りを分析し、必ずJSON形式のみで回答してください。
        
        【対象】
        {user_thought}

        【出力形式】
        {{
          "game_name": "心理ゲーム名",
          "definition": "ゲームの解説",
          "position_start": {{ "self": "OK or NOT OK", "others": "OK or NOT OK", "description": "開始時の状態" }},
          "position_end": {{ "self": "OK or NOT OK", "others": "OK or NOT OK", "description": "結末の状態" }},
          "prediction": "このまま繰り返すとどうなるか",
          "hidden_motive": "このゲームで無意識に得ているもの",
          "advice": "ゲームを止めるためのアドバイス"
        }}
        """

        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # --- ここから「200 22」問題を解決する重要ロジック ---
        # AIが回答の前後に「```json」などを付けても、中身のJSONだけを取り出す
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.split("```")[0]
        
        # JSONとして解析できるかチェック
        result = json.loads(text.strip())
        
        # 成功：解析したデータを丸ごと送る（これでサイズが数千になるはずです）
        return jsonify(result)

    except Exception as e:
        print(f"Error: {e}")
        # エラー時もHTML側で表示できるよう、JSON形式で返す
        return jsonify({
            "game_name": "分析エラー",
            "definition": "AIからの応答を解析できませんでした。",
            "prediction": f"詳細: {str(e)}",
            "hidden_motive": "-",
            "advice": "もう一度試すか、入力内容を変えてみてください。"
        }), 200