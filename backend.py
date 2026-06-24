import os
import json
import requests
import re
import time
import traceback
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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    try:
        data = request.get_json()
        thought = data.get('thought', '').strip() if data else ""
        mode = data.get('mode', 'strict') if data else 'strict'

        print("MODE:", mode, flush=True)

        if not thought:
            return jsonify({"error": "Empty input"}), 200

        with open("prompt.txt", "r", encoding="utf-8") as f:
            base_prompt = f.read()

        if mode == "strict":
            game_list = "1.Alcoholic, 2.Debtor, 3.Kick Me, 4.Now I've Got You, You Son of a Bitch, 5.See What You Made Me Do, 6.Corner, 7.Courtroom, 8.Frigid Woman, 9.Harried, 10.If It Weren't For You, 11.Look How Hard I've Tried, 12.Sweetheart, 13.Ain't It Awful, 14.Blemish, 15.Schlemiel, 16.Why Don't You - Yes But, 17.Let's You and Him Fight, 18.Perversion, 19.Rapo, 20.Stocking Game, 21.Uproar, 22.Cops and Robbers, 23.How Do You Get Out of Here?, 24.Let's Pull a Fast One on Joey, 25.Greenhouse, 26.I'm Only Trying to Help You, 27.Indigence, 28.Peasant, 29.Psychiatry, 30.Stupid, 31.Wooden Leg, 32.Busman's Holiday, 33.Cavalier, 34.Happy to Help, 35.Homely Sage, 36.They'll Be Glad They Knew Me"
            mode_instruction = f"""
【追加制約】
分析結果に最も合致するゲーム名を以下から選んでください。
リスト：{game_list}
"""
        else:
            mode_instruction = """
【追加制約】
原典に縛られず、現代的なゲーム名称を自由に命名してください。
必ず厳密なJSONのみを返してください。
"""

        prompt = (
            f"{base_prompt}\n{mode_instruction}\n\n"
            f"【分析対象】: {thought}\n\n"
            f"※必ずJSON配列形式 [{{...}}, {{...}}] で出力してください。"
        )

        print("PROMPT LENGTH:", len(prompt), flush=True)

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.15
            }
        }

        response = requests.post(url, json=payload, timeout=60)
        time.sleep(0.3)

        print("STATUS:", response.status_code, flush=True)
        print("BODY:", response.text[:1000], flush=True)

        if response.status_code == 429:
            return jsonify({"error": "Rate Limit"}), 429

        if response.status_code != 200:
            return jsonify({"error": "API Error", "detail": response.text}), 502

        result = response.json()
        print("RESULT JSON:", result, flush=True)

        if 'candidates' in result and result['candidates']:
            candidate = result['candidates'][0]
            print("CANDIDATE:", candidate, flush=True)

            if 'content' not in candidate:
                return jsonify({
                    "error": "No content",
                    "raw": candidate
                }), 500

            ai_text = candidate['content']['parts'][0]['text'].strip()
            print("AI_TEXT:", ai_text[:1000], flush=True)

            clean_text = re.sub(r'```json\s*|```', '', ai_text)

            start_indices = [i for i in [clean_text.find('{'), clean_text.find('[')] if i != -1]
            end_indices = [i for i in [clean_text.rfind('}'), clean_text.rfind(']')] if i != -1]

            start_idx = min(start_indices) if start_indices else 0
            end_idx = max(end_indices) if end_indices else len(clean_text)

            if start_indices and end_indices:
                clean_text = clean_text[start_idx:end_idx+1]

            try:
                parsed_json = json.loads(clean_text)

                if isinstance(parsed_json, dict):
                    parsed_json = [parsed_json]

                return jsonify(parsed_json)

            except json.JSONDecodeError as e:
                print("PARSE ERROR:", str(e), flush=True)
                print("RAW:", clean_text, flush=True)
                return jsonify({"error": "Parse Error", "raw": clean_text}), 500
        else:
            return jsonify({"error": "No response from AI"}), 500

    except Exception as e:
        traceback.print_exc()
        print("SYSTEM ERROR:", repr(e), flush=True)
        return jsonify({"error": "System error", "detail": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)