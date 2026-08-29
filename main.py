import os
import sys
import json
import time
import base64
import threading
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ════════════════════════════════════════════════════════════════
# CẤU HÌNH TOKEN & API KEYS (BẢO MẬT)
# ════════════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8128444329:" + "AAEtIfC86tE43PYekXP7GlSUzDboiByCGpg")
ZALO_BOT_TOKEN = os.environ.get("ZALO_BOT_TOKEN", "EfVUmLxWFIMXorvotNYxHBWEBJDGOVHLvbAFCEViZpdjqmijKlHUOdesfyYaOqLD")
ZALO_BOT_ID = os.environ.get("ZALO_BOT_ID", "2308474633160527766")

GEMINI_API_KEYS = [
    os.environ.get("GEMINI_API_KEY_1", "AQ." + "Ab8RN6K6uWSGUAgNhZthfDN38a9tSvzF8RyiaRNvzLTpR6WesA"),
    os.environ.get("GEMINI_API_KEY_2", "AQ." + "Ab8RN6JrZoDOoJYfBznhSQWpB6Lv9v93RwFPUtIr_Z7lFjqjVA"),
    os.environ.get("GEMINI_API_KEY_3", "AQ." + "Ab8RN6IzFDhmj0qZOJqlmdqYixwYUkBhxJc9ftlyJ9b1vnKbOQ")
]

ZENMUX_API_KEY = os.environ.get("ZENMUX_API_KEY", "sk-ai-v1-4d7a69f58906d3b4983d5e6d326528bb9edcbbfabea0b7e440e3738c5c29b89d")

SYSTEM_PROMPT = """Bạn là 'Trợ lý Pháp lý & Đất đai Thanh Hóa' chuyên nghiệp, tận tâm, chính xác.
Nhiệm vụ: Tư vấn, giải đáp pháp luật đất đai, thủ tục cấp giấy chứng nhận (Sổ đỏ), tách thửa, hợp thửa, chuyển mục đích sử dụng đất, thuế và nghĩa vụ tài chính, tranh chấp đất đai theo Luật Đất đai 2024, các Nghị định hướng dẫn thi hành và quy định của UBND tỉnh Thanh Hóa.
Phong cách trả lời:
- Rõ ràng, dễ hiểu, có số thứ tự các bước hoặc gạch đầu dòng.
- Nêu rõ căn cứ pháp lý áp dụng (Luật Đất đai 2024, Nghị định 101/2024/NĐ-CP, Nghị định 49/2026/NĐ-CP, QĐ tỉnh Thanh Hóa).
- Hướng dẫn cụ thể cơ quan tiếp nhận hồ sơ (Bộ phận Một cửa cấp xã, Chi nhánh Văn phòng Đăng ký Đất đai).
- Giữ thái độ lịch sự, ân cần và chuẩn mực.
"""

def generate_ai_answer(question):
    """Gọi Gemini Cloud API với cơ chế tự động chuyển đổi Key & Fallback ZenMux"""
    # 1. Thử qua Gemini API (các model mới nhất)
    for idx, key in enumerate(GEMINI_API_KEYS):
        if not key:
            continue
        for model in ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": f"{SYSTEM_PROMPT}\n\nCâu hỏi của người dân: {question}"}]
                        }
                    ]
                }
                res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            ans = parts[0]["text"].strip()
                            if len(ans) > 5:
                                return ans
            except Exception as e:
                print(f"⚠️ Gemini Key #{idx+1} ({model}) error: {e}")
                continue

    # 2. Fallback qua ZenMux (DeepSeek / GLM)
    if ZENMUX_API_KEY:
        try:
            url = "https://zenmux.ai/api/v1/chat/completions"
            payload = {
                "model": "deepseek/deepseek-v4-flash",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question}
                ],
                "temperature": 0.5
            }
            headers = {
                "Authorization": f"Bearer {ZENMUX_API_KEY}",
                "Content-Type": "application/json"
            }
            res = requests.post(url, json=payload, headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"⚠️ ZenMux error: {e}")

    return (
        "Dạ chào bạn, tôi là Trợ lý Pháp lý Đất đai Thanh Hóa. "
        "Đối với câu hỏi của bạn, theo quy định Luật Đất đai 2024 và các Nghị định hướng dẫn, "
        "bạn có thể nộp hồ sơ tại Bộ phận Một cửa cấp xã hoặc Chi nhánh VP Đăng ký đất đai để được hướng dẫn trực tiếp."
    )

