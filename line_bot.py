import os
import json
import datetime
from flask import Flask, request, render_template, redirect
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = Flask(__name__)
# Renderの環境変数 SECRET_KEY を使用
app.secret_key = os.environ.get('SECRET_KEY', 'kanji-ai-2025')

# Google OAuth設定
google_creds_raw = os.environ.get('GOOGLE_CREDENTIALS_JSON')
CLIENT_CONFIG = json.loads(google_creds_raw) if google_creds_raw else {}
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

@app.route("/")
def index():
    return render_template("index.html")

# --- 回答方法選択画面 ---
@app.route("/answer")
def answer():
    # URLパラメータから情報を取得してテンプレートに渡す
    title = request.args.get('title', 'イベント')
    start = request.args.get('start', '') # 開催期間（開始）
    end = request.args.get('end', '')     # 開催期間（終了）
    res = request.args.get('res')
    
    if res == 'no':
        return """
        <html><body style="text-align:center;padding-top:50px;font-family:sans-serif;background:#f4f5f7;">
            <div style="background:white;margin:20px;padding:30px;border-radius:16px;">
                <h2>了解いたしました！</h2>
                <p>またの機会によろしくお願いします。</p>
            </div>
        </body></html>
        """
    # select_method.html に日付データを引き継ぐ
    return render_template('select_method.html', title=title, start=start, end=end)

# --- 手動入力画面 ---
@app.route("/manual_input")
def manual_input():
    return render_template('manual_input.html')

# --- Google OAuth認証開始 ---
@app.route("/auth/google")
def auth_google():
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    
    # 外部ブラウザ強制起動フラグを付与
    separator = "&" if "?" in authorization_url else "?"
    external_url = f"{authorization_url}{separator}openExternalBrowser=1"
    
    # JavaScriptで外部ブラウザへリダイレクト
    return f"""
    <html><head><script>window.location.href = "{external_url}";</script></head>
    <body style="text-align:center;padding-top:50px;">Googleログイン画面へ移動中...</body></html>
    """

# --- Google OAuthコールバック & 予定表示 ---
@app.route("/callback/google")
def callback_google():
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    flow.fetch_token(authorization_response=request.url)
    
    # Google Calendar APIから予定を取得
    service = build('calendar', 'v3', credentials=flow.credentials)
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + 'Z'
    
    events_result = service.events().list(
        calendarId='primary', timeMin=now, timeMax=time_max,
        singleEvents=True, orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    # 予定のリストをHTML用に整形（開始〜終了時間を表示）
    event_items_html = ""
    for event in events:
        start_raw = event['start'].get('dateTime', event['start'].get('date'))
        end_raw = event['end'].get('dateTime', event['end'].get('date'))
        
        # 2025-12-22T19:00:00 -> 12/22 19:00
        date_str = start_raw[5:10].replace('-', '/')
        start_time = start_raw[11:16] if 'T' in start_raw else "終日"
        end_time = end_raw[11:16] if 'T' in end_raw else ""
        
        time_display = f"{start_time} - {end_time}" if end_time else start_time
        summary = event.get('summary', '予定あり')
        
        event_items_html += f"<li><span style='color:#888;'>{date_str}</span> <b>{time_display}</b>: {summary}</li>"

    if not event_items_html:
        event_items_html = "<li>直近の予定は見つかりませんでした。</li>"

    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width,initial-scale=1.0">
            <style>
                body {{ font-family: sans-serif; background: #f4f5f7; padding: 15px; text-align: center; }}
                .card {{ background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 400px; margin: auto; }}
                .event-box {{ background: #f9f9f9; border-radius: 12px; padding: 15px; margin: 15px 0; max-height: 200px; overflow-y: auto; text-align: left; font-size: 0.85rem; border: 1px solid #eee; }}
                ul {{ list-style: none; padding: 0; }}
                li {{ padding: 5px 0; border-bottom: 1px solid #eee; }}
                .btn-confirm {{ display: block; width: 100%; padding: 18px; background: #00b900; color: white; border: none; border-radius: 35px; font-weight: bold; font-size: 1.1rem; cursor: pointer; }}
                .privacy-note {{ font-size: 0.8rem; color: #666; margin: 15px 0; text-align: left; background: #fffde7; padding: 10px; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2 style="color:#00b900;margin-top:0;">📅 予定を確認しました</h2>
                <div class="event-box"><ul>{event_items_html}</ul></div>
                <div class="privacy-note">
                    🛡️ <b>プライバシー保護</b><br>
                    幹事には「いつが空いているか」という計算結果だけが送られます。予定の内容（例：{events[0].get('summary') if events else '会議'}）は送信されません。
                </div>
                <button class="btn-confirm" onclick="alert('空き時間を送信しました！'); window.close();">この内容で空き時間を送る</button>
            </div>
        </body>
    </html>
    """

if __name__ == "__main__":
    app.run()
