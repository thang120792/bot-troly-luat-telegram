import os
import sys
import re
import json
import time
import threading
import urllib.request
from flask import Flask, request, jsonify

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

app = Flask(__name__)

# ══════════════════════════════════════════════
# CORS - Cho phép Web GitHub Pages gọi API
# ══════════════════════════════════════════════
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        res = jsonify({"status": "ok"})
        res.headers['Access-Control-Allow-Origin'] = '*'
        res.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With'
        res.headers['Access-Control-Allow-Methods'] = 'GET,POST,DELETE,OPTIONS'
        return res, 200

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,DELETE,OPTIONS'
    return response

# ══════════════════════════════════════════════
# CẤU HÌNH API KEYS
# ══════════════════════════════════════════════
GEMINI_API_KEYS = [
    os.environ.get("GEMINI_API_KEY_1", "AQ.Ab8RN6K6uWSGUAgNhZthfDN38a9tSvzF8RyiaRNvzLTpR6WesA"),
    os.environ.get("GEMINI_API_KEY_2", "AQ.Ab8RN6JrZoDOoJYfBznhSQWpB6Lv9v93RwFPUtIr_Z7lFjqjVA"),
    os.environ.get("GEMINI_API_KEY_3", "AQ.Ab8RN6IzFDhmj0qZOJqlmdqYixwYUkBhxJc9ftlyJ9b1vnKbOQ"),
]
ZENMUX_API_KEY = os.environ.get("ZENMUX_API_KEY", "sk-ai-v1-4d7a69f58906d3b4983d5e6d326528bb9edcbbfabea0b7e440e3738c5c29b89d")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8128444329:AAEtIfC86tE43PYekXP7GlSUzDboiByCGpg")
ZALO_BOT_TOKEN = os.environ.get("ZALO_BOT_TOKEN", "EfVUmLxWFIMXorvotNYxHBWEBJDGOVHLvbAFCEViZpdjqmijKlHUOdesfyYaOqLD")

# ══════════════════════════════════════════════
# SYSTEM PROMPT - Bộ Não Pháp Lý Thanh Hóa
# ══════════════════════════════════════════════
SYSTEM_PROMPT = """Bạn là Trợ lý AI Pháp lý Đất đai tỉnh Thanh Hóa, chuyên nghiệp và chính xác.

QUY CHUẨN BẮT BUỘC KHI TRẢ LỜI:
1. Toàn bộ câu trả lời phải bằng TIẾNG VIỆT CHUẨN MỰC 100% - tuyệt đối không dùng tiếng Anh.
2. Trình bày rõ ràng theo số thứ tự (Bước 1, Bước 2...) hoặc gạch đầu dòng.
3. Nêu rõ căn cứ pháp lý từ các văn bản:
   - Luật Đất đai 2024 (Luật số 31/2024/QH15)
   - Nghị định 101/2024/NĐ-CP về cấp Giấy chứng nhận và đăng ký biến động
   - Nghị định 102/2024/NĐ-CP quy định chi tiết thi hành Luật Đất đai
   - Nghị định 49/2026/NĐ-CP về nghĩa vụ tài chính, tiền sử dụng đất
   - Quyết định 18/2026/QĐ-UBND tỉnh Thanh Hóa: hạn mức giao đất ở, công nhận đất ở, diện tích tối thiểu tách thửa tại 27 huyện/thị/thành phố
   - Quyết định 2604/QĐ-VP Thanh Hóa: quy trình nội bộ TTHC, phân cấp thẩm quyền cấp GCN, mẫu đơn số 25, 29, 34, 35

CHI TIẾT NGHIỆP VỤ QUAN TRỌNG NHẤT:
• Hạn mức tách thửa đất ở theo QĐ 18/2026/QĐ-UBND:
  - Đất ở tại Phường (đô thị): tối thiểu ≥ 40m², mặt tiền ≥ 3.0m
  - Đất ở tại Xã (đồng bằng/trung du): tối thiểu ≥ 40m², mặt tiền ≥ 4.0m  
  - Đất ở tại Xã (miền núi): tối thiểu ≥ 50m², mặt tiền ≥ 5.0m
  - Đất nông nghiệp (CLN, BHK): tối thiểu ≥ 500m²
  - Đất rừng sản xuất: tối thiểu ≥ 3.000m²
  - Đất trồng lúa: tối thiểu ≥ 1.000m²

• Thẩm quyền cấp GCN theo QĐ 2604/QĐ-VP (Phụ lục I, II, III):
  - Tổ chức, doanh nghiệp thuê đất trả tiền một lần: Sở Nông nghiệp và Môi trường cấp tỉnh
  - Hộ gia đình, cá nhân: Chi nhánh Văn phòng Đăng ký đất đai cấp huyện
  - Đặc biệt: UBND cấp xã CÓ THẨM QUYỀN ký và cấp GCN lần đầu cho các trường hợp: giao đất không thu tiền trong 1 xã, đất ở không đấu giá cho cá nhân ưu tiên, xác định lại đất ở trước 01/7/2004, đất tôn giáo tín ngưỡng.

• Nghĩa vụ tài chính:
  - Lệ phí trước bạ nhà đất: 0.5% giá trị GCN
  - Thuế thu nhập cá nhân chuyển nhượng BĐS: 2% giá chuyển nhượng
  - Tiền sử dụng đất khi chuyển mục đích: theo bảng giá đất tỉnh Thanh Hóa 2024-2028

• Thời hạn giải quyết (QĐ 2604/QĐ-VP):
  - Đăng ký đất đai lần đầu: không quá 30 ngày làm việc
  - Chuyển nhượng, tặng cho, thừa kế: không quá 15 ngày làm việc
  - Tách thửa, hợp thửa: không quá 15 ngày làm việc
  - Đính chính, cấp lại GCN: không quá 10 ngày làm việc

Luôn kết thúc câu trả lời bằng gợi ý các câu hỏi liên quan mà người dân có thể hỏi tiếp."""

