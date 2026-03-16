import os
import json
import requests
import re
import time
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://tomarigi-net.github.io"}})

# --- Gemini呼び出し関数（429リトライ対応） ---
def call_gemini_api(prompt, api_key, max_retries=3):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2
        }
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                wait_time = 2 ** attempt  # 2,4,8秒バックオフ
                print(f"[Retry] 429 Rate Limit - Waiting {wait_time}s (Attempt {attempt+1})")
                time.sleep(wait_time)
            else:
                return {"error": "API Error", "detail": response.text}
        except requests.exceptions.RequestException as e:
            wait_time = 2 ** attempt
            print(f"[Retry] Request Exception: {e} - Waiting {wait_time}s (Attempt {attempt+1})")
            time.sleep(wait_time)
    return {"error": "Rate Limit", "detail": "リクエスト制限中です。しばらくお待ちください。"}

# --- Flaskルート ---
@app.route('/', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def home():
    if request.method == 'OPTIONS':
        return '', 200
    if request.method == 'GET':
        return jsonify({"status": "online", "message": "Gemini 2.5 Flash Ready!"})

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "API Key not set"}), 500

    data = request.get_json()
    thought = data.get('thought', '').strip() if data else ""
    mode = data.get('mode', 'strict') if data else 'strict'

    if not thought:
        return jsonify({"error": "Empty input"}), 200

    # prompt.txt の読み込み
    try:
        with open("prompt.txt", "r", encoding="utf-8") as f:
            base_prompt = f.read()
    except Exception as e:
        return jsonify({"error": "System error", "detail": f"prompt.txt読み込み失敗: {str(e)}"}), 500

    mode_instruction = "\n【追加制約】ゲーム名称は必ずエリック・バーンの原典'Games People Play'にある公式名称36種類の中から選択してください。" if mode == "strict" else "\n【追加制約】原典に縛られず現代的な名称を自由に命名してください。"
    
    prompt = f"{base_prompt}\n{mode_instruction}\n\n【分析対象】: {thought}"

    # --- Gemini API呼び出し ---
    result = call_gemini_api(prompt, api_key, max_retries=3)

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
            return jsonify({"error": "Parse Error", "raw": clean_text})
    else:
        return jsonify(result)

# --- Renderポート設定 ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)