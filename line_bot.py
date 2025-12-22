import os
import re
import json
from flask import Flask, request, abort, render_template, redirect
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google_auth_oauthlib.flow import Flow

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kanji-ai-2025')

line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

# Google設定
CLIENT_CONFIG = json.loads(os.environ.get('GOOGLE_CREDENTIALS_JSON'))
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/answer")
def answer():
    res = request.args.get('res')
    title = request.args.get('title', 'イベント')
    if res == 'no':
        return """<html><body style="text-align:center;padding-top:50px;font-family:sans-serif;"><h2>了解いたしました！</h2></body></html>"""
    return render_template('select_method.html', title=title)

@app.route("/auth/google")
def auth_google():
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    
    # 🚀 URLに強制起動フラグを付与
    separator = "&" if "?" in authorization_url else "?"
    external_url = f"{authorization_url}{separator}openExternalBrowser=1"
    
    # JSでSafari/Chromeを強制起動する中継画面
    return f"""
    <html>
        <head><meta name="viewport" content="width=device-width,initial-scale=1.0">
        <script>window.location.href = "{external_url}";</script></head>
        <body style="text-align:center;padding-top:50px;font-family:sans-serif;">
            <p>Googleログイン画面へ移動しています...</p>
            <a href="{external_url}">切り替わらない場合はこちら</a>
        </body>
    </html>
    """

@app.route("/callback/google")
def callback_google():
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google")
    flow.fetch_token(authorization_response=request.url)
    return """<html><body style="text-align:center;padding-top:50px;font-family:sans-serif;"><h2>✅ 連携成功！</h2><p>ブラウザを閉じてLINEに戻ってください。</p></body></html>"""

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

if __name__ == "__main__":
    app.run()
