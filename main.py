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

# ══════════════════════════════════════════════════════════════════
# CORS - Cho phép kết nối từ mọi Web & GitHub Pages
# ══════════════════════════════════════════════════════════════════
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        res = jsonify({"status": "ok"})
        res.headers['Access-Control-Allow-Origin'] = '*'
        res.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,x-goog-api-key'
        res.headers['Access-Control-Allow-Methods'] = 'GET,POST,DELETE,OPTIONS'
        return res, 200

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,x-goog-api-key'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,DELETE,OPTIONS'
    return response

# ══════════════════════════════════════════════════════════════════
# CẤU HÌNH API KEYS (GEMINI LÀ CHỦ ĐẠO - XOAY VÒNG 3 KEYS)
# ══════════════════════════════════════════════════════════════════
GEMINI_API_KEYS = [
    os.environ.get("GEMINI_API_KEY_1", "AQ.Ab8RN6K6uWSGUAgNhZthfDN38a9tSvzF8RyiaRNvzLTpR6WesA"),
    os.environ.get("GEMINI_API_KEY_2", "AQ.Ab8RN6JrZoDOoJYfBznhSQWpB6Lv9v93RwFPUtIr_Z7lFjqjVA"),
    os.environ.get("GEMINI_API_KEY_3", "AQ.Ab8RN6IzFDhmj0qZOJqlmdqYixwYUkBhxJc9ftlyJ9b1vnKbOQ"),
]
ZENMUX_API_KEY = os.environ.get("ZENMUX_API_KEY", "sk-ai-v1-4d7a69f58906d3b4983d5e6d326528bb9edcbbfabea0b7e440e3738c5c29b89d")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8128444329:AAEtIfC86tE43PYekXP7GlSUzDboiByCGpg")
ZALO_BOT_TOKEN = os.environ.get("ZALO_BOT_TOKEN", "EfVUmLxWFIMXorvotNYxHBWEBJDGOVHLvbAFCEViZpdjqmijKlHUOdesfyYaOqLD")

# ══════════════════════════════════════════════════════════════════
# SYSTEM PROMPT CHUẨN CỦA TRỢ LÝ PHÁP LÝ & ĐẤT ĐAI THANH HÓA
# ══════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """Bạn là 'Trợ lý Pháp lý & Đất đai Thanh Hóa' chuyên nghiệp, tận tâm, chính xác.

Nhiệm vụ:
Tư vấn, giải đáp pháp luật đất đai, thủ tục cấp giấy chứng nhận (Sổ đỏ), tách thửa, hợp thửa, chuyển mục đích sử dụng đất, thuế và nghĩa vụ tài chính, tranh chấp đất đai theo Luật Đất đai 2024, các Nghị định hướng dẫn thi hành (Nghị định 101/2024/NĐ-CP, Nghị định 49/2026/NĐ-CP, v.v.) và quy định của UBND tỉnh Thanh Hóa (Quyết định 18/2026/QĐ-UBND, Quyết định 2604/QĐ-VP).

Phong cách và quy chuẩn trả lời:
1. Rõ ràng, ngắn gọn, dễ hiểu, trình bày có gạch đầu dòng hoặc số thứ tự từng bước cụ thể.
2. Nêu rõ căn cứ pháp lý áp dụng (Luật Đất đai 2024, các Nghị định, Quyết định liên quan).
3. Hướng dẫn cụ thể cơ quan có thẩm quyền tiếp nhận hồ sơ (Bộ phận Một cửa cấp xã/phường hoặc Chi nhánh Văn phòng Đăng ký Đất đai nơi có đất).
4. Liệt kê rõ các thành phần hồ sơ, giấy tờ người dân cần chuẩn bị.
5. Giữ thái độ lịch sự, ân cần, chuẩn mực của cán bộ tư vấn pháp luật.

DỮ LIỆU ĐẶC BIỆT CẦN NẮM VỮNG VỀ TỈNH THANH HÓA:
- Tách thửa đất ở theo QĐ 18/2026/QĐ-UBND:
  + Phường (đô thị): diện tích >= 40m2, mặt tiền và chiều sâu >= 3.0m
  + Xã đồng bằng, trung du: diện tích >= 40m2, mặt tiền và chiều sâu >= 4.0m
  + Xã miền núi: diện tích >= 50m2, mặt tiền và chiều sâu >= 5.0m
  + Đất nông nghiệp: CLN, BHK >= 500m2; Đất lúa >= 1000m2; Đất rừng >= 3000m2
