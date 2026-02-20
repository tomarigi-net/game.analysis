@app.route('/', methods=['GET', 'POST', 'OPTIONS'], strict_slashes=False)
def home():
    if request.method == 'OPTIONS':
        return '', 200
    
    if request.method == 'GET':
        return "CBT Backend is Online"

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent"

    try:
        # 【修正！】force=Trueを入れることで、ヘッダーが不完全でもJSONとして読み込みます
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "No Data", "detail": "JSONの読み込みに失敗しました"}), 400
            
        thought = data.get('thought', '入力なし')

        payload = {
            "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nユーザーの思考: {thought}"}]}],
            "safetySettings": [
                {"category": "HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
            ]
        }

        # API呼び出し
        response = requests.post(url, params={"key": api_key}, json=payload, timeout=25)
        
        # もしGoogle側から400が返ってきた場合、内容をログに出す
        if response.status_code != 200:
            print(f"Gemini API Error Response: {response.text}")
            return jsonify({"error": "Gemini API Error", "detail": response.text}), response.status_code

        result = response.json()
        candidate = result.get('candidates', [{}])[0]
        
        # AIの回答抽出（安全装置）
        try:
            ai_text = candidate['content']['parts'][0]['text']
        except (KeyError, IndexError):
            return jsonify({"error": "Safety", "detail": "内容を生成できませんでした"}), 200
        
        # 余計な文字を消してJSONとして返す
        clean_json = ai_text.replace('```json', '').replace('```', '').strip()
        return jsonify(json.loads(clean_json))

    except Exception as e:
        print(f"Internal Server Error: {str(e)}")
        return jsonify({"error": "Server Error", "detail": str(e)}), 500