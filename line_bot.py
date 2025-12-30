import os
import json
import datetime
from flask import Flask, request, render_template, redirect
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kanji-ai-secret-key-2025')

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
    count = 1 
    if res == 'no':
        return """
        <html><body style="text-align:center; padding-top:50px; font-family:sans-serif; background:#f4f5f7;">
            <div style="background:white; margin:20px; padding:30px; border-radius:16px; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
                <h2>了解いたしました！</h2>
                <p>またの機会に誘ってくださいね。</p>
            </div>
        </body></html>
        """
    return render_template('select_method.html', title=title, count=count)

@app.route("/manual_input")
def manual_input():
    title = request.args.get('title', 'イベント')
    return render_template('manual_input.html', title=title)

@app.route("/auth/google")
def auth_google():
    # 審査対応：stateにタイトルなどを込めて認証後も引き継げるようにする
    title = request.args.get('title', 'イベント')
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    
    # stateパラメータを使用してコンテキストを保持
    authorization_url, state = flow.authorization_url(
        access_type='offline', 
        include_granted_scopes='true',
        state=title
    )
    
    # LINE外部ブラウザ対策
    separator = "&" if "?" in authorization_url else "?"
    external_url = f"{authorization_url}{separator}openExternalBrowser=1"
    
    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width,initial-scale=1.0">
            <script>window.location.href = "{external_url}";</script>
        </head>
        <body style="text-align:center; padding-top:50px; font-family:sans-serif; background:#f4f5f7;">
            <p>Googleログイン画面へ移動しています...</p>
            <a href="{external_url}" style="color:#00b900;">自動で切り替わらない場合はこちら</a>
        </body>
    </html>
    """

@app.route("/callback/google")
def callback_google():
    title = request.args.get('state', 'イベント') # auth_googleから引き継いだタイトル
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    flow.fetch_token(authorization_response=request.url)
    
    creds = flow.credentials
    service = build('calendar', 'v3', credentials=creds)
    
    # 予定取得範囲
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=14)).isoformat() + 'Z'
    
    events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=time_max,
                                        singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    # --- 判定用データの作成 ---
    busy_slots = []
    for event in events:
        start_raw = event['start'].get('dateTime', event['start'].get('date'))
        # 日付と時間を判定しやすいキー（YYYY-MM-DD_HH:MM）に変換
        if 'T' in start_raw:
            dt_key = start_raw[:10] + "_" + start_raw[11:16]
            busy_slots.append(dt_key)
        else:
            # 終日の予定
            busy_slots.append(start_raw[:10] + "_ALLDAY")

    # 完成度向上のため、専用のテンプレートにデータを渡してレンダリング
    return render_template('google_result.html', 
                           title=title, 
                           busy_slots=busy_slots)

if __name__ == "__main__":
    app.run()
