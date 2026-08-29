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
# CẤU HÌNH API KEYS & TOKENS
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
# CƠ SỞ DỮ LIỆU PHÁP LÝ CHUYÊN SÂU TỈNH THANH HÓA (IN-MEMORY RAG)
# ══════════════════════════════════════════════════════════════════
KNOWLEDGE_RULES = [
    {
        "keywords": ["tách thửa", "diện tích tối thiểu", "hạn mức tách", "chia đất", "tách sổ", "tách đất"],
        "answer": (
            "### 🏛️ Quy định về Hạn mức & Điều kiện Tách thửa Đất ở tỉnh Thanh Hóa\n\n"
            "Căn cứ **Luật Đất đai 2024 (Điều 220)** và **Quyết định số 18/2026/QĐ-UBND** của UBND tỉnh Thanh Hóa:\n\n"
            "#### 1️⃣ Diện tích và Kích thước tối thiểu được phép tách thửa đất ở:\n"
            "* **Tại các Phường (Đô thị):**\n"
            "  - Diện tích tối thiểu: **≥ 40 m²**\n"
            "  - Chiều rộng mặt tiền và chiều sâu: **≥ 3,0 m**\n"
            "* **Tại các Xã thuộc khu vực Đồng bằng, Trung du & Ven biển:**\n"
            "  - Diện tích tối thiểu: **≥ 40 m²**\n"
            "  - Chiều rộng mặt tiền và chiều sâu: **≥ 4,0 m**\n"
            "* **Tại các Xã thuộc 11 huyện Miền núi Thanh Hóa:**\n"
            "  - Diện tích tối thiểu: **≥ 50 m²**\n"
            "  - Chiều rộng mặt tiền và chiều sâu: **≥ 5,0 m**\n\n"
            "#### 2️⃣ Đối với Đất Nông nghiệp:\n"
            "* Đất trồng cây lâu năm, hàng năm: **≥ 500 m²**\n"
            "* Đất trồng lúa: **≥ 1.000 m²**\n"
            "* Đất rừng sản xuất: **≥ 3.000 m²**\n\n"
            "#### 3️⃣ Điều kiện bắt buộc khi tách thửa:\n"
            "1. Thửa đất đã được cấp Giấy chứng nhận (Sổ đỏ/Sổ hồng).\n"
            "2. Thửa đất không có tranh chấp, không bị kê biên để thi hành án.\n"
            "3. Thửa đất còn trong thời hạn sử dụng đất.\n"
            "4. Thửa đất mới hình thành và thửa đất còn lại sau khi tách phải có lối đi kết nối với đường giao thông công cộng hiện có."
        )
    },
    {
        "keywords": ["thuế", "lệ phí", "trước bạ", "tncn", "nghĩa vụ tài chính", "tiền sử dụng đất", "phí sang tên", "chi phí chuyển nhượng"],
        "answer": (
            "### 💰 Nghĩa vụ Tài chính khi Chuyển nhượng / Cấp GCN Đất đai\n\n"
            "Căn cứ **Luật Thuế TNCN**, **Nghị định 10/2022/NĐ-CP**, **Nghị định 49/2026/NĐ-CP** và Bảng giá đất tỉnh Thanh Hóa:\n\n"
            "#### 1️⃣ Thuế Thu nhập Cá nhân (TNCN) khi chuyển nhượng BĐS:\n"
            "* **Mức thuế:** **2%** trên giá trị chuyển nhượng ghi trong hợp đồng (hoặc theo Bảng giá đất của UBND tỉnh Thanh Hóa nếu giá hợp đồng thấp hơn).\n"
            "* **Miễn thuế:** Chuyển nhượng, tặng cho, thừa kế giữa những người có quan hệ huyết thống, hôn nhân (Vợ - chồng; Cha/mẹ - con; Ông/bà - cháu; Anh/chị/em ruột) theo Mẫu số 03/BĐS-TNCN.\n\n"
            "#### 2️⃣ Lệ phí Trước bạ nhà đất:\n"
            "* **Mức nộp:** **0,5%** tính trên Giá trị quyền sử dụng đất (Diện tích × Giá đất theo Bảng giá đất tỉnh Thanh Hóa).\n"
            "* **Miễn lệ phí:** Tặng cho, thừa kế giữa người thân ruột thịt theo quy định.\n\n"
            "#### 3️⃣ Các khoản phí & lệ phí khác:\n"
            "* **Phí thẩm định hồ sơ:** Từ 500.000đ - 2.000.000đ tùy diện tích và địa bàn huyện/thị.\n"
            "* **Lệ phí cấp đổi/cấp mới GCN:** 50.000đ - 100.000đ/GCN.\n"
            "* **Phí trích đo địa chính:** (Nếu phải đo đạc chỉnh lý thửa đất)."
        )
    },
    {
        "keywords": ["cấp sổ", "cấp gcn", "lần đầu", "hồ sơ cấp gcn", "thủ tục cấp sổ đỏ", "chưa có sổ", "mẫu 29"],
        "answer": (
            "### 📋 Thủ tục & Hồ sơ Cấp Giấy chứng nhận (Sổ đỏ) Lần đầu tỉnh Thanh Hóa\n\n"
            "Căn cứ **Luật Đất đai 2024 (Điều 138-140)**, **Nghị định 101/2024/NĐ-CP** và **Quyết định số 2604/QĐ-VP** tỉnh Thanh Hóa:\n\n"
            "#### 1️⃣ Thành phần Hồ sơ cần chuẩn bị:\n"
            "1. **Đơn đăng ký, cấp Giấy chứng nhận:** Mẫu số **04/ĐK** (theo NĐ 101/2024) hoặc Mẫu số 29 (theo QĐ 2604).\n"
            "2. **Giấy tờ chứng minh nguồn gốc sử dụng đất:** Một trong các loại giấy tờ quy định tại Điều 137 Luật Đất đai 2024 (giấy tờ trước 15/10/1993, giấy tờ giao đất đúng/không đúng thẩm quyền...).\n"
            "3. **Sơ đồ trích đo địa chính thửa đất** do đơn vị đo đạc có tư cách pháp nhân lập hoặc do Chi nhánh VPĐKĐĐ trích lục.\n"
            "4. **Tờ khai nghĩa vụ tài chính:** Tờ khai Lệ phí trước bạ (Mẫu 01/LPTB), Tờ khai Tiền sử dụng đất.\n"
            "5. Bản sao CCCD, Giấy xác nhận tình trạng hôn nhân của người sử dụng đất.\n\n"
            "#### 2️⃣ Nơi nộp hồ sơ & Thời hạn giải quyết:\n"
            "* **Nơi nộp:** Bộ phận Một cửa UBND cấp xã nơi có đất HOẶC Trung tâm Hành chính công / Chi nhánh VPĐKĐĐ cấp huyện.\n"
            "* **Thời hạn giải quyết:** Không quá **30 ngày làm việc** (đối với miền núi không quá 40 ngày làm việc)."
        )
    },
    {
        "keywords": ["thẩm quyền", "ai cấp", "ubnd xã", "sở tài nguyên", "văn phòng đăng ký", "chi nhánh", "phân cấp"],
        "answer": (
            "### 🏛️ Thẩm quyền Cấp Giấy chứng nhận (GCN) theo Quyết định 2604/QĐ-VP tỉnh Thanh Hóa\n\n"
            "Căn cứ **Điều 136 Luật Đất đai 2024** và quy định phân cấp tại **Quyết định 2604/QĐ-VP**:\n\n"
            "#### 1️⃣ Thẩm quyền cấp GCN lần đầu:\n"
            "* **UBND cấp huyện:** Cấp GCN lần đầu cho cá nhân, hộ gia đình, cộng đồng dân cư trong nước.\n"
            "* **UBND cấp tỉnh (hoặc ủy quyền cho Sở TN&MT):** Cấp GCN cho tổ chức trong nước, tổ chức tôn giáo, người gốc Việt Nam định cư ở nước ngoài, tổ chức có vốn đầu tư nước ngoài.\n\n"
            "#### 2️⃣ Thẩm quyền cấp GCN khi đăng ký biến động (chuyển nhượng, tặng cho, tách thửa, cấp đổi, cấp lại):\n"
            "* **Chi nhánh Văn phòng Đăng ký đất đai cấp huyện:** Thực hiện cấp đổi, cấp lại, đăng ký biến động cho cá nhân, hộ gia đình.\n"
            "* **Văn phòng Đăng ký đất đai tỉnh Thanh Hóa:** Thực hiện cho các tổ chức, doanh nghiệp."
        )
    },
    {
        "keywords": ["chuyển mục đích", "lên thổ cư", "đất vườn", "đất nông nghiệp sang đất ở", "chuyển đất nông nghiệp"],
        "answer": (
            "### 🔄 Thủ tục & Tiền sử dụng đất khi Chuyển mục đích sang Đất ở (Thổ cư)\n\n"
            "Căn cứ **Luật Đất đai 2024 (Điều 121, 122)** và **Nghị định 49/2026/NĐ-CP**:\n\n"
            "#### 1️⃣ Điều kiện cho phép chuyển mục đích:\n"
            "1. Phù hợp với **Quy hoạch sử dụng đất cấp huyện** đã được UBND tỉnh Thanh Hóa phê duyệt.\n"
            "2. Có đơn xin chuyển mục đích sử dụng đất theo quy định.\n\n"
            "#### 2️⃣ Cách tính Tiền sử dụng đất phải nộp:\n"
            "$$\\text{Tiền sử dụng đất} = \\text{Giá đất ở theo Bảng giá đất} - \\text{Giá đất nông nghiệp tương ứng}$$\n"
            "* Tính theo Bảng giá đất hiện hành của UBND tỉnh Thanh Hóa nhân với diện tích xin chuyển mục đích.\n\n"
            "#### 3️⃣ Hồ sơ nộp tại:\n"
            "* Phòng Tài nguyên và Môi trường / Trung tâm Phục vụ hành chính công cấp huyện nơi có đất."
        )
    }
]

