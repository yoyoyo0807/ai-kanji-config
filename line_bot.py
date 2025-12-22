import os
import re
import random
import json
from flask import Flask, request, abort, render_template, redirect, session
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# Googleライブラリ
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = Flask(__name__)
# Renderの環境変数 SECRET_KEY を使用（未設定時はデフォルト値）
app.secret_key = os.environ.get('SECRET_KEY', 'kanji-ai-secret-key-2025')

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- Google設定 ---
# Renderの環境変数 GOOGLE_CREDENTIALS_JSON から読み込む
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
        return """
        <html><head><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
        <body style="text-align:center; padding-top:50px; font-family:sans-serif; background:#f4f5f7;">
            <div style="background:white; margin:20px; padding:30px; border-radius:16px; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
                <h1 style="font-size:50px; margin:0;">😢</h1>
                <h2 style="color:#333;">了解いたしました！</h2>
                <p style="color:#666;">またの機会に誘ってくださいね。</p>
            </div>
        </body></html>
        """
    return render_template('select_method.html', title=title)

# --- 🚀 修正：外部ブラウザを強制起動する処理 ---
@app.route("/auth/google")
def auth_google():
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    
    # 認証URLを生成
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    
    # URLに「openExternalBrowser=1」を付与して、LINE内ブラウザではなくSafari/Chromeを起動させる
    separator = "&" if "?" in authorization_url else "?"
    external_url = f"{authorization_url}{separator}openExternalBrowser=1"
    
    return redirect(external_url)

@app.route("/callback/google")
def callback_google():
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    flow.fetch_token(authorization_response=request.url)
    
    # ここで成功画面を表示
    return """
    <html><head><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
    <body style="text-align:center; padding-top:50px; font-family:sans-serif; background:#f4f5f7;">
        <div style="background:white; margin:20px; padding:30px; border-radius:16px; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
            <h1 style="font-size:50px; margin:0;">✅</h1>
            <h2 style="color:#00b900;">連携成功！</h2>
            <p style="color:#666;">カレンダーの読み取りが完了しました。<br>ブラウザを閉じてLINEに戻ってください。</p>
        </div>
    </body></html>
    """

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # ここに調整結果の計算ロジックなどを後ほど拡張します
    pass

if __name__ == "__main__":
    app.run()
