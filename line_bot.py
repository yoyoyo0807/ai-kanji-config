import os
import re
import random
from flask import Flask, request, abort, render_template, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- ダミーデータセクション ---
DUMMY_SCHEDULES = {
    f"メンバー{i}": [random.choice([0, 0, 0, 1]) for _ in range(30)] for i in range(1, 21)
}

def solve_schedule(priorities, participants, start_date):
    candidate_days = ["12月24日", "12月25日", "12月27日", "1月5日"]
    best_day = random.choice(candidate_days)
    return best_day, len(participants)

# --- 1. メイン画面 (幹事が使う) ---
@app.route("/")
def index():
    return render_template("index.html")

# --- 2. 回答ページ (招待された友達が飛んでくる) ---
@app.route("/answer")
def answer():
    # URLパラメータから情報を取得 (?res=yes&title=...)
    res = request.args.get('res')
    title = request.args.get('title', 'イベント')
    
    if res == 'no':
        # 不参加の場合の画面を直接返す
        return """
        <html>
        <head><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
        <body style="text-align:center; padding-top:50px; font-family:sans-serif; background:#f4f5f7;">
            <div style="background:white; margin:20px; padding:30px; border-radius:16px; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
                <h1 style="font-size:50px; margin:0;">😢</h1>
                <h2 style="color:#333;">了解いたしました！</h2>
                <p style="color:#666;">またの機会に誘ってくださいね。</p>
                <p style="font-size:0.8rem; color:#999; margin-top:20px;">※このタブを閉じて大丈夫です</p>
            </div>
        </body>
        </html>
        """
    
    # 参加(yes)の場合：連携方法を選択させるHTMLを表示
    # templates/select_method.html が必要です
    return render_template('select_method.html', title=title)

# --- 3. LINE Webhook設定 ---
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
    text = event.message.text
    
    if "調整開始" in text:
        prio_match = re.search(r'優先：(.+)', text)
        all_match = re.search(r'参加：(.+)', text)
        start_match = re.search(r'期間：(.+?)〜', text)
        time_match = re.search(r'時間：(.+)', text)
        
        priorities = prio_match.group(1).split(',') if prio_match and prio_match.group(1) else []
        participants = all_match.group(1).split(',') if all_match else []
        start_date = start_match.group(1) if start_match else "未指定"
        times = time_match.group(1) if time_match else "指定なし"

        best_day, count = solve_schedule(priorities, participants, start_date)

        res = "📝 【日程調整の結果】\n\n"
        res += f"📅 指定期間：{start_date}〜\n"
        res += f"🏆 第一候補：{best_day}\n"
        res += f"👥 参加可能：{count}名\n"
        res += f"⏰ 希望時間：{times}\n\n"
        res += "※優先メンバーのダミー予定に基づき、最適な日を算出しました。"
        
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res))

if __name__ == "__main__":
    app.run()