def search_local_rules(question):
    q_lower = (question or "").lower()
    best_match = None
    max_hits = 0
    for rule in KNOWLEDGE_RULES:
        hits = sum(1 for kw in rule["keywords"] if kw in q_lower)
        if hits > max_hits:
            max_hits = hits
            best_match = rule["answer"]
    return best_match if max_hits > 0 else None

# ══════════════════════════════════════════════════════════════════
# AI ENGINE - GEMINI & ZENMUX MULTI-TIER
# ══════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """Bạn là Chuyên gia Trợ lý AI Pháp lý Đất đai tỉnh Thanh Hóa (ThanhHoa Land AI).

QUY CHUẨN TRẢ LỜI BẮT BUỘC:
1. BẮT BUỘC trả lời 100% bằng TIẾNG VIỆT CHUẨN MỰC, đúng thuật ngữ pháp lý.
2. Trình bày rõ ràng theo từng phần:
   - 🏛️ Căn cứ pháp lý: Luật Đất đai 2024, NĐ 101/2024, NĐ 102/2024, NĐ 49/2026, Quyết định 18/2026/QĐ-UBND và Quyết định 2604/QĐ-VP tỉnh Thanh Hóa.
   - 📋 Quy định cụ thể và hạn mức chi tiết.
   - 📝 Hướng dẫn các bước nộp hồ sơ, giấy tờ cần chuẩn bị.
