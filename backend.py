import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# すべてのオリジンを許可（CORSエラー防止）
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
    # フォールバック用プロンプト：JSON構造をAIに再提示して安定させます
    return "あなたは優秀な交流分析カウンセラーです。必ず以下のJSON形式で回答してください: { 'game_name': '', 'definition': '', 'position_start': {'self': '', 'others': '', 'description': ''}, 'position_end': {'self': '', 'others': '', 'description': ''}, 'prediction': '', 'hidden_motive': '', 'advice': '' }"

SYSTEM_PROMPT = get_prompt()

@app.route('/', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def home():
    if request.method == 'OPTIONS':
        return '', 200
    
    if request.method == 'GET':
        return "CBT Backend is Online (Gemini 3 Mode)"

    # API設定：バージョンは変えず gemini-3-flash-preview を維持
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"

    try:
        # 生データの取得と解析
        raw_data = request.data.decode('utf-8')
        try:
            data = json.loads(raw_data) if raw_data else {}
        except json.JSONDecodeError:
            data = request.form.to_dict() if request.form else {}

        thought = data.get('thought', '').strip()
        if not thought:
             return jsonify({"error": "Empty input", "detail": "内容が入力されていません"}), 200

        # ペイロード作成：バージョン変更なし
        payload = {
            "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nユーザーの思考: {thought}"}]}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
            ]
        }

        # タイムアウトを少し長めに設定してAPI呼び出し
        response = requests.post(url, json=payload, timeout=25)
        
        # サーバーエラー（500系）でもJSONを返すようにしてフロントを落とさない
        if response.status_code != 200:
            return jsonify({"error": "Gemini API Error", "detail": "AIサーバー側で問題が発生しました"}), 200

        result = response.json()

        # セーフティチェック
        candidates = result.get('candidates', [{}])
        if not candidates or 'content' not in candidates[0]:
            finish_reason = candidates[0].get('finishReason', 'UNKNOWN')
            return jsonify({"error": "Safety", "detail": f"AIにより制限されました: {finish_reason}"}), 200

        candidate = candidates[0]
        
        # AIテキスト抽出とクリーンアップ
        try:
            ai_text = candidate['content']['parts'][0]['text']
            # JSON以外のゴミ（Markdownタグなど）を徹底排除
            clean_json = ai_text.replace('```json', '').replace('```', '').strip()
            
            # パースできるかチェック
            final_data = json.loads(clean_json)
            return jsonify(final_data)

        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"Parse/Format Error: {e}")
            return jsonify({"error": "Format error", "detail": "AIの回答が正しいJSON形式ではありませんでした"}), 200

    except Exception as e:
        print(f"Fatal Server Error: {e}")
        return jsonify({"error": "Process Error", "detail": "分析中に予期せぬエラーが発生しました"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)