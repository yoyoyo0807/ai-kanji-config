import os
import json
import datetime
from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)
# Renderの環境変数から取得。未設定時のデフォルト値も設定。
app.secret_key = os.environ.get('SECRET_KEY', 'kanji-ai-secret-key-2025')

# Google設定
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

google_creds_raw = os.environ.get('GOOGLE_CREDENTIALS_JSON')
CLIENT_CONFIG = json.loads(google_creds_raw) if google_creds_raw else {}
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# ---------------------------------------------------------
# 1. メイン画面・回答分岐
# ---------------------------------------------------------

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

# ---------------------------------------------------------
# 2. 幹事専用：日程確定フロー
# ---------------------------------------------------------

@app.route("/fix_date")
def fix_date():
    """リッチメニューの『日程を確定する』ボタンから呼ばれる画面"""
    title = request.args.get('title', 'イベント')
    # 本来はDBから回答データを集計しますが、現在はテンプレート側のデモデータを表示
    return render_template('fix_date.html', title=title)

@app.route("/submit_fix", methods=["POST"])
def submit_fix():
    """日程確定画面から送信された決定内容を処理する"""
    data = request.json
    selected_date = data.get('date')
    selected_time = data.get('time')
    # ここにMessaging APIを使ってLINEグループに「決定通知」を送るロジックを将来的に追加
    print(f"日程が確定されました: {selected_date} {selected_time}")
    return json.dumps({"status": "success"})

# ---------------------------------------------------------
# 3. Google OAuth 連携
# ---------------------------------------------------------

@app.route("/auth/google")
def auth_google():
    title = request.args.get('title', 'イベント')
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline', 
        include_granted_scopes='true',
        state=title
    )
    
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
    title = request.args.get('state', 'イベント')
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    flow.fetch_token(authorization_response=request.url)
    
    creds = flow.credentials
    service = build('calendar', 'v3', credentials=creds)
    
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=14)).isoformat() + 'Z'
    
    events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=time_max,
                                        singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    busy_slots = []
    for event in events:
        start_raw = event['start'].get('dateTime', event['start'].get('date'))
        if 'T' in start_raw:
            dt_key = start_raw[:10] + "_" + start_raw[11:16]
            busy_slots.append(dt_key)
        else:
            busy_slots.append(start_raw[:10] + "_ALLDAY")

    return render_template('google_result.html', title=title, busy_slots=busy_slots)

# ---------------------------------------------------------
# 4. Google審査対応：法的ページ
# ---------------------------------------------------------

@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

# ---------------------------------------------------------
# 実行
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run()
