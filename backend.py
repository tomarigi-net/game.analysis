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

@app.route('/', methods=['GET', 'POST', 'OPTIONS', 'HEAD'], strict_slashes=False)
def home():

    if request.method == 'OPTIONS':
        return '', 200

    if request.method == 'HEAD':
        return '', 200

    if request.method == 'GET':
        return jsonify({"status": "online", "message": "Gemini 2.5 Flash Ready!"})

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    try:
        # POSTのときだけJSONを読む
        data = request.get_json(silent=True)

        thought = data.get('thought', '').strip() if data else ""
        mode = data.get('mode', 'strict') if data else 'strict'

        print("MODE:", mode, flush=True)

        if not thought:
            return jsonify({"error": "Empty input"}), 200

        with open("prompt.txt", "r", encoding="utf-8") as f:
            base_prompt = f.read()

        # 36種類限定モードの場合、分析後の照合を強調
        if mode == "strict":
            game_list = """
1.Alcoholic(個人/依存/反復),
2.Debtor(相互/拘束/依存),
3.KickMe(個人/誘発拒絶/反復),
4.NowI'veGotYou(二者/捕獲/失点確定),
5.SeeWhatYouMadeMeDo(二者/転嫁/責任移動),
6.Corner(相互/閉塞/二重拘束),
7.Courtroom(集団/裁定/非難増幅),
8.FrigidWoman(二者/誘惑拒絶/反復),
9.Harried(個人/過負荷/回避),
10.IfItWeren'tForYou(二者/回避/依存正当化),
11.LookHowHardI'veTried(個人/証明/無力化),
12.Sweetheart(二者/皮肉優位/関係操作),
13.Ain'tItAwful(集団/共感拘束/不満拡散),
14.Blemish(二者/欠点捕獲/優越),
15.Schlemiel(二者/失敗誘発/許可獲得),
16.WhyDon'tYouYesBut(二者/助言拒否/優位維持),
17.Let'sYouAndHimFight(三者/対立誘導/傍観),
18.Perversion(二者/倒錯操作/混乱),
19.Rapo(二者/誘惑拒絶/劇化),
20.StockingGame(個人/注目獲得/誘惑),
21.Uproar(集団/拡散/エスカレーション),
22.CopsAndRobbers(二者/捕獲ゲーム/スリル),
23.HowDoYouGetOut(二者/閉塞/出口喪失),
24.FastOneOnJoey(共謀/出し抜き/裏操作),
25.Greenhouse(二者/理性支配/感情抑制),
26.ImOnlyTryingToHelp(二者/介入/無力化),
27.Indigence(個人/依存/無力化),
28.Peasant(二者/無知偽装/操作),
29.Psychiatry(二者/診断操作/固定化),
30.Stupid(個人/無能演出/回避),
31.WoodenLeg(個人/免責/正当化),
32.BusmansHoliday(個人/役割侵食/固執),
33.Cavalier(個人/回避/軽薄化),
34.HappyToHelp(二者/過剰支援/優位),
35.HomelySage(二者/教示/優位),
36.TheyllBeGladTheyKnewMe(個人/未来正当化/報復想像)
"""
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
                return jsonify({"error": "Parse Error", "raw": clean_text}), 500
        else:
            return jsonify({"error": "No response from AI"}), 500

    except Exception as e:
        return jsonify({"error": "System error", "detail": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)