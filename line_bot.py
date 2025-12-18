import os
import re
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 環境変数から設定を取得
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

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
    user_message = event.message.text

    # 1. LIFFからの「調整」指示に反応する
    if "調整" in user_message:
        # --- データの解析 (正規表現を使用) ---
        # 「優先：」から後ろのメンバーをリスト化
        prio_match = re.search(r'優先：(.+)', user_message)
        selected_prios = prio_match.group(1).split(',') if prio_match else []
        
        # 「時間：」から後ろの時間帯をリスト化
        time_match = re.search(r'時間：(.+)', user_message)
        selected_times = time_match.group(1).split(',') if time_match else []

        # 2. 計算ロジック（AI部分）へ渡す
        # ※ ここに以前作成した solve_schedule(selected_prios) などを呼び出すコードを入れます
        # 今回はデモとして、受け取った内容をそのまま返します
        
        result_text = "【調整を開始します】\n\n"
        if selected_prios:
            result_text += f"👤 優先メンバー:\n・" + "\n・".join(selected_prios) + "\n"
        else:
            result_text += "👤 優先メンバー: 指定なし\n"
            
        if selected_times:
            result_text += f"\n⏰ 希望時間帯:\n・" + "\n・".join(selected_times) + "\n"
        else:
            result_text += "\n⏰ 希望時間帯: 指定なし\n"

        result_text += "\n上記条件で最適な日程を算出中... しばらくお待ちください。"

        # LINEに返信を送信
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=result_text)
        )

    # 3. その他の通常メッセージ（「おすすめのお店」など）への反応
    elif "お店" in user_message:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="この付近で評価の高いお店をいくつかピックアップしますね！")
        )

if __name__ == "__main__":
    app.run()