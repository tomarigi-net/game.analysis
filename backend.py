import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# すべてのオリジンからのリクエストを許可
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def home():
    if request.method == 'OPTIONS':
        return '', 200
    if request.method == 'GET':
        return "Psychology Game Analyzer Backend (Gemini 3 Mode) is Online."

    # APIキーの取得（RenderのEnvironment Variablesに設定してください）
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"

    try:
        # フロントエンドからのデータ受け取り
        raw_data = request.data.decode('utf-8')
        data = json.loads(raw_data) if raw_data else {}
        thought = data.get('thought', '').strip()

        if not thought:
             return jsonify({"error": "Empty input", "detail": "分析する内容を入力してください。"}), 200

        # AIへのプロンプト（JSON構造を強制）
        prompt = f"""
        あなたは心理カウンセラーです。以下の相談内容を交流分析の「心理ゲーム」として分析し、必ず指定のJSON形式のみで回答してください。

        ユーザーの思考: {thought}

        JSON構造:
        {{
          "game_name": "特定されたゲームの名前",
          "definition": "そのゲームの一般的な定義",
          "position_start": {{"self": "OK or Not OK", "others": "OK or Not OK", "description": "開始時の心理状態"}},
          "position_end": {{"self": "OK or Not OK", "others": "OK or Not OK", "description": "結末の心理状態"}},
          "prediction": "このまま繰り返した場合の結末",
          "hidden_motive": "このゲームで無意識に得ている利得",
          "advice": "ゲームを止めるための具体的なアドバイス"
        }}
        """

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }

        # Gemini APIリクエスト
        response = requests.post(url, json=payload, timeout=30)
        
        # API自体のエラーチェック
        if response.status_code != 200:
            print(f"API Error: {response.text}")
            return jsonify({"error": "API Error", "detail": "AIサーバーに接続できませんでした。"}), 200

        result = response.json()

        # AIの回答候補があるかチェック
        candidates = result.get('candidates', [])
        if not candidates:
            return jsonify({"error": "No response", "detail": "AIが回答を生成しませんでした。"}), 200

        candidate = candidates[0]
        
        # 安全ブロックのチェック
        finish_reason = candidate.get('finishReason')
        if finish_reason not in ["STOP", "MAX_TOKENS", None]:
            return jsonify({"error": "Safety", "detail": f"内容がAIの安全ポリシーに触れました（理由: {finish_reason}）。少し表現を変えてみてください。"}), 200

        # テキストの抽出とJSONパース
        try:
            ai_text = candidate['content']['parts'][0]['text']
            
            # JSON以外のテキストが含まれている場合のクリーニング
            start_idx = ai_text.find('{')
            end_idx = ai_text.rfind('}') + 1
            if start_idx == -1:
                raise ValueError("JSONが見つかりません")
            
            json_str = ai_text[start_idx:end_idx]
            analysis_data = json.loads(json_str)
            
            return jsonify(analysis_data)

        except Exception as e:
            print(f"Parsing error: {e} | AI Text: {ai_text}")
            return jsonify({"error": "Format error", "detail": "AIの回答を読み込めませんでした。"}), 200

    except Exception as e:
        print(f"System fatal error: {e}")
        return jsonify({"error": "System error", "detail": str(e)}), 200

if __name__ == '__main__':
    # Renderのポート番号に対応
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)