import os
import json
import datetime
from flask import Flask, request, render_template, redirect
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = Flask(__name__)
# Renderの環境変数から取得。未設定時のデフォルト値も設定。
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
    # データベース未実装のため、現在は統計を仮で1名として表示
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
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    
    # LINEの外部ブラウザ起動フラグを付与
    separator = "&" if "?" in authorization_url else "?"
    external_url = f"{authorization_url}{separator}openExternalBrowser=1"
    
    # 💡 JSでSafari/Chromeへの切り替えを促す中継ページ
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
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google"
    )
    flow.fetch_token(authorization_response=request.url)
    
    # Googleカレンダーから予定を取得
    creds = flow.credentials
    service = build('calendar', 'v3', credentials=creds)
    
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=10)).isoformat() + 'Z'
    
    events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=time_max,
                                        singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    # 予定リストのHTML作成（開始〜終了時間を表示）
    event_items_html = ""
    for event in events:
        start_raw = event['start'].get('dateTime', event['start'].get('date'))
        end_raw = event['end'].get('dateTime', event['end'].get('date'))
        
        # 形式: 12/22 19:00 - 21:00
        date_str = start_raw[5:10].replace('-', '/')
        start_time = start_raw[11:16] if 'T' in start_raw else "終日"
        end_time = end_raw[11:16] if 'T' in end_raw else ""
        
        time_display = f"{start_time} - {end_time}" if end_time else start_time
        summary = event.get('summary', '予定あり')
        event_items_html += f"<li><span style='color:#888;'>{date_str}</span> <b>{time_display}</b>: {summary}</li>"

    if not event_items_html:
        event_items_html = "<li>直近の予定はありません</li>"

    # 確認画面の表示
    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width,initial-scale=1.0">
            <style>
                body {{ font-family: sans-serif; background: #f4f5f7; padding: 15px; text-align: center; }}
                .container {{ background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 400px; margin: auto; }}
                .event-box {{ background: #f9f9f9; border-radius: 12px; padding: 15px; margin: 15px 0; max-height: 180px; overflow-y: auto; text-align: left; font-size: 0.85rem; border: 1px solid #eee; }}
                ul {{ list-style: none; padding: 0; margin: 0; }}
                li {{ padding: 6px 0; border-bottom: 1px solid #eee; }}
                .btn-confirm {{ display: block; width: 100%; padding: 18px; background: #00b900; color: white; border: none; border-radius: 35px; font-weight: bold; font-size: 1.1rem; cursor: pointer; }}
                .privacy-msg {{ font-size: 0.8rem; color: #666; background: #fffde7; padding: 12px; border-radius: 10px; text-align: left; margin-bottom: 20px; border: 1px solid #ffe082; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 style="color:#00b900; margin-top:0;">📅 予定を確認しました</h2>
                <div class="event-box"><ul>{event_items_html}</ul></div>
                <div class="privacy-msg">
                    <strong>🛡️ 幹事への共有について</strong><br>
                    安心してください。幹事には「OKな時間」だけを伝えます。予定のタイトル（例：通院）は<b>一切送信されません</b>。
                </div>
                <button class="btn-confirm" onclick="finish()">この内容で回答する</button>
            </div>
            <script>
                function finish() {{
                    alert("回答が完了しました！\\nブラウザを閉じてトーク画面に戻ってください。");
                    window.close();
                }}
            </script>
        </body>
    </html>
    """

if __name__ == "__main__":
    app.run()