- Nghĩa vụ tài chính: Thuế TNCN chuyển nhượng 2%, Lệ phí trước bạ 0.5%
- Thẩm quyền cấp GCN theo QĐ 2604/QĐ-VP: Cấp xã tiếp nhận & xác nhận hiện trạng; Chi nhánh VPĐKĐĐ cấp huyện thẩm định và cấp đổi/cấp lại/biến động cho cá nhân; UBND cấp huyện cấp lần đầu."""

# ══════════════════════════════════════════════════════════════════
# AI ENGINE - GEMINI LÀ CHỦ ĐẠO -> DỰ PHÒNG ZENMUX -> DỰ PHÒNG KNOWLEDGE
# ══════════════════════════════════════════════════════════════════
def call_gemini_primary(question):
    """Ưu tiên số 1: Gọi Gemini API xoay vòng qua 3 API Keys và các model mới nhất."""
    gemini_models = [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash-lite",
        "gemini-flash-latest"
    ]
    
    for idx, key in enumerate(GEMINI_API_KEYS):
        if not key or len(key) < 10:
            continue
        key_label = f"Key #{idx+1}"
        for model in gemini_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = json.dumps({
                    "contents": [{
                        "parts": [{"text": f"{SYSTEM_PROMPT}\n\n[CÂU HỎI CỦA NGƯỜI DÂN]:\n{question}\n\n[TRẢ LỜI (100% TIẾNG VIỆT CHUẨN MỰC)]:"}]
                    }],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 3000
                    }
                }).encode("utf-8")
                
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json", "x-goog-api-key": key},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and parts[0].get("text", "").strip():
                            ans = parts[0]["text"].strip()
                            print(f"✅ Gemini API {key_label} ({model}) trả lời thành công!")
                            return ans, f"Google Gemini Flash ({model})"
            except Exception as e:
                print(f"⚠️ Gemini {key_label} model {model} lỗi/quota: {e}")
                continue

    return None, None

def call_zenmux_backup(question):
    """Ưu tiên số 2: Chỉ khi tất cả Gemini Keys hết quota mới chuyển sang ZenMux."""
    if not ZENMUX_API_KEY:
        return None, None
        
    zenmux_models = [
        "deepseek/deepseek-chat",
        "z-ai/glm-5.3-free",
        "dots-studio/dots3-note-prev"
    ]
    for m in zenmux_models:
        try:
            url = "https://zenmux.ai/api/v1/chat/completions"
            payload = json.dumps({
                "model": m,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question}
                ],
                "temperature": 0.2
            }).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Authorization": f"Bearer {ZENMUX_API_KEY}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ans = data["choices"][0]["message"]["content"].strip()
                ans = re.sub(r'<think>.*?</think>', '', ans, flags=re.DOTALL).strip()
                if len(ans) > 20:
                    print(f"✅ ZenMux Backup ({m}) phản hồi thành công!")
                    return ans, f"ZenMux AI Gateway ({m})"
        except Exception as e:
            print(f"⚠️ ZenMux backup {m} lỗi: {e}")
            continue

    return None, None

# ══════════════════════════════════════════════════════════════════
# DỮ LIỆU CỐ ĐỊNH THANH HÓA (DỰ PHÒNG KHI MẤT MẠNG / KHẨN CẤP)
# ══════════════════════════════════════════════════════════════════
KNOWLEDGE_RULES = [
    {
        "keywords": ["tách thửa", "diện tích tối thiểu", "hạn mức tách", "chia đất", "tách sổ", "tách đất"],
        "answer": (
            "Dạ, chào bạn! Về điều kiện và hạn mức tách thửa đất ở tại tỉnh Thanh Hóa, tôi xin tư vấn chi tiết như sau:\n\n"
            "1. **Căn cứ pháp lý áp dụng:**\n"
            "- Điều 220 Luật Đất đai 2024.\n"
            "- Quyết định số 18/2026/QĐ-UBND của UBND tỉnh Thanh Hóa quy định về hạn mức giao đất, diện tích tối thiểu được phép tách thửa.\n\n"
            "2. **Diện tích và kích thước tối thiểu được phép tách thửa đất ở:**\n"
            "- **Tại các Phường thuộc Đô thị:** Diện tích tối thiểu **≥ 40 m²**, chiều rộng mặt tiền và chiều sâu **≥ 3,0 m**.\n"
            "- **Tại các Xã thuộc khu vực Đồng bằng, Trung du & Ven biển:** Diện tích tối thiểu **≥ 40 m²**, chiều rộng mặt tiền và chiều sâu **≥ 4,0 m**.\n"
            "- **Tại các Xã thuộc 11 huyện Miền núi Thanh Hóa:** Diện tích tối thiểu **≥ 50 m²**, chiều rộng mặt tiền và chiều sâu **≥ 5,0 m**.\n"
            "- **Đất nông nghiệp:** Đất trồng cây lâu năm/hàng năm **≥ 500 m²**; Đất trồng lúa **≥ 1.000 m²**; Đất rừng sản xuất **≥ 3.000 m²**.\n\n"
            "3. **Điều kiện bắt buộc khác:**\n"
            "- Thửa đất đã có Giấy chứng nhận quyền sử dụng đất.\n"
            "- Đất không có tranh chấp, không bị kê biên thi hành án, còn thời hạn sử dụng.\n"
            "- Thửa đất mới hình thành và phần còn lại sau khi tách bắt buộc phải có lối đi kết nối với đường giao thông công cộng.\n\n"
            "4. **Cơ quan tiếp nhận hồ sơ:**\n"
            "- Bộ phận Một cửa cấp xã/phường nơi có thửa đất HOẶC Chi nhánh Văn phòng Đăng ký đất đai cấp huyện.\n\n"
            "5. **Hồ sơ cần chuẩn bị:**\n"
            "- Đơn xin tách thửa đất (Mẫu số 04/ĐK theo Nghị định 101/2024/NĐ-CP).\n"
            "- Bản gốc Giấy chứng nhận quyền sử dụng đất đã cấp.\n"
            "- Bản vẽ trích đo địa chính thửa đất xin tách."
        )
    },
    {
        "keywords": ["thuế", "lệ phí", "trước bạ", "tncn", "nghĩa vụ tài chính", "phí sang tên", "chi phí chuyển nhượng"],
        "answer": (
            "Dạ, chào bạn! Khi thực hiện thủ tục chuyển nhượng quyền sử dụng đất tại tỉnh Thanh Hóa, các bên có nghĩa vụ nộp các khoản tài chính sau:\n\n"
            "1. **Căn cứ pháp lý áp dụng:**\n"
            "- Luật Thuế Thu nhập Cá nhân.\n"
            "- Nghị định số 10/2022/NĐ-CP về Lệ phí trước bạ.\n"
            "- Nghị định 49/2026/NĐ-CP và Bảng giá đất hiện hành của UBND tỉnh Thanh Hóa.\n\n"
            "2. **Các khoản thuế và lệ phí bắt buộc:**\n"
            "- **Thuế Thu nhập Cá nhân (TNCN):** Mức nộp là **2%** trên giá trị chuyển nhượng ghi trong hợp đồng (hoặc theo Bảng giá đất của UBND tỉnh Thanh Hóa nếu giá trong hợp đồng thấp hơn quy định). Thông thường do bên bán nộp, trừ khi có thỏa thuận khác.\n"
            "- **Lệ phí Trước bạ:** Mức nộp là **0,5%** tính trên Giá trị chuyển quyền sử dụng đất (Diện tích × Giá đất theo Bảng giá đất của tỉnh). Thông thường do bên mua nộp.\n"
            "- **Phí thẩm định hồ sơ và lệ phí cấp đổi Sổ đỏ:** Từ 500.000đ - 2.000.000đ tùy theo địa bàn huyện/thị.\n\n"
            "3. **Trường hợp được Miễn thuế TNCN & Lệ phí trước bạ:**\n"
            "- Chuyển nhượng, tặng cho, thừa kế giữa những người thân thích trong gia đình (Vợ - chồng; Cha/mẹ - con; Ông/bà - cháu; Anh/chị/em ruột) kèm theo giấy tờ chứng minh quan hệ nhân thân (Mẫu số 03/BĐS-TNCN).\n\n"
            "4. **Cơ quan tiếp nhận và thẩm định:**\n"
            "- Chi cục Thuế khu vực cấp huyện thông qua Bộ phận Một cửa nơi nộp hồ sơ đăng ký biến động đất đai."
        )
    }
]

def search_fallback_knowledge(question):
    q_lower = (question or "").lower()
    best_match = None
    max_hits = 0
    for rule in KNOWLEDGE_RULES:
        hits = sum(1 for kw in rule["keywords"] if kw in q_lower)
        if hits > max_hits:
            max_hits = hits
            best_match = rule["answer"]
    return best_match if max_hits > 0 else None

def process_question_pipeline(question):
    """Pipeline xử lý: Gemini (Chủ đạo) -> ZenMux (Dự phòng) -> Knowledge Base"""
    # 1. CHỦ ĐẠO: Gọi Gemini API với các model phân tích sâu
    ans, model_name = call_gemini_primary(question)
    if ans:
        return ans, model_name

    # 2. DỰ PHÒNG 1: Gọi ZenMux khi Gemini hết token
    ans, model_name = call_zenmux_backup(question)
    if ans:
        return ans, model_name

    # 3. DỰ PHÒNG 2: Tra cứu CSDL chuẩn Thanh Hóa
    ans = search_fallback_knowledge(question)
    if ans:
        return ans, "CSDL Pháp lý Thanh Hóa (QĐ 18/2026 & QĐ 2604)"

    # 4. Phản hồi định hướng chuẩn mực
    return (
        "Dạ, chào bạn! Đối với nội dung bạn quan tâm, tôi xin tư vấn theo quy định hiện hành:\n\n"
        "1. **Căn cứ pháp lý:** Áp dụng Luật Đất đai 2024, Nghị định 101/2024/NĐ-CP, Nghị định 49/2026/NĐ-CP và Quyết định số 18/2026/QĐ-UBND tỉnh Thanh Hóa.\n"
        "2. **Cơ quan tiếp nhận:** Bạn vui lòng liên hệ Bộ phận Một cửa UBND cấp xã/phường nơi có đất hoặc Chi nhánh Văn phòng Đăng ký đất đai cấp huyện để được tiếp nhận hồ sơ trích lục địa chính và thẩm định cụ thể.\n"
        "3. **Hồ sơ cơ bản:** Đơn đăng ký biến động, bản gốc Giấy chứng nhận quyền sử dụng đất, bản sao CCCD và các giấy tờ chứng minh nguồn gốc đất."
    ), "Trợ lý Pháp lý Thanh Hóa"

# ══════════════════════════════════════════════════════════════════
# API ROUTES
# ══════════════════════════════════════════════════════════════════
@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
@app.route('/api/status', methods=['GET'])
def health():
    return jsonify({
        "status": "online",
        "service": "ThanhHoa Land AI v2026",
        "api_chat": "/api/chat [POST]",
        "telegram": "@TroLyLuatbot",
        "primary_model": "Google Gemini Flash (Primary) + ZenMux (Fallback)",
        "prompt": "Tro Ly Phap Ly & Dat Dai Thanh Hoa Chuyen Nghiep"
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
    answer, model_used = process_question_pipeline(question)

    return jsonify({
        "answer": answer,
        "model": f"🤖 {model_used}",
        "session_id": session_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200

# ══════════════════════════════════════════════════════════════════
# TELEGRAM & ZALO WEBHOOKS
# ══════════════════════════════════════════════════════════════════
def send_telegram(chat_id, text):
    try:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = json.dumps({"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown", "disable_web_page_preview": True}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10):
                pass
    except Exception as e:
        print(f"⚠️ Telegram send error: {e}")

@app.route('/api/telegram/webhook', methods=['GET', 'POST', 'OPTIONS'])
def telegram_webhook():
    if request.method in ('GET', 'OPTIONS'):
        return jsonify({"status": "webhook active", "bot": "@TroLyLuatbot"}), 200
    data = request.get_json(silent=True) or {}
    msg = data.get("message") or data.get("edited_message")
    if msg:
        chat_id = msg.get("chat", {}).get("id")
        text = (msg.get("text") or "").strip()
        if chat_id and text:
            def _reply():
                if text == "/start":
                    send_telegram(chat_id, "👋 Xin chào! Tôi là Trợ lý Pháp lý & Đất đai Thanh Hóa (@TroLyLuatbot).\nTôi sẵn sàng tư vấn chi tiết về thủ tục cấp Sổ đỏ, tách thửa, chuyển mục đích, thuế đất đai theo Luật Đất đai 2024 & Quyết định 18/2026/QĐ-UBND.")
                else:
                    ans, _ = process_question_pipeline(text)
                    send_telegram(chat_id, ans)
            threading.Thread(target=_reply, daemon=True).start()
    return jsonify({"ok": True}), 200

@app.route('/api/zalo/webhook', methods=['GET', 'POST', 'OPTIONS'])
def zalo_webhook():
    if request.method == 'GET':
        challenge = request.args.get('hub.challenge') or request.args.get('challenge')
        if challenge:
            return challenge, 200
        return jsonify({"status": "active"}), 200
    return jsonify({"status": "received"}), 200

@app.route('/api/ocr/scan', methods=['POST', 'OPTIONS'])
def api_ocr():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    return jsonify({"success": False, "message": "OCR khả dụng trên máy trạm cục bộ."}), 200

@app.route('/api/export/docx', methods=['POST', 'OPTIONS'])
def api_export_docx():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    return jsonify({"error": "Export DOCX khả dụng trên máy trạm cục bộ."}), 501

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
