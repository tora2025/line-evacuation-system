from flask import Flask, request, jsonify, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    LocationMessage, QuickReply, QuickReplyButton, MessageAction, QuickReply
)
import psycopg2
import os
from line_config import CHANNEL_SECRET, CHANNEL_ACCESS_TOKEN

from supabase import create_client, Client

# 環境変数から Supabase 接続情報を取得
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Supabase クライアントを作成
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


app = Flask(__name__)
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ユーザーごとの入力状態を管理
user_states = {}

# PostgreSQL接続関数
def connect_db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=5432
    )

# DB保存関数
def save_to_db(user_id, data):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE damage_reports
                SET damage_info = %s,
                    health_status = %s,
                    rescue_needed = %s,
                    people_count = %s,
                    age_group = %s,
                    comment = %s
                WHERE id = (
                    SELECT id FROM damage_reports
                    WHERE user_id = %s
                    ORDER BY id DESC LIMIT 1
                )
            """, (
                data.get("damage_info"),
                data.get("health_status"),
                data.get("rescue_needed"),
                data.get("people_count"),
                data.get("age_group"),
                data.get("comment"),
                user_id
            ))
            conn.commit()

# Webhookエンドポイント
@app.route("/webhook", methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return 'Invalid signature', 400
    return 'OK', 200

# 位置情報メッセージ受信 → DB保存 + 健康状態質問
@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    lat = event.message.latitude
    lng = event.message.longitude
    user_id = event.source.user_id

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO damage_reports (user_id, latitude, longitude) VALUES (%s, %s, %s)",
                (user_id, lat, lng)
            )
            conn.commit()

    # 会話の最初のステップ
    user_states[user_id] = {"latitude": lat, "longitude": lng}

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text='健康状態を選んでください：',
            quick_reply=QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="無傷", text="無傷")),
                QuickReplyButton(action=MessageAction(label="軽傷", text="軽傷")),
                QuickReplyButton(action=MessageAction(label="重傷", text="重傷")),
            ])
        )
    )

# テキストメッセージ受信 → 状態に応じて次の質問
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    text = event.message.text

    if user_id not in user_states:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="まず位置情報を送ってください。")
        )
        return

    state = user_states[user_id]

    # 健康状態
    if "health_status" not in state:
        state["health_status"] = text
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="救助は必要ですか？",
                quick_reply=QuickReply(items=[
                    QuickReplyButton(action=MessageAction(label="はい", text="はい")),
                    QuickReplyButton(action=MessageAction(label="いいえ", text="いいえ")),
                ])
            )
        )
        return

    # 救助要否
    if "rescue_needed" not in state:
        state["rescue_needed"] = (text == "はい")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="被害状況を選んでください：",
                quick_reply=QuickReply(items=[
                    QuickReplyButton(action=MessageAction(label="倒壊", text="倒壊")),
                    QuickReplyButton(action=MessageAction(label="冠水", text="冠水")),
                    QuickReplyButton(action=MessageAction(label="通行止め", text="通行止め")),
                    QuickReplyButton(action=MessageAction(label="火災", text="火災")),
                    QuickReplyButton(action=MessageAction(label="その他", text="その他")),
                ])
            )
        )
        return

    # 被害状況
    if "damage_info" not in state:
        state["damage_info"] = text
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="一緒にいる人数を入力してください（例: 3）")
        )
        return

    # 人数
    if "people_count" not in state:
        try:
            state["people_count"] = int(text)
        except ValueError:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="人数は数字で入力してください。")
            )
            return
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="年齢層を入力してください（例: 子供、大人、高齢者）")
        )
        return

    # 年齢層
    if "age_group" not in state:
        state["age_group"] = text
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="最後にコメントがあれば入力してください（なければ「なし」と送信）")
        )
        return

    # コメント → DB保存
    if "comment" not in state:
        state["comment"] = text

        save_to_db(user_id, state)

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="情報を受け付けました。ありがとうございます。")
        )

        # 状態リセット
        del user_states[user_id]

# 地図ページ
@app.route("/map")
def map_view():
    return render_template("index.html")

@app.route("/clear_data", methods=["POST"])
def clear_data():
    try:
        global supabase
        supabase.table("disaster_reports").delete().neq("id", 0).execute()
        return jsonify({"status": "success", "message": "全データを削除しました"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# 被害情報をGeoJSONで返すAPI（追加情報を含む）
@app.route("/data")
def get_data():
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT latitude, longitude, damage_info, health_status, rescue_needed,
                       people_count, age_group, comment
                FROM damage_reports
                WHERE damage_info IS NOT NULL
            """)
            rows = cur.fetchall()

    features = []
    for lat, lng, damage, health_status, rescue_needed, people_count, age_group, comment in rows:
        properties = {
            "damage": damage,
            "health_status": health_status,
            "rescue_needed": rescue_needed,
            "people_count": people_count,
            "age_group": age_group,
            "comment": comment
        }
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lng, lat]},
            "properties": properties
        }
        features.append(feature)

    return jsonify({"type": "FeatureCollection", "features": features})

# Flaskの起動（Render対応）
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)





