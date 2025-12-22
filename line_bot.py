import os
import json
from flask import Flask, request, render_template, redirect
from google_auth_oauthlib.flow import Flow

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kanji-ai-2025')

# Google設定
google_creds_raw = os.environ.get('GOOGLE_CREDENTIALS_JSON')
CLIENT_CONFIG = json.loads(google_creds_raw) if google_creds_raw else {}
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/answer")
def answer():
    res = request.args.get('res')
    title = request.args.get('title', 'イベント')
    if res == 'no':
        return """<html><body style="text-align:center;padding-top:50px;"><h2>了解いたしました！</h2></body></html>"""
    return render_template('select_method.html', title=title)

@app.route("/auth/google")
def auth_google():
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    
    # 🚀 GoogleログインURLに外部ブラウザ指定を追加
    separator = "&" if "?" in authorization_url else "?"
    external_url = f"{authorization_url}{separator}openExternalBrowser=1"
    
    # 💡 redirect()ではなく、JSで外部ブラウザ起動を強制する中継ページを表示
    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width,initial-scale=1.0">
            <script>window.location.href = "{external_url}";</script>
        </head>
        <body style="text-align:center; padding-top:50px; font-family:sans-serif; background:#f4f5f7;">
            <div style="background:white; margin:20px; padding:30px; border-radius:16px; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
                <p>Googleログイン画面へ移動しています...</p>
                <p style="font-size:0.8rem; color:#888;">切り替わらない場合は以下をタップしてください</p>
                <a href="{external_url}" style="color:#00b900; font-weight:bold;">[ ログイン画面を開く ]</a>
            </div>
        </body>
    </html>
    """

@app.route("/callback/google")
def callback_google():
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google")
    flow.fetch_token(authorization_response=request.url)
    return """<html><body style="text-align:center;padding-top:50px;"><h2>✅ 連携成功！</h2><p>ブラウザを閉じてLINEに戻ってください。</p></body></html>"""

if __name__ == "__main__":
    app.run()
