import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET', 'POST', 'OPTIONS'])
def home():
    if request.method == 'OPTIONS': return '', 200
    return jsonify({"status": "online", "message": "Backend is running!"})

if __name__ == '__main__':
    # Render対応の起動設定
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)