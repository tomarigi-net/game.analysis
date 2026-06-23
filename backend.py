import os
import json
import requests
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# 開発・テスト用に許可設定を柔軟にしていますが、本番では元のURLに絞ってください
CORS(app) 

@app.route('/', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def home():
    if request.method == 'OPTIONS':
        return '', 200
    if request.method == 'GET':
        return jsonify({"status": "online", "message": "Gemini 1.5 Flash Ready!"})

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    # モデル名を安定版の 1.5-flash に修正
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    try:
        data = request.get_json()
        thought = data.get('thought', '').strip() if data else ""
        mode = data.get('mode', 'strict') if data else 'strict'

        if not thought:
            return jsonify({"error": "Empty input"}), 200

        with open("prompt.txt", "r", encoding="utf-8") as f:
            base_prompt = f.read()
        
        if mode == "strict":
            game_list = "1.Alcoholic(自滅と救済の反復), 2.Debtor(負債による束縛と依存), 3.Kick Me(拒絶を誘う自虐的行動), 4.Now I've Got You, You Son of a Bitch(失態を待ち構えた正当な怒り), 5.See What You Made Me Do(失敗の責任転嫁), 6.Corner(逃げ道のない二重拘束), 7.Courtroom(第3者の前での非難合戦), 8.Frigid Woman(性的誘惑とその後の道徳的拒絶), 9.Harried(多忙による自滅と非難回避), 10.If It Weren't For You(相手を口実にした挑戦回避), 11.Look How Hard I've Tried(努力の強調と無力感の証明), 12.Sweetheart(皮肉まじりの偽りの賞賛), 13.Ain't It Awful(不幸の嘆きと連帯感の強要), 14.Blemish(些浅な欠点探しによる優越), 15.Schlemiel(失敗と謝罪による許しの強要), 16.Why Don't You - Yes But(助言の拒絶による知的優位), 17.Let's You and Him Fight(対立の煽り立てと傍観), 18.Perversion(心理的・性的倒錯), 19.Rapo(誘惑と劇的な拒絶), 20.Stocking Game(性的魅力による注目収集), 21.Uproar(激しい衝突による親密さの回避), 22.Cops and Robbers(発覚のスリルと捕獲の誘発), 23.How Do You Get Out of Here?(出口のない関係性の演出), 24.Let's Pull a Fast One on Joey(他者を出し抜く共謀), 25.Greenhouse(理屈による感情の封じ込め), 26.I'm Only Trying to Help You(善意の押し売りと無力感), 27.Indigence(無力・貧困を理由にした依存), 28.Peasant(無知を装った他者操作), 29.Psychiatry(診断名や用語による変化の拒絶), 30.Stupid(無能を演じた責任回避), 31.Wooden Leg(ハンデを理由にした免責), 32.Busman's Holiday(休息の場での仕事への固執), 33.Cavalier(軽薄さによる真剣な関わりの回避), 34.Happy to Help(過剰な支援による心理的優位), 35.Homely Sage(教示的態度による優越), 36.They'll Be Glad They Knew Me(将来の報復を夢見た自己正当化)"
            mode_instruction = f"\n【厳格モード】必ず以下のリストから最も近い構造を持つゲーム名を1つ選んでください。\nリスト：{game_list}"
        else:
            mode_instruction = "\n【自由命名モード】分析結果に基づき、現代的な名称を自由に命名してください。"

        # システム指示を統合
        prompt = (
            f"{base_prompt}\n{mode_instruction}\n\n"
            f"【分析対象】: {thought}\n\n"
            "※必ず [{{...}}, {{...}}] という「2つの要素を持つJSON配列形式」のみを出力してください。"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        response = requests.post(url, json=payload, timeout=60)
        if response.status_code != 200:
            return jsonify({"error": "API Error", "detail": response.text}), response.status_code

        result = response.json()
        if 'candidates' in result and result['candidates']:
            ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            # JSON部分のみを抽出（念のため）
            match = re.search(r'\[\s*\{.*\}\s*\]', ai_text, re.DOTALL)
            if match:
                clean_text = match.group(0)
            else:
                clean_text = ai_text

            parsed_json = json.loads(clean_text)
            return jsonify(parsed_json)
        else:
            return jsonify({"error": "No response from AI"}), 200

    except Exception as e:
        return jsonify({"error": "System error", "detail": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)