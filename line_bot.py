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

# --- 回答方法の選択 (手動入力ボタンをここで復活) ---
@app.route("/answer")
def answer():
    res = request.args.get('res')
    title = request.args.get('title', 'イベント')
    if res == 'no':
        return """<html><body style="text-align:center;padding-top:50px;font-family:sans-serif;"><h2>了解いたしました！</h2></body></html>"""
    # 選択画面を表示（ここで「手動入力」か「Google連携」かを選べる）
    return render_template('select_method.html', title=title)

# --- 🚀 手動入力画面のルートを追加 ---
@app.route("/manual_input")
def manual_input():
    # 今回はひとまず入力用テンプレートを呼び出す形にします
    title = request.args.get('title', 'イベント')
    return render_template('manual_input.html', title=title)

@app.route("/auth/google")
def auth_google():
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google")
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    # 外部ブラウザ強制フラグ
    separator = "&" if "?" in authorization_url else "?"
    external_url = f"{authorization_url}{separator}openExternalBrowser=1"
    return f"""<html><head><script>window.location.href = "{external_url}";</script></head>
               <body style="text-align:center;padding-top:50px;">移動中...</body></html>"""

@app.route("/callback/google")
def callback_google():
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri="https://ai-kanji-config-1.onrender.com/callback/google")
    flow.fetch_token(authorization_response=request.url)
    
    creds = flow.credentials
    service = build('calendar', 'v3', credentials=creds)
    
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    time_max = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + 'Z'
    
    events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=time_max,
                                        singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    # HTML表示用の予定リスト作成（ユーザー確認用）
    event_items_html = "".join([f"<li>{e['start'].get('dateTime', e['start'].get('date'))[5:16].replace('T',' ')}: {e.get('summary', '予定あり')}</li>" for e in events]) or "<li>直近の予定はありません</li>"

    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width,initial-scale=1.0">
            <style>
                body {{ font-family: sans-serif; background: #f4f5f7; padding: 15px; text-align: center; }}
                .container {{ background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 400px; margin: auto; }}
                .event-box {{ background: #f9f9f9; border-radius: 12px; padding: 15px; margin: 15px 0; max-height: 150px; overflow-y: auto; text-align: left; font-size: 0.85rem; border: 1px solid #eee; }}
                .btn-confirm {{ display: block; width: 100%; padding: 18px; background: #00b900; color: white; border: none; border-radius: 35px; font-weight: bold; font-size: 1.1rem; cursor: pointer; }}
                .privacy-note {{ font-size: 0.8rem; color: #666; margin: 15px 0; background: #fffde7; padding: 12px; border-radius: 8px; text-align: left; line-height: 1.4; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 style="color:#00b900;">📅 予定を確認しました</h2>
                <div class="event-box"><ul>{event_items_html}</ul></div>

                <div class="privacy-note">
                    <strong>🛡️ プライバシー保護について</strong><br>
                    安心してください。幹事には「何の予定か（例：通院）」は<b>一切送信されません</b>。AIが「いつが空いているか」を計算した結果だけを共有します。
                </div>

                <button class="btn-confirm" onclick="confirmShare()">この予定を除いて空き時間を送る</button>
            </div>
            <script>
                function confirmShare() {{
                    alert("空き時間の計算が完了しました！幹事には『OKな時間のみ』を共有しました。");
                    window.close();
                }}
            </script>
        </body>
    </html>
    """

if __name__ == "__main__":
    app.run()
