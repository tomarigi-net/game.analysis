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
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"

    try:
        data = request.get_json()
        thought = data.get('thought', '').strip() if data else ""
        mode = data.get('mode', 'strict') if data else 'strict'

        if not thought:
            return jsonify({"error": "Empty input"}), 200

        # prompt.txt の読み込み
        with open("prompt.txt", "r", encoding="utf-8") as f:
            base_prompt = f.read()
        
        # 36種類限定モードの場合、リストを提示しつつ「分析後の照合」を強調する
        if mode == "strict":
            game_list = (
    "1.Alcoholic(自滅と救済の反復), 2.Debtor(負債による束縛と依存), 3.Kick Me(拒絶を誘う自虐的行動), 4.Now I've Got You, You Son of a Bitch(失態を待ち構えた正当な怒り), 5.See What You Made Me Do(失敗の責任転嫁), 6.Corner(逃げ道のない二重拘束), 7.Courtroom(第3者の前での非難合戦), 8.Frigid Woman(性的誘惑とその後の道徳的拒絶), 9.Harried(多忙による自滅と非難回避), 10.If It Weren't For You(相手を口実にした挑戦回避), 11.Look How Hard I've Tried(努力の強調と無力感の証明), 12.Sweetheart(皮肉まじりの偽りの賞賛), 13.Ain't It Awful(不幸の嘆きと連帯感の強要), 14.Blemish(些浅な欠点探しによる優越), 15.Schlemiel(失敗と謝罪による許しの強要), 16.Why Don't You - Yes But(助言の拒絶による知的優位), 17.Let's You and Him Fight(対立の煽り立てと傍観), 18.Perversion(心理的・性的倒錯), 19.Rapo(誘惑と劇的な拒絶), 20.Stocking Game(性的魅力による注目収集), 21.Uproar(激しい衝突による親密さの回避), 22.Cops and Robbers(発覚のスリルと捕獲の誘発), 23.How Do You Get Out of Here?(出口のない関係性の演出), 24.Let's Pull a Fast One on Joey(他者を出し抜く共謀), 25.Greenhouse(理屈による感情の封じ込め), 26.I'm Only Trying to Help You(善意の押し売りと無力感), 27.Indigence(無力・貧困を理由にした依存), 28.Peasant(無知を装った他者操作), 29.Psychiatry(診断名や用語による変化の拒絶), 30.Stupid(無能を演じた責任回避), 31.Wooden Leg(ハンデを理由にした免責), 32.Busman's Holiday(休息の場での仕事への固執), 33.Cavalier(軽薄さによる真剣な関わりの回避), 34.Happy to Help(過剰な支援による心理的優位), 35.Homely Sage(教示的態度による優越), 36.They'll Be Glad They Knew Me(将来の報復を夢見た自己正当化)"
)
            mode_instruction = f"""
【追加制約】
まず【分析プロセス】を完遂してください。その分析結果（仕掛けの質や相手の反応）に最も合致するゲーム名を、以下の「エリック・バーン原典36種類」から厳格に選択してください。
該当するものがないと感じる場合でも、プロセスの分析結果に最も近い構造を持つものをこの中から一つ選んでください。
リスト：{game_list}
"""
        else:
            mode_instruction = "\n【追加制約】原典に縛られず、分析プロセスから導き出されたダイナミクスに最もふさわしい現代的な名称を自由に命名してください。"

        # --- フロントエンド（index.html）の要求するJSON構造に100%完全同調させる指示 ---
        prompt = (
            f"{base_prompt}\n{mode_instruction}\n\n"
            f"【分析対象】: {thought}\n\n"
            f"※必ず2つの異なる視点や解釈を含むJSON配列形式 [{{...}}, {{...}}] で出力してください。\n"
            f"※各要素（オブジェクト）には、フロントエンドが表示処理を行えるよう、以下のキー（フィールド）を「必ず」漏れなく含めてください。英数字のキー名は完全に一致させてください：\n"
            f"1. 'game_name': 判定された心理ゲームの日本語名称。\n"
            f"2. 'english_name': 判定された心理ゲームの英語名称（例: 'Why Don't You - Yes But' や 'Kick Me' など、strictモードの場合は原典の英語表記を正確に。自由モードの場合は適切な英語を命名）。\n"
            f"3. 'probability': 入力内容がその心理ゲームの特徴とどれだけ一致するかを0-100の数値で示す「分析モデルへの合致度」（整数値のみ）。\n"
            f"4. 'reason_for_prob': なぜそのゲームと判定したのか。入力文内の具体的な描写を引用した分析の根拠・解説。\n"
            f"5. 'definition': その心理ゲームが持つ一般的な定義や特徴の解説。\n"
            f"6. 'scenario': 今回の入力内容における、やり取りの心理的要約。\n"
            f"7. 'prediction': このままゲームを進めた場合に予測される、残酷で破綻した結末のシナリオ。\n"
            f"8. 'hidden_motive': このゲームを演じることで当事者が無意識に得ようとしている「利得（真実）」。\n"
            f"9. 'advice': この心理ゲームを根本から回避するための具体的な対応策やアドバイス。\n"
            f"10. 'counseling': 当事者の心に寄り嘘う、今後のための「心の処方箋」メッセージ。\n"
            f"11. 'subject_name': 分析の主軸となっている人物（例: '自分'、'部下' など）。\n"
            f"12. 'position_start': 開始時の立ち位置オブジェクト。以下の3つのキーを必ず含むこと：\n"
            f"    - 'self': 自分のOK牧場の状態（'OK' または 'not OK'）\n"
            f"    - 'others': 相手のOK牧場の状態（'OK' または 'not OK'）\n"
            f"    - 'description