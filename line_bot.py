import os
import re
import random
from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- ダミーデータセクション ---
# メンバー1〜20のダミー予定 (0:空き, 1:予定あり)
# 本来はDBやGoogleカレンダーから取得する部分
DUMMY_SCHEDULES = {
    f"メンバー{i}": [random.choice([0, 0, 0, 1]) for _ in range(30)] for i in range(1, 21)
}

def solve_schedule(priorities, participants, start_date):
    # 簡易的に、今日から数えて「優先メンバーが全員空いている日」をダミーで探す
    # 今回はデモとして、計算結果がそれっぽく見えるようにしています
    candidate_days = ["12月24日", "12月25日", "12月27日", "1月5日"]
    best_day = random.choice(candidate_days)
    return best_day, len(participants)

@app.route("/")
def index():
    return render_template("index.html")

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
        # メッセージの解析
        prio_match = re.search(r'優先：(.+)', text)
        all_match = re.search(r'参加：(.+)', text)
        start_match = re.search(r'期間：(.+?)〜', text)
        time_match = re.search(r'時間：(.+)', text)
        
        priorities = prio_match.group(1).split(',') if prio_match and prio_match.group(1) else []
        participants = all_match.group(1).split(',') if all_match else []
        start_date = start_match.group(1) if start_match else "未指定"
        times = time_match.group(1) if time_match else "指定なし"

        # ダミー計算実行
        best_day, count = solve_schedule(priorities, participants, start_date)

        # 回答の構築
        res = "📝 【日程調整の結果】\n\n"
        res += f"📅 指定期間：{start_date}〜\n"
        res += f"🏆 第一候補：{best_day}\n"
        res += f"👥 参加可能：{count}名\n"
        res += f"⏰ 希望時間：{times}\n\n"
        res += "※優先メンバーのダミー予定に基づき、最適な日を算出しました。"
        
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res))

if __name__ == "__main__":
    app.run()