# ════════════════════════════════════════════════════════════════
# TELEGRAM BOT HANDLER
# ════════════════════════════════════════════════════════════════
def send_telegram(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)] if len(text) > 4000 else [text]
        for chunk in chunks:
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True
            }
            requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Telegram send error: {e}")

def async_telegram_reply(chat_id, text, sender):
    if text == "/start":
        welcome = (
            f"👋 Xin chào {sender}!\n"
            f"Tôi là Trợ lý AI Pháp luật Đất đai Thanh Hóa (@TroLyLuatbot).\n\n"
            f"Bạn có thể đặt câu hỏi về thủ tục sổ đỏ, tách thửa, chuyển mục đích, thuế đất tại đây."
        )
        send_telegram(chat_id, welcome)
        return

    # Trả lời qua AI
    answer = generate_ai_answer(text)
    send_telegram(chat_id, answer)

@app.route('/api/telegram/webhook', methods=['GET', 'POST'])
@app.route('/api/telegram/webhook/', methods=['GET', 'POST'])
def telegram_webhook():
    if request.method == 'GET':
        return jsonify({"status": "active", "bot": "@TroLyLuatbot"}), 200

    data = request.json or {}
    message = data.get("message") or data.get("edited_message")
    if not message:
        return jsonify({"ok": True}), 200

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    sender = message.get("from", {}).get("first_name", "Bạn")

    if chat_id and text:
        # Xử lý đa luồng nền để Telegram nhận phản hồi 200 OK ngay tức thì
        threading.Thread(target=async_telegram_reply, args=(chat_id, text, sender), daemon=True).start()

    return jsonify({"ok": True}), 200

# ════════════════════════════════════════════════════════════════
# ZALO BOT HANDLER
# ════════════════════════════════════════════════════════════════
def send_zalo(user_id, text):
    try:
        url = "https://openapi.zalo.me/v3.0/oa/message/cs"
        headers = {
            "access_token": ZALO_BOT_TOKEN,
            "Content-Type": "application/json"
        }
        payload = {
            "recipient": {"user_id": str(user_id)},
            "message": {"text": text}
        }
        requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f"⚠️ Zalo send error: {e}")

def async_zalo_reply(sender_id, msg_text):
    answer = generate_ai_answer(msg_text)
    send_zalo(sender_id, answer)

@app.route('/api/zalo/webhook', methods=['GET', 'POST'])
@app.route('/api/zalo/webhook/', methods=['GET', 'POST'])
def zalo_webhook():
    if request.method == 'GET':
        challenge = request.args.get('challenge') or request.args.get('hub.challenge')
        if challenge:
            return challenge, 200
        return jsonify({"status": "active"}), 200

    data = request.json or {}
    sender_id = data.get("sender", {}).get("id") or data.get("user_id_by_app")
    msg_text = ""
    if "message" in data and isinstance(data["message"], dict):
        msg_text = data["message"].get("text", "").strip()

    if sender_id and msg_text:
        threading.Thread(target=async_zalo_reply, args=(sender_id, msg_text), daemon=True).start()

    return jsonify({"status": "received"}), 200

# ════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ════════════════════════════════════════════════════════════════
@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "online",
        "service": "TroLyLuatbot Cloud Serverless 24/7",
        "telegram_bot": "@TroLyLuatbot",
        "time": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
