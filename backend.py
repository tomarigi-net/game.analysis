import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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
    if request.method == 'OPTIONS':
        return '', 200
    
    if request.method == 'GET':
        return "CBT Backend is Online (Gemini 3 Mode)"

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent"

    try:
        data = request.get_json()
        thought = data.get('thought', '入力なし')

        payload = {
            "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nユーザーの思考: {thought}"}]}]
        }

        # API呼び出し
        response = requests.post(url, params={"key": api_key}, json=payload, timeout=25)
        
        # HTTPステータスが200以外（API側のエラーなど）の処理
        if response.status_code != 200:
            return jsonify({"error": "Gemini API Error", "detail": response.text}), response.status_code

        result = response.json()

        # 【修正ポイント1】セーフティフィルターによるブロックのチェック
        # Geminiが安全上の理由で回答を生成しなかった場合、finishReasonが"SAFETY"などになります
        candidate = result.get('candidates', [{}])[0]
        finish_reason = candidate.get('finishReason')

        if finish_reason and finish_reason != "STOP" and finish_reason != "MAX_TOKENS":
            # 500エラーにせず、正常なレスポンス(200)として"Safety"エラーを返す
            return jsonify({"error": "Safety", "detail": finish_reason}), 200

        # 【修正ポイント2】AIのテキスト抽出時の安全策
        try:
            ai_text = candidate['content']['parts'][0]['text']
        except (KeyError, IndexError):
            return jsonify({"error": "Safety", "detail": "No content generated"}), 200
        
        # Markdown（```json ... ```）の除去
        clean_json = ai_text.replace('```json', '').replace('```', '').strip()
        
        # JSONとして解析して返す（ここでもエラーが起きる可能性があるのでtry内）
        return jsonify(json.loads(clean_json))

    except Exception as e:
        # 【修正ポイント3】全ての予期せぬエラーも、フロントを壊さないよう200で「Safety」扱いにするか、
        # ログに詳細を残して安全なエラーを返します
        print(f"Server Error: {e}")
        return jsonify({"error": "Safety", "detail": "Process Error"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)