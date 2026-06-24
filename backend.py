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
        
        # 36種類限定モードの場合、分析後の照合を強調
        if mode == "strict":
            game_list = "アルコール中毒者, 負債者, 私を蹴ってください, さあ捕まえたぞ, あなたが私にさせたことといったら, 追い詰め, 法廷, 冷感症の女, 苦労性, あなたさえいなければ, どんなに私が一生懸命やったか, 恋人, ひどいじゃありませんか, 欠点探し, 不手際, はいでも, あなたと彼を戦わせましょう, 倒側, ラポ, ストッキング・ゲーム, 大騒ぎ, 泥棒と警察, どうやってここを抜け出すか, ジョーイの奴に一杯食わせようや, 温室, 私はただあなたを助けようとしているのです, 貧乏, 農民, 精神医学, 馬鹿, 木製の義足, バス運転手の休日, 騎士, 喜んでお手伝いします, 素朴な賢人, 彼らは私を知っていたことを喜ぶでしょう"
            mode_instruction = f"""
【追加制約】
まず【分析プロセス】を完遂してください。その分析結果（仕掛けの質や相手の反応）に最も合致するゲーム名を、以下の「エリック・バーン原典36種類」から厳格に選択してください。
リスト：{game_list}
"""
        else:
            mode_instruction = "\n【追加制約】原典に縛られず、分析プロセスから導き出されたダイナミクスに最もふさわしい現代的な名称を自由に命名してください。"
        
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