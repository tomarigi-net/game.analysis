import os
import json
import requests
import re
import time
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "[https://tomarigi-net.github.io](https://tomarigi-net.github.io)"}})

@app.route('/', methods=['GET', 'POST', 'OPTIONS', 'HEAD'], strict_slashes=False)
def home():
    if request.method == 'OPTIONS':
        return '', 200

    if request.method == 'HEAD':
        return '', 200

    if request.method == 'GET':
        return jsonify({"status": "online", "message": "Gemini 2.5 Flash Ready!"})

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=){api_key}"

    try:
        # POSTのときだけJSONを読む
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Empty payload"}), 400

        # バックエンド側での簡易パスワード認証
        password = data.get('password', '').strip()
        if password != "okok":
            return jsonify({"error": "Unauthorized", "detail": "認証パスワードが一致しません。"}), 403

        thought = data.get('thought', '').strip()
        mode = data.get('mode', 'strict')

        print("MODE:", mode, flush=True)

        if not thought:
            return jsonify({"error": "Empty input"}), 200

        with open("prompt.txt", "r", encoding="utf-8") as f:
            base_prompt = f.read()

        # 36種類限定モードの場合、分析後の照合を強調
        if mode == "strict":
            game_list = [
                "1.Alcoholic = IND + DEP + REP",
                "2.Debtor = DYA + DEP + LOCK",
                "3.KickMe = IND + REW + REP",
                "4.NowI'veGotYou = DYA + CON + LOCK",
                "5.SeeWhatYouMadeMeDo = DYA + DEF + FLIP",
                "6.Corner = DYA + OPN + LOCK",
                "7.Courtroom = GRP + CON + SPIL",
                "8.FrigidWoman = DYA + CTRL + REP",
                "9.Harried = IND + ESC + REP",
                "10.IfItWeren'tForYou = DYA + DEF + REP",
                "11.LookHowHardI'veTried = IND + DEF + LOOP",
                "12.Sweetheart = DYA + CTRL + FLIP",
                "13.Ain'tItAwful = GRP + REW + SPIL",
                "14.Blemish = DYA + CON + REP",
                "15.Schlemiel = DYA + DEF + LOOP",
                "16.WhyDon'tYouYesBut = DYA + INV + LOOP",
                "17.Let'sYouAndHimFight = TRI + CTRL + SPIL",
                "18.Perversion = DYA + CTRL + FLIP",
                "19.Rapo = DYA + CTRL + FLIP",
                "20.StockingGame = IND + REW + LOOP",
                "21.Uproar = GRP + ESCAL + SPIL",
                "22.CopsAndRobbers = DYA + CON + LOOP",
                "23.HowDoYouGetOut = DYA + OPN + LOCK",
                "24.FastOneOnJoey = GRP + CTRL + FLIP",
                "25.Greenhouse = DYA + CTRL + LOCK",
                "26.ImOnlyTryingToHelp = DYA + INV + DEF",
                "27.Indigence = IND + DEP + LOCK",
                "28.Peasant = DYA + CTRL + DEF",
                "29.Psychiatry = DYA + CTRL + LOCK",
                "30.Stupid = IND + DEF + REP",
                "31.WoodenLeg = IND + DEF + LOCK",
                "32.BusmansHoliday = IND + ESC + LOOP",
                "33.Cavalier = IND + ESC + REP",
                "34.HappyToHelp = DYA + INV + REW",
                "35.HomelySage = DYA + CTRL + REW",
                "36.TheyllBeGladTheyKnewMe = IND + DEF + FLIP"
            ]

            mode_instruction = f"""
【追加制約】
まず【分析プロセス】を完遂してください。その分析結果（仕掛けの質や相手の反応）に最も合致するゲーム名を、以下の「エリック・バーン原典36種類」から厳格に選択してください。
リスト：{game_list}
"""
        else:
            mode_instruction = """
【追加制約】
原典に縛られる必要はありません。分析プロセスから導き出されたダイナミクスを最優先してください。
エリック・バーンの36種類のリストに限定せず、現代の人間関係においてそのやり取りが持つ本質的な力学（ダイナミクス）を最も的確に言い表せる「現代的なゲーム名称」を自由に命名してください。
※回答は、簡潔かつ要点を絞ったJSON形式で出力してください。詳細な解説は最小限に留めてください。
"""

        prompt = (
            f"{base_prompt}\n{mode_instruction}\n\n"
            f"【分析対象】: {thought}\n\n"
            f"※必ず2つの異なる視点や解釈を含むJSON配列形式 [{{...}}, {{...}}] で出力してください。\n"
            f"※各要素には'probability'（分析モデルとの合致度: 0-100）と、分析プロセスに基づいた'reason_for_prob'を必ず含めてください。"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.15
            }
        }

        response = requests.post(url, json=payload, timeout=60)

        if response.status_code == 429:
            return jsonify({"error": "Rate Limit", "detail": "リクエスト制限中です。しばらくお待ちください。"}), 429

        if response.status_code != 200:
            return jsonify({"error": "API Error", "detail": response.text}), 502

        result = response.json()

        if 'candidates' in result and result['candidates']:
            ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            clean_text = re.sub(r'```json\s*|```', '', ai_text)

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
                return jsonify({"error": "Parse Error", "raw": clean_text}), 500
        else:
            return jsonify({"error": "No response from AI"}), 500

    except Exception as e:
        return jsonify({"error": "System error", "detail": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)