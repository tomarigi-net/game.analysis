import os
import json
import requests
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET', 'POST'])
def home():

```
if request.method == 'GET':
    return jsonify({"status": "online"})

try:
    data = request.get_json()
    thought = data.get("thought", "")
    mode = data.get("mode", "strict")

    if not thought:
        return jsonify({"error": "Empty input"}), 200

    with open("prompt.txt", "r", encoding="utf-8") as f:
        base_prompt = f.read()

    # 36ゲームリスト
    game_list = [
        "Alcoholic","Debtor","KickMe","NowI'veGotYou",
        "SeeWhatYouMadeMeDo","Corner","Courtroom",
        "FrigidWoman","Harried","IfItWeren'tForYou",
        "LookHowHardI'veTried","Sweetheart","Ain'tItAwful",
        "Blemish","Schlemiel","WhyDon'tYouYesBut",
        "Let'sYouAndHimFight","Perversion","Rapo",
        "StockingGame","Uproar","CopsAndRobbers",
        "HowDoYouGetOut","FastOneOnJoey","Greenhouse",
        "ImOnlyTryingToHelp","Indigence","Peasant",
        "Psychiatry","Stupid","WoodenLeg",
        "BusmansHoliday","Cavalier","HappyToHelp",
        "HomelySage","TheyllBeGladTheyKnewMe"
    ]

    if mode == "strict":
        mode_instruction = f"""
```

【追加制約】
必ず以下の36ゲームから選択：
{game_list}
必ず2候補提示すること。
"""
else:
mode_instruction = "自由命名可"

````
    prompt = f"{base_prompt}\n{mode_instruction}\n\n分析対象:\n{thought}"

    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2
        }
    }

    response = requests.post(url, json=payload, timeout=60)

    if response.status_code != 200:
        return jsonify({"error": response.text}), 500

    result = response.json()
    text = result['candidates'][0]['content']['parts'][0]['text']

    clean = re.sub(r'```json|```', '', text).strip()

    parsed = json.loads(clean)

    if isinstance(parsed, dict):
        parsed = [parsed]

    return jsonify(parsed)

except Exception as e:
    return jsonify({"error": str(e)}), 500
````

if __name__ == "__main__":
port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
