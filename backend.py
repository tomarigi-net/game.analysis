import os
import json
import requests
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://tomarigi-net.github.io"}})

@app.route('/', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def home():
    if request.method == 'OPTIONS':
        return '', 200
    if request.method == 'GET':
        return jsonify({"status": "online", "message": "Gemini 3 Flash Ready!"})

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    # モデル名は指定通り 2.5-flash を使用
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    try:
        data = request.get_json()
        thought = data.get('thought', '').strip() if data else ""
        mode = data.get('mode', 'strict') if data else 'strict'

        if not thought:
            return jsonify({"error": "Empty input"}), 200

        # prompt.txt の読み込み
        with open("prompt.txt", "r", encoding="utf-8") as f:
            base_prompt = f.read()
        
        mode_instruction = "\n【追加制約】ゲーム名称は必ずエリック・バーンの原典'Games People Play'にある公式名称36種類の中から選択してください。" if mode == "strict" else "\n【追加制約】原典に縛られず現代的な名称を自由に命名してください。"
        
        # --- 修正箇所：'probability' を「分析モデルへの合致度」として算出するよう指示を調整 ---
        prompt = (
            f"{base_prompt}\n{mode_instruction}\n\n"
            f"【分析対象】: {thought}\n\n"
            f"※必ず各要素に 'probability' (0-100の数値で示す分析モデルへの合致度) と 'reason_for_prob' (分析根拠のテキスト) を含めてください。\n"
            f"※必ず2つの解釈を含むJSON配列形式 [{{...}}, {{...}}] で出力してください。"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 429:
            return jsonify({"error": "Rate Limit", "detail": "リクエスト制限中です。しばらくお待ちください。"}), 429

        if response.status_code != 200:
            return jsonify({"error": "API Error", "detail": response.text}), 200

        result = response.json()
        
        if 'candidates' in result and result['candidates']:
            ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            clean_text = re.sub(r'```json\s*|```', '', ai_text)
            
            # 配列 [ ] と オブジェクト { } の両方に対応する抽出ロジック
            start_indices = [i for i in [clean_text.find('{'), clean_text.find('[')] if i != -1]
            end_indices = [i for i in [clean_text.rfind('}'), clean_text.rfind(']')] if i != -1]
            
            start_idx = min(start_indices) if start_indices else 0
            end_idx = max(end_indices) if end_indices else len(clean_text)
            
            if start_indices and end_indices:
                clean_text = clean_text[start_idx:end_idx+1]
            
            try:
                parsed_json = json.loads(clean_text)
                
                # 常に配列形式でフロントに返す
                if isinstance(parsed_json, dict):
                    parsed_json = [parsed_json]
                
                return jsonify(parsed_json)
            except json.JSONDecodeError:
                return jsonify({"error": "Parse Error", "raw": clean_text})
        else:
            return jsonify({"error": "No response from AI"}), 200

    except Exception as e:
        return jsonify({"error": "System error", "detail": str(e)}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)