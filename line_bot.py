import os
import json
import datetime
from flask import Flask, request, render_template, redirect
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

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
        return """<html><body style="text-align:center;padding-top:50px;font-family:sans-serif;"><h2>了解いたしました！</h2></body></html>"""
    return render_template('select_method.html', title=title)

@app.route("/auth/google")
def auth_google():
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google")
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    
    # LINEの外部ブラウザ起動フラグを付与
    separator = "&" if "?" in authorization_url else "?"
    external_url = f"{authorization_url}{separator}openExternalBrowser=1"
    
    return f"""<html><head><script>window.location.href = "{external_url}";</script></head>
               <body style="text-align:center;padding-top:50px;font-family:sans-serif;">移動中...</body></html>"""

@app.route("/callback/google")
def callback_google():
    # 1. 認証トークンの取得
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google")
    flow.fetch_token(authorization_response=request.url)
    
    # 2. Googleカレンダーから予定を取得
    creds = flow.credentials
    service = build('calendar', 'v3', credentials=creds)
    
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    # 向こう10日間の予定を取得
    time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=10)).isoformat() + 'Z'
    
    events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=time_max,
                                        singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    # 3. 予定リストのHTML作成
    event_items_html = ""
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        # 表示用に時間を整形 (例: 12-22 10:00)
        time_str = start[5:16].replace('T', ' ')
        summary = event.get('summary', '（予定なし）')
        event_items_html += f"<li><span class='ev-time'>{time_str}</span> <span class='ev-title'>{summary}</span></li>"

    if not event_items_html:
        event_items_html = "<li>直近の予定はありません</li>"

    # 4. 確認画面の表示
    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width,initial-scale=1.0">
            <style>
                body {{ font-family: sans-serif; background: #f4f5f7; padding: 15px; margin: 0; color: #333; }}
                .container {{ background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 400px; margin: auto; }}
                h2 {{ color: #00b900; margin-top: 0; text-align: center; }}
                .event-box {{ background: #f9f9f9; border-radius: 12px; padding: 15px; margin: 15px 0; max-height: 200px; overflow-y: auto; text-align: left; border: 1px solid #eee; }}
                ul {{ list-style: none; padding: 0; margin: 0; }}
                li {{ padding: 8px 0; border-bottom: 1px solid #eee; font-size: 0.9rem; }}
                .ev-time {{ color: #888; margin-right: 10px; font-weight: bold; }}
                .privacy-card {{ background: #f0fff0; border: 2px solid #00b900; border-radius: 15px; padding: 15px; margin: 20px 0; text-align: left; }}
                .btn-confirm {{ display: block; width: 100%; padding: 18px; background: #00b900; color: white; border: none; border-radius: 35px; font-weight: bold; font-size: 1.1rem; cursor: pointer; box-shadow: 0 4px 10px rgba(0,185,0,0.3); }}
                label {{ display: block; margin: 10px 0; cursor: pointer; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>📅 予定の確認</h2>
                <p style="font-size:0.9rem;">カレンダーから以下の予定が見つかりました。これをもとに空き時間を計算します。</p>
                
                <div class="event-box">
                    <ul>{event_items_html}</ul>
                </div>

                <div class="privacy-card">
                    <strong style="color:#00b900;">🛡️ プライバシー保護</strong>
                    <label>
                        <input type="radio" name="p_mode" value="on" checked> 
                        <b>ON:</b> 内容を隠す（「予定あり」と共有）
                    </label>
                    <label>
                        <input type="radio" name="p_mode" value="off"> 
                        <b>OFF:</b> 内容も送る（幹事に詳細を伝える）
                    </label>
                </div>

                <button class="btn-confirm" onclick="confirmShare()">幹事に空き時間を送る</button>
            </div>

            <script>
                function confirmShare() {{
                    const mode = document.querySelector('input[name="p_mode"]:checked').value;
                    const msg = mode === 'on' ? "プライバシー保護を有効にして共有しました！" : "予定の詳細を含めて共有しました！";
                    alert(msg);
                    // 実際にはここでサーバーにデータを保存するリクエストを飛ばします
                    window.close();
                }}
            </script>
        </body>
    </html>
    """

if __name__ == "__main__":
    app.run()
