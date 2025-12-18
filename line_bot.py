import os
import re
from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 環境変数
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 模擬データ
availability_data = {f"人{i}": [0, 1, 0] if i % 2 == 0 else [1, 0, 0] for i in range(1, 21)}
dates = ["20日", "21日", "22日"]

def solve_schedule(priorities, participants):
    scores = [0, 0, 0]
    for i in range(3):
        prio_ok = all(availability_data.get(p, [0,0,0])[i] == 0 for p in priorities)
        count = sum(1 for p in participants if availability_data.get(p, [0,0,0])[i] == 0)
        scores[i] = count + 100 if prio_ok else count
    best_idx = scores.index(max(scores))
    return dates[best_idx], scores[best_idx] % 100

# --- ここが重要！Web画面を表示する設定 ---
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
    if "調整" in text:
        range_match = re.search(r'期間：(.+)', text)
        all_match = re.search(r'参加：(.+)', text)
        prio_match = re.search(r'優先：(.+)', text)
        time_match = re.search(r'時間：(.+)', text)
        
        d_range = range_match.group(1) if range_match else "未指定"
        participants = all_match.group(1).split(',') if all_match else []
        priorities = prio_match.group(1).split(',') if prio_match else []
        times = time_match.group(1).split(',') if time_match else []

        best_day, ok_count = solve_schedule(priorities, participants)

        res = f"【日程調整の結果】\n\n📅 指定期間：\n{d_range}\n🏆 第一候補：12月{best_day}\n👥 参加可能：{ok_count}名\n⏰ 希望時間：{', '.join(times)}\n\n※最適な日を算出しました。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res))

if __name__ == "__main__":
    app.run()