def call_gemini(question, context=""):
    """Gọi Gemini API với nhiều key dự phòng"""
    full_prompt = f"{SYSTEM_PROMPT}\n\n"
    if context:
        full_prompt += f"THÔNG TIN BỔ SUNG:\n{context}\n\n"
    full_prompt += f"CÂU HỎI: {question}\n\nTRẢ LỜI (100% Tiếng Việt):"

    for key in GEMINI_API_KEYS:
        if not key or len(key) < 10:
            continue
        for model in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = json.dumps({
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}
                }).encode("utf-8")
                req = urllib.request.Request(url, data=payload,
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and parts[0].get("text", "").strip():
                            return parts[0]["text"].strip(), model
            except Exception as e:
                print(f"⚠️ Gemini {model} error: {e}")
                continue

    # Fallback ZenMux (DeepSeek)
    try:
        url = "https://zenmux.ai/api/v1/chat/completions"
        payload = json.dumps({
            "model": "deepseek/deepseek-v4-flash",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ],
            "temperature": 0.2
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Bearer {ZENMUX_API_KEY}",
            "Content-Type": "application/json"
        }, method="POST")
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip(), "deepseek-v4-flash"
    except Exception as e:
        print(f"⚠️ ZenMux error: {e}")

    return (
        "Dạ, câu hỏi của bạn liên quan đến pháp luật đất đai tỉnh Thanh Hóa. "
        "Theo Luật Đất đai 2024 và Quyết định 18/2026/QĐ-UBND, bạn vui lòng liên hệ "
        "Bộ phận Một cửa UBND cấp xã hoặc Chi nhánh Văn phòng Đăng ký đất đai để được "
        "hướng dẫn chi tiết và chính xác nhất."
    ), "fallback"

# ══════════════════════════════════════════════
# API ROUTES
# ══════════════════════════════════════════════
@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
@app.route('/api/status', methods=['GET'])
def health():
    return jsonify({
        "status": "online",
        "service": "ThanhHoa Land AI v2026",
        "api_chat": "/api/chat [POST]",
        "telegram": "@TroLyLuatbot",
        "model": "Gemini 2.5 Flash + DeepSeek Fallback"
    }), 200

