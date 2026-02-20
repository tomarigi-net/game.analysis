import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# CORS設定をより詳細に（すべてのオリジンとメソッドを許可）
CORS(app, resources={r"/*": {"origins": "*"}})

def get_prompt():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "prompt.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        print(f"Prompt loading error: {e}")
    return "あなたは優秀な交流分析カウンセラーです。必ずJSON形式で回答してください。"

SYSTEM_PROMPT = get_prompt()

@app.route('/', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def home():
    # OPTIONS（プリフライトリクエスト）への明示的な応答
    if request.method == 'OPTIONS':
        return '', 200
    
    if request.method == 'GET':
        return "CBT Backend is Online (Gemini 3 Mode)"

    # POST処理の開始
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"

    try:
        # 【修正ポイント】Flaskの自動パースを使わず、生のデータを取得
        raw_data = request.data.decode('utf-8')
        print(f"Raw data received: {raw_data}") # ログで確認

        try:
            data = json.loads(raw_data) if raw_data else {}
        except json.JSONDecodeError:
            # 万が一JSONが壊れていても、無理やり辞書として扱う
            data = request.form.to_dict() if request.form else {}

        thought = data.get('thought', '入力なし')
        
        # 思考内容が空の場合のガード
        if not thought or thought == '入力なし':
             return jsonify({"error": "Empty input", "detail": "内容が入力されていません"}), 200

        print(f"Processing thought: {thought}")

# Payloadの作成（カテゴリー名を正しい形式に修正）
        payload = {
            "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nユーザーの思考: {thought}"}]}],
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",  # 修正
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_HARASSMENT",   # 修正
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", # 修正
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT", # 修正
                    "threshold": "BLOCK_ONLY_HIGH"
                }
            ]
        }

        # Gemini API呼び出し
        response = requests.post(url, json=payload, timeout=25)
        
        if response.status_code != 200:
            print(f"Gemini API Error: {response.text}")
            return jsonify({"error": "Gemini API Error", "detail": response.text}), response.status_code

        result = response.json()

        # セーフティフィルターチェック
        candidate = result.get('candidates', [{}])[0]
        finish_reason = candidate.get('finishReason')

        if finish_reason and finish_reason not in ["STOP", "MAX_TOKENS"]:
            return jsonify({"error": "Safety", "detail": finish_reason}), 200

        # AIのテキスト抽出
        try:
            ai_text = candidate['content']['parts'][0]['text']
            # Markdown（```json ... ```）の除去
            clean_json = ai_text.replace('```json', '').replace('```', '').strip()
            return jsonify(json.loads(clean_json))
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"Parsing error: {e}")
            return jsonify({"error": "Safety", "detail": "Invalid AI response format"}), 200

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": "Process Error", "detail": str(e)}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)