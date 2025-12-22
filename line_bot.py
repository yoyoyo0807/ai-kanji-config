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
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key') # セッション用

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- Google設定 ---
google_creds_raw = os.environ.get('GOOGLE_CREDENTIALS_JSON')
CLIENT_CONFIG = json.loads(google_creds_raw) if google_creds_raw else {}
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# --- メイン画面 (幹事用) ---
@app.route("/")
def index():
    return render_template("index.html")

# --- 回答ページ (招待された友達が飛んでくる) ---
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
                <button onclick="window.close()" style="margin-top:20px; padding:10px 20px; border-radius:20px; border:none; background:#ccc;">閉じる</button>
            </div>
        </body></html>
        """
    return render_template('select_method.html', title=title)

# --- Google認証開始 ---
@app.route("/auth/google")
def auth_google():
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    return redirect(authorization_url)

# --- Google認証コールバック ---
@app.route("/callback/google")
def callback_google():
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    flow.fetch_token(authorization_response=request.url)
    
    # 本来はここでカレンダーを取得してDBへ保存しますが、まずは成功確認
    return """
    <html><head><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
    <body style="text-align:center; padding-top:50px; font-family:sans-serif; background:#f4f5f7;">
        <div style="background:white; margin:20px; padding:30px; border-radius:16px; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
            <h1 style="font-size:50px; margin:0;">✅</h1>
            <h2 style="color:#00b900;">連携成功！</h2>
            <p style="color:#666;">AIがあなたの空き時間を読み取りました。<br>この画面を閉じてお待ちください。</p>
            <button onclick="window.close()" style="margin-top:20px; padding:10px 20px; border-radius:20px; border:none; background:#00b900; color:white;">閉じる</button>
        </div>
    </body></html>
    """

# --- LINE Webhook ---
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
    # (既存の調整開始ロジック... そのまま残す)
    pass

if __name__ == "__main__":
    app.run()