@app.route('/api/chat', methods=['GET', 'POST', 'OPTIONS'])
def api_chat():
    if request.method in ('GET', 'OPTIONS'):
        return jsonify({"status": "ok", "endpoint": "/api/chat", "method": "POST"}), 200

    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    session_id = data.get("session_id", "web_user")

    if not question:
        return jsonify({"error": "Vui lòng nhập câu hỏi"}), 400

    print(f"📥 [Web] {session_id}: {question[:80]}")
    answer, model_used = call_gemini(question)

    return jsonify({
        "answer": answer,
        "model": f"🤖 {model_used}",
        "session_id": session_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200

# ══════════════════════════════════════════════
# TELEGRAM WEBHOOK
# ══════════════════════════════════════════════
def send_telegram(chat_id, text):
    try:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = json.dumps({"chat_id": chat_id, "text": chunk,
                "parse_mode": "Markdown", "disable_web_page_preview": True}).encode("utf-8")
            req = urllib.request.Request(url, data=payload,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10):
                pass
    except Exception as e:
        print(f"⚠️ Telegram send error: {e}")

def reply_telegram(chat_id, text, sender):
    if text == "/start":
        msg = (f"👋 Xin chào {sender}!\n"
               f"Tôi là *Trợ lý AI Pháp lý Đất đai Thanh Hóa* (@TroLyLuatbot).\n\n"
               f"Hãy đặt câu hỏi về:\n"
               f"• Thủ tục cấp Sổ đỏ, tách thửa\n"
               f"• Chuyển mục đích sử dụng đất\n"
               f"• Hạn mức giao đất tại tỉnh Thanh Hóa\n"
               f"• Thuế, lệ phí trước bạ đất đai")
        send_telegram(chat_id, msg)
        return
    answer, _ = call_gemini(text)
    send_telegram(chat_id, answer)

@app.route('/api/telegram/webhook', methods=['GET', 'POST', 'OPTIONS'])
def telegram_webhook():
    if request.method in ('GET', 'OPTIONS'):
        return jsonify({"status": "webhook active", "bot": "@TroLyLuatbot"}), 200

    data = request.get_json(silent=True) or {}
    message = data.get("message") or data.get("edited_message")
    if not message:
        return jsonify({"ok": True}), 200

    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    sender = message.get("from", {}).get("first_name", "Bạn")

    if chat_id and text:
        threading.Thread(target=reply_telegram, args=(chat_id, text, sender), daemon=True).start()

    return jsonify({"ok": True}), 200

# ══════════════════════════════════════════════
# ZALO WEBHOOK
# ══════════════════════════════════════════════
def send_zalo(user_id, text):
    try:
        url = "https://openapi.zalo.me/v3.0/oa/message/cs"
        payload = json.dumps({
            "recipient": {"user_id": str(user_id)},
            "message": {"text": text}
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={
            "access_token": ZALO_BOT_TOKEN,
            "Content-Type": "application/json"
        }, method="POST")
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        print(f"⚠️ Zalo send error: {e}")

@app.route('/api/zalo/webhook', methods=['GET', 'POST', 'OPTIONS'])
def zalo_webhook():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge') or request.args.get('challenge')
        if challenge:
            return challenge, 200
        return jsonify({"status": "active"}), 200

    data = request.get_json(silent=True) or {}
    sender_id = (data.get("sender") or {}).get("id") or data.get("user_id_by_app")
    msg = (data.get("message") or {})
    text = msg.get("text", "").strip() if isinstance(msg, dict) else ""

    if sender_id and text:
        def _reply():
            answer, _ = call_gemini(text)
            send_zalo(sender_id, answer)
        threading.Thread(target=_reply, daemon=True).start()

    return jsonify({"status": "received"}), 200

# ══════════════════════════════════════════════
# OCR Placeholder (giữ tương thích với frontend)
# ══════════════════════════════════════════════
@app.route('/api/ocr/scan', methods=['POST', 'OPTIONS'])
def api_ocr():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    return jsonify({"success": False, "message": "OCR chỉ khả dụng khi chạy server cục bộ có GPU."}), 200

@app.route('/api/export/docx', methods=['POST', 'OPTIONS'])
def api_export_docx():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    return jsonify({"error": "Export DOCX chỉ khả dụng khi chạy server cục bộ."}), 501

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 ThanhHoa Land AI Cloud Server đang khởi động trên port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
