from flask import Flask, request, jsonify, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    LocationMessage, QuickReply, QuickReplyButton, MessageAction
)
import psycopg2
import os
from geopy.distance import geodesic
from line_config import CHANNEL_SECRET, CHANNEL_ACCESS_TOKEN

app = Flask(__name__)
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# PostgreSQL接続関数
def connect_db():
    return psycopg2.connect(
        host=os.environ.get("aws-0-ap-northeast-1.pooler.supabase.com"),
        dbname=os.environ.get("postgres"),
        user=os.environ.get("postgres.igalbyihaubxbfhyvuwe"),
        password=os.environ.get("tora0614nazarick"),
        port=5432
    )

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

# 位置情報メッセージ受信 → DB保存 + QuickReply
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

    items = ['倒壊', '冠水', '通行止め', '火災', 'その他']
    quick_reply_items = [QuickReplyButton(action=MessageAction(label=item, text=item)) for item in items]
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text='被害状況を選択してください：',
            quick_reply=QuickReply(items=quick_reply_items)
        )
    )

# テキストメッセージ受信 → 被害内容DBに登録
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    damage = event.message.text

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE damage_reports 
                SET damage_info = %s
                WHERE user_id = %s AND damage_info IS NULL
                ORDER BY id DESC LIMIT 1
            """, (damage, user_id))
            conn.commit()

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f'被害情報「{damage}」を受け付けました。ありがとうございました。')
    )

# 地図ページ
@app.route("/map")
def map_view():
    return render_template("index.html")

# 被害情報をGeoJSONで返すAPI
@app.route("/data")
def get_data():
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT latitude, longitude, damage_info FROM damage_reports WHERE damage_info IS NOT NULL")
            rows = cur.fetchall()

    features = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": {"damage": damage}
    } for lat, lng, damage in rows]

    return jsonify({"type": "FeatureCollection", "features": features})

# Flaskの起動（Render対応）
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