3. Luôn bám sát địa bàn 27 huyện, thị xã, thành phố của tỉnh Thanh Hóa."""

def call_ai_cloud(question):
    # 1. Thử ZenMux Multi-Model Gateway
    zenmux_models = ["deepseek/deepseek-chat", "z-ai/glm-5.3-free", "dots-studio/dots3-note-prev"]
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
            req = urllib.request.Request(url, data=payload, headers={
                "Authorization": f"Bearer {ZENMUX_API_KEY}",
                "Content-Type": "application/json"
            }, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ans = data["choices"][0]["message"]["content"].strip()
                ans = re.sub(r'<think>.*?</think>', '', ans, flags=re.DOTALL).strip()
                if len(ans) > 20:
                    return ans, f"ZenMux Cloud ({m})"
        except Exception as e:
            print(f"⚠️ ZenMux {m} error: {e}")
            continue

    # 2. Thử Gemini API
    for key in GEMINI_API_KEYS:
        if not key or len(key) < 10:
            continue
        for model in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = json.dumps({
                    "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nCÂU HỎI: {question}\n\nTRẢ LỜI (100% Tiếng Việt):"}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}
                }).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and parts[0].get("text", "").strip():
                            return parts[0]["text"].strip(), f"Gemini Cloud ({model})"
            except Exception as e:
                print(f"⚠️ Gemini {model} error: {e}")
                continue

    return None, None

def process_question(question):
    # Ưu tiên 1: Tra cứu CSDL Pháp lý Thanh Hóa chuẩn xác
    local_ans = search_local_rules(question)
    if local_ans:
        return local_ans, "CSDL Pháp lý Thanh Hóa (QĐ 18/2026 & QĐ 2604)"

    # Ưu tiên 2: Gọi AI Cloud (ZenMux / Gemini)
    ai_ans, model_name = call_ai_cloud(question)
    if ai_ans:
        return ai_ans, model_name

    # Dự phòng
    return (
        "### 🏛️ Tư vấn Pháp lý Đất đai Thanh Hóa\n"
        "Đối với câu hỏi của bạn, theo quy định của **Luật Đất đai 2024**, **Quyết định 18/2026/QĐ-UBND** và **Quyết định 2604/QĐ-VP** tỉnh Thanh Hóa:\n\n"
        "1. Người sử dụng đất cần nộp hồ sơ tại **Bộ phận Một cửa UBND cấp xã** hoặc **Chi nhánh Văn phòng Đăng ký đất đai** nơi có thửa đất.\n"
        "2. Cán bộ địa chính sẽ tiếp nhận, kiểm tra trích lục bản đồ địa chính và thẩm định thực địa.\n"
        "3. Sau khi hoàn thành nghĩa vụ tài chính (thuế, lệ phí), cơ quan có thẩm quyền sẽ cấp Giấy chứng nhận theo thời hạn quy định."
    ), "Hệ thống Pháp lý Thanh Hóa"

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
        "model": "Knowledge RAG + ZenMux + Gemini Multi-Tier"
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
    answer, model_used = process_question(question)

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
                    send_telegram(chat_id, "👋 Xin chào! Tôi là Trợ lý AI Pháp lý Đất đai Thanh Hóa (@TroLyLuatbot). Hãy đặt câu hỏi về thủ tục đất đai, tách thửa, cấp sổ...")
                else:
                    ans, _ = process_question(text)
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
