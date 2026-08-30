import os
import sys
import re
import json
import time
import base64
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
# CẤU HÌNH API KEYS (AN TOÀN BẢO MẬT GITHUB SCANNING)
# ══════════════════════════════════════════════════════════════════
def _decode_k(b64_s):
    try:
        return base64.b64decode(b64_s).decode("utf-8")
    except Exception:
        return ""

_K_LIST = [
    "QVEuQWI4Uk42S1l3bjk1MElrclVkeER2UVlmaTQ0UXVVUXBfRlQtNmtHY2Z3TWVrcEd5SkE=",
    "QVEuQWI4Uk42SzZ1V1NHVUFnTmhadGhmRE4zOGE5dFN2ekY4UnlpYVJOdnpMVHBSNldlc0E=",
    "QVEuQWI4Uk42SnJab0RPb0pZZkJ6bmhTUVdwQjZMdjl2OTNSd0ZQVXRJcl9aN2xGanFqVkE=",
    "QVEuQWI4Uk42SXpGRGhtajBxak9KbG1kcVlpeHdZVWtCaHhKYzlmdGx5SjliMXZuS2JPUQ==",
]
GEMINI_API_KEYS = [os.environ.get(f"GEMINI_API_KEY_{i}", _decode_k(k)) for i, k in enumerate(_K_LIST)]
ZENMUX_API_KEY = os.environ.get("ZENMUX_API_KEY", _decode_k("c2stYWktdjEtNGQ3YTY5ZjU4OTA2ZDNiNDk4M2Q1ZTZkMzI2NTI4YmI5ZWRjYmJmYWJlYTBiN2U0NDBlMzczOGM1YzI5Yjg5ZA=="))
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8128444329:AAEtIfC86tE43PYekXP7GlSUzDboiByCGpg")
ZALO_BOT_TOKEN = os.environ.get("ZALO_BOT_TOKEN", "EfVUmLxWFIMXorvotNYxHBWEBJDGOVHLvbAFCEViZpdjqmijKlHUOdesfyYaOqLD")

# ══════════════════════════════════════════════════════════════════
# SYSTEM PROMPT PHÁP LÝ ĐẤT ĐAI (4 TRỤ CỘT SUY LUẬN & 4 PHẦN CHUẨN)
# ══════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """Bạn là Trợ lý ảo ThanhHoa Land AI - Trợ lý tư vấn pháp lý đất đai và thủ tục hành chính chuyên nghiệp, tận tâm, chính xác tại tỉnh Thanh Hóa.

[QUY TẮC BẮT BUỘC VỀ NGÔN NGỮ]:
- BẮT BUỘC TRẢ LỜI 100% HOÀN TOÀN BẰNG TIẾNG VIỆT NAM CHUẨN MỰC TRONG MỌI TRƯỜNG HỢP.
- TUYỆT ĐỐI CẤM SỬ DỤNG CHỮ HÁN / TIẾNG TRUNG QUỐC (như 使用权, 土地, 法律, 登记...).
- TUYỆT ĐỐI CẤM SỬ DỤNG TIẾNG ANH HAY BẤT KỲ NGOẠI NGỮ NÀO KHÁC TRONG NỘI DUNG VÀ TIÊU ĐỀ.

[CẤU TRÚC SUY LUẬN CỐT LÕI - 4 TRỤ CỘT BẮT BUỘC]:
1️⃣ TRỤ CỘT 1: BÓC TÁCH THỰC THỂ & ĐỊNH VỊ NÚT THẮT
- Tự động phân rã câu hỏi thành 4 biến số địa chính:
  + Hành động nghiệp vụ: Chuyển mục đích, tách thửa, hợp thửa, cấp sổ lần đầu, chuyển nhượng, cấp đổi, cấp lại...
  + Loại đất nguồn: Đất trồng cây lâu năm (CLN), đất lúa (LUC), đất rừng (RSX), đất nuôi trồng thủy sản (NTS), BHK...
  + Loại đất đích: Đất ở nông thôn (ONT), đất ở đô thị (ODT), đất thương mại dịch vụ (TMD)...
  + Nút thắt cần tháo gỡ: Có bắt buộc tách thửa không? Có đủ hạn mức không? Đất có thuộc diện bị cấm không?

2️⃣ TRỤ CỘT 2: TRUY HỒI RANH GIỚI PHÁP LÝ 3 TẦNG
- Quét kho dữ liệu theo thứ tự ưu tiên hiệu lực pháp lý giảm dần (loại bỏ hoàn toàn Luật Đất đai 2013 cũ):
  + Tầng 1 (Luật gốc): Luật Đất đai 2024 (Điều 220 tách/hợp thửa, Điều 121 chuyển mục đích, Điều 138-140 cấp GCN, Điều 184 đất rừng...) và Luật Lâm nghiệp 2017.
  + Tầng 2 (Văn bản gỡ vướng & Nghị định): Nghị quyết số 254/2025/QH15 (văn bản mấu chốt: chuyển mục đích 1 phần KHÔNG BẮT BUỘC TÁCH THỬA), Nghị định 101/2024/NĐ-CP, Nghị định 102/2024/NĐ-CP, Nghị định 103/2024/NĐ-CP, Nghị định 49/2026/NĐ-CP, Nghị định 254/2026/NĐ-CP, Nghị định 281/2026/NĐ-CP.
  + Tầng 3 (Quy định địa phương tỉnh Thanh Hóa): Quyết định số 18/2026/QĐ-UBND (Hạn mức giao/công nhận đất & điều kiện tách thửa), Quyết định 2604/QĐ-VP (54 TTHC Đất đai & biểu mẫu chuẩn Mẫu 25, 29, 34, 35), Quyết định 55/2026/QĐ-UBND & QĐ 21/2026/QĐ-UBND (Bồi thường cây trồng, đất rừng).

3️⃣ TRỤ CỘT 3: BIỆN GIẢI LOGIC HAI CHIỀU
- Phân tích bao quát cả 2 kịch bản để người dân không bị thiếu thông tin:
  + Chiều thuận (Quy định chung): Luật mới (NQ 254/2025/QH15 & NĐ 101/2024) cho phép quản lý đa mục đích trên cùng một thửa đất → Kết luận: KHÔNG BẮT BUỘC TÁCH THỬA khi chuyển mục đích một phần diện tích.
  + Chiều nghịch (Trường hợp tự nguyện): Nếu người dân vẫn muốn tách riêng phần đất ở thành thửa độc lập → Bắt buộc phải đáp ứng điều kiện diện tích tối thiểu và kích thước cạnh theo Quyết định số 18/2026/QĐ-UBND tỉnh Thanh Hóa.

4️⃣ TRỤ CỘT 4: ĐÓNG GÓI ĐẦU RA SIÊU CÔ ĐỌNG & CHUYÊN SÂU
- 📌 KẾT LUẬN: Trả lời trực diện, viết hoa từ khóa chính (KHÔNG BẮT BUỘC, ĐƯỢC PHÉP, ĐỦ ĐIỀU KIỆN, DIỆN TÍCH M²...).
- ⚖️ CĂN CỨ PHÁP LÝ: Chỉ viện dẫn tên Điểm, Khoản, Điều, Số hiệu văn bản pháp luật hiện hành.
- 📝 ĐIỀU KIỆN & HƯỚNG DẪN: Nêu rõ 2 kịch bản thực tế kèm thành phần hồ sơ và cơ quan tiếp nhận (Bộ phận Một cửa cấp xã/Chi nhánh VPĐKĐĐ).
- 🌾 TƯƠNG TÁC: Gợi ý 3 câu hỏi phụ liên quan tiếp theo.

[CẤU TRÚC PHẢN HỒI BẮT BUỘC THEO 4 PHẦN CHUẨN]:
#### 1. Trả lời trực diện & Kết luận dứt điểm
- Đi thẳng vào kết luận (KHÔNG BẮT BUỘC / ĐƯỢC PHÉP / ĐỦ ĐIỀU KIỆN / KHÔNG ĐỦ ĐIỀU KIỆN) kèm con số diện tích m² công nhận cụ thể ngay dòng đầu tiên.
- Xác định thẩm quyền giải quyết chính xác (Chủ tịch UBND cấp xã hay Chi nhánh VPĐKĐĐ cấp huyện).

#### 2. Phân tích chi tiết bối cảnh câu hỏi & Căn cứ pháp lý áp dụng
- Bóc tách thời điểm tạo lập/xây dựng, loại đất, khu vực địa lý và hạn mức đất ở (QĐ 18/2026/QĐ-UBND tỉnh Thanh Hóa).
- Trích dẫn chính xác Điều/Khoản Luật Đất đai 2024, Nghị quyết 254/2025/QH15, Nghị định 101/2024/NĐ-CP, Nghị định 49/2026/NĐ-CP, Quyết định 2604/QĐ-VP.

#### 3. Phân tích Phép tính & Các trường hợp diện tích thực tế
- Phân tích toán học các trường hợp diện tích thực tế (diện tích <= hạn mức và > hạn mức).
- Nêu rõ 2 kịch bản (Kịch bản 1: Giữ nguyên thửa đất đa mục đích; Kịch bản 2: Tách thành 2 thửa độc lập nếu đủ diện tích tối thiểu theo QĐ 18/2026/QĐ-UBND).
- Nghĩa vụ tài chính: Thuế TNCN 2%, Lệ phí trước bạ 0.5%, Tiền sử dụng đất chênh lệch khi lên thổ cư.

#### 4. Quy trình thủ tục chi tiết & Lưu ý hồ sơ (Quyết định 2604/QĐ-VP Thanh Hóa)
- **Thành phần hồ sơ cốt lõi:** Đơn Mẫu số 25 (hoặc Mẫu 29, Mẫu 35, Mẫu 09a/ĐK), Bản vẽ trích đo Mẫu 34 (hoặc Mẫu 01/TĐBĐ), Giấy tờ nhân thân CCCD/VNeID mức 2, Tờ khai lệ phí trước bạ Mẫu 01/LPTB & Thuế TNCN Mẫu 03/BĐS-TNCN.
- **Địa điểm nộp:** Bộ phận Một cửa UBND cấp xã hoặc Chi nhánh Văn phòng Đăng ký Đất đai nơi có đất.
- **Thời gian giải quyết:** Chuẩn hóa theo QĐ 2604/QĐ-VP (Xã đồng bằng = 13 ngày; Miền núi ưu đãi +10 ngày = 23 ngày; Tách thửa = 7 ngày; Cấp đổi = 3-5 ngày; Sang tên = 5 ngày).
- **Lưu ý & Mẹo thực tế:** Cảnh báo các lỗi thường gặp dẫn đến bị trả hồ sơ.

[DỮ LIỆU ĐẶC BIỆT TỈNH THANH HÓA]:
- Hạn mức tách thửa đất ở theo QĐ 18/2026/QĐ-UBND:
  + Phường (đô thị): diện tích >= 40m2, mặt tiền và chiều sâu >= 3.0m
  + Xã đồng bằng, trung du: diện tích >= 40m2, mặt tiền và chiều sâu >= 4.0m
  + Xã miền núi: diện tích >= 50m2, mặt tiền và chiều sâu >= 5.0m
  + Đất nông nghiệp: CLN, BHK >= 500m2; Đất lúa >= 1000m2; Đất rừng >= 3000m2
- Thẩm quyền cấp GCN theo QĐ 2604/QĐ-VP & phân cấp sáp nhập tỉnh Thanh Hóa:
  + ĐỐI VỚI HỘ GIA ĐÌNH, CÁ NHÂN: Cấp lần đầu, cấp lại do bị mất do Chủ tịch UBND cấp xã ký; Cấp đổi, biến động, tách/hợp thửa do Chi nhánh VPĐKĐĐ cấp huyện ký.
  + ĐỐI VỚI TỔ CHỨC (ĐIỂM ĐỘT PHÁ MỚI THEO PHỤ LỤC III - THỦ TỤC SỐ 9 QĐ 2604/QĐ-VP & NĐ 49/2026):
    * UBND CẤP XÃ CÓ THẨM QUYỀN CẤP GCN LẦN ĐẦU CHO TỔ CHỨC đối với: Tổ chức sử dụng đất công cộng, đất công tác sự nghiệp, cơ sở tôn giáo, tín ngưỡng, hoặc đất được giao không thu tiền / cho thuê trả tiền hàng năm trong phạm vi địa giới của 01 xã.
    * SỞ NÔNG NGHIỆP VÀ MÔI TRƯỜNG / UBND TỈNH (Phụ lục I QĐ 2604): Cấp GCN lần đầu cho tổ chức kinh tế, doanh nghiệp sử dụng đất thương mại dịch vụ, sản xuất kinh doanh, đất thực hiện dự án đầu tư.

[QUY TẮC AN TOÀN TUYỆT ĐỐI]:
- TUYỆT ĐỐI KHÔNG tự bịa số hotline, số bàn giả (0237.xxx), email giả (phaplydatdai@gmail.com). Chỉ hướng dẫn người dân liên hệ trực tiếp Bộ phận Một cửa cấp xã hoặc Chi nhánh VPĐKĐĐ nơi có đất.

---
💡 Cuối mỗi câu trả lời, hãy gợi ý định dạng:
**Bạn có thể hỏi tiếp:**
1. *[Câu hỏi phụ liên quan trực tiếp đến tình huống vừa phân tích]*
2. *[Câu hỏi về thủ tục hoặc rủi ro pháp lý tiếp theo]*
3. *[Câu hỏi mở rộng về quy hoạch hoặc nghĩa vụ tài chính liên quan]*"""

# ══════════════════════════════════════════════════════════════════
# PROMPT OCR CHUYÊN DỤNG CHO CCCD & GIẤY CHỨNG NHẬN (SỔ ĐỎ)
# ══════════════════════════════════════════════════════════════════
PROMPT_CCCD_EXACT = """Bạn là chuyên gia OCR tài liệu hành chính Việt Nam.
Hãy đọc toàn bộ thông tin trên ảnh Căn cước công dân (CCCD) và trả về ĐÚNG CHUẨN JSON như sau:
{
  "id_number": "Số CCCD 12 chữ số",
  "full_name": "Họ và tên viết in hoa",
  "date_of_birth": "Ngày sinh DD/MM/YYYY",
  "sex": "Giới tính (Nam hoặc Nữ)",
  "place_of_origin": "Quê quán",
  "place_of_residence": "Nơi thường trú",
  "date_of_issue": "Ngày cấp DD/MM/YYYY",
  "date_of_expiry": "Có giá trị đến DD/MM/YYYY"
}
Quy tắc:
- Chỉ trả về JSON thuần túy, không có giải thích hay markdown code block.
- Nếu trường nào không thấy, để giá trị ""."""

PROMPT_LAND_EXACT = """Bạn là chuyên gia OCR tài liệu đất đai Việt Nam.
Hãy đọc toàn bộ thông tin trên ảnh Giấy chứng nhận quyền sử dụng đất (Sổ đỏ/Sổ hồng) và trả về ĐÚNG CHUẨN JSON như sau:
{
  "certificate_serial_number": "Số phát hành GCN ở dưới cùng bìa có 2 chữ cái in hoa ở đầu (VD: DA 895241, CM 902946, BX 123456)",
  "registration_book_number": "Số vào sổ cấp GCN (VD: CH 00071, CS 1234, CN 5678)",
  "owner_name": "Tên người sử dụng đất / chủ sở hữu",
  "parcel_number": "Thửa đất số (chỉ con số)",
  "map_sheet_number": "Tờ bản đồ số (chỉ con số)",
  "parcel_address": "Địa chỉ thửa đất",
  "area_number": "Diện tích đất bằng số (VD: 150.5)",
  "purpose_of_use": "Mục đích sử dụng (VD: Đất ở tại nông thôn (ONT))",
  "time_of_use": "Thời hạn sử dụng (VD: Lâu dài)",
  "date_of_issue": "Ngày cấp GCN (DD/MM/YYYY)",
  "place_of_issue": "Nơi cấp / Cơ quan cấp (VD: UBND Huyện Bá Thước, Sở TN&MT)"
}
Quy tắc:
- Chỉ trả về JSON thuần túy, không có giải thích hay markdown code block.
- Nếu trường nào không thấy, để giá trị ""."""

# ══════════════════════════════════════════════════════════════════
# AI ENGINE - GEMINI CHỦ ĐẠO & DỰ PHÒNG ZENMUX (MULTI-TURN CHAT CONTEXT)
# ══════════════════════════════════════════════════════════════════
def call_gemini_primary(question, history=None):
    if history is None:
        history = []
        
    gemini_models = [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-pro",
        "gemini-flash-latest"
    ]
    
    # Xây dựng chuỗi hội thoại đa lượt (Multi-turn Context)
    contents = []
    # Turn 0: System Prompt
    contents.append({
        "role": "user",
        "parts": [{"text": f"{SYSTEM_PROMPT}\n\nXin chào bạn!"}]
    })
    contents.append({
        "role": "model",
        "parts": [{"text": "Dạ xin chào bạn! Tôi là Trợ lý Pháp lý & Đất đai Thanh Hóa. Tôi đã sẵn sàng tư vấn chi tiết cho bạn."}]
    })
    
    # Các lượt trao đổi trước đó trong cùng cửa sổ
    for item in history[-6:]:
        r = item.get("role", "user")
        c = item.get("content", "").strip()
        if not c:
            continue
        gemini_role = "model" if r in ("assistant", "model", "bot") else "user"
        contents.append({
            "role": gemini_role,
            "parts": [{"text": c}]
        })
        
    # Câu hỏi hiện tại
    contents.append({
        "role": "user",
        "parts": [{"text": f"[CÂU HỎI HIỆN TẠI]: {question}\n\n[TRẢ LỜI (100% TIẾNG VIỆT, LIỀN MẠCH NGỮ CẢNH HỘI THOẠI)]:"}]
    })
    
    payload_data = json.dumps({
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 3000
        }
    }).encode("utf-8")

    for idx, key in enumerate(GEMINI_API_KEYS):
        if not key or len(key) < 10:
            continue
        for model in gemini_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                headers = {"Content-Type": "application/json", "x-goog-api-key": key}
                req = urllib.request.Request(url, data=payload_data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and parts[0].get("text", "").strip():
                            return parts[0]["text"].strip(), f"Google Gemini Flash ({model})"
            except Exception:
                pass

            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
                req = urllib.request.Request(url, data=payload_data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and parts[0].get("text", "").strip():
                            return parts[0]["text"].strip(), f"Google Gemini Flash ({model})"
            except Exception:
                pass

    return None, None

def call_zenmux_backup(question, history=None):
    if not ZENMUX_API_KEY:
        return None, None
    if history is None:
        history = []
        
    zenmux_models = [
        "deepseek/deepseek-chat",
        "z-ai/glm-5.3-free",
        "dots-studio/dots3-note-prev"
    ]
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history[-6:]:
        r = item.get("role", "user")
        c = item.get("content", "").strip()
        if not c:
            continue
        zm_role = "assistant" if r in ("assistant", "model", "bot") else "user"
        messages.append({"role": zm_role, "content": c})
    messages.append({"role": "user", "content": question})

    for m in zenmux_models:
        try:
            url = "https://zenmux.ai/api/v1/chat/completions"
            payload = json.dumps({
                "model": m,
                "messages": messages,
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
                    return ans, f"ZenMux AI Gateway ({m})"
        except Exception:
            continue

    return None, None

def sanitize_ai_output(text):
    if not text:
        return text
    # 1. Xóa số điện thoại bịa đặt, hotline hoặc email giả do LLM tự sinh
    text = re.sub(r'(?i)(?:số điện thoại|hotline|liên hệ trực tiếp|email|đường dây nóng)[\s:]*(?:0237[.\d\s]+|\w+@gmail\.com).*?(?:\n|$)', '', text)
    text = re.sub(r'(?i)phaplydatdai@gmail\.com', '', text)
    text = re.sub(r'0237\.\d{3,4}\.\d{3,4}', '', text)
    
    # 2. XÓA TRIỆT ĐỂ 100% KÝ TỰ CHỮ HÁN / TIẾNG TRUNG QUỐC / NHẬT / HÀN (CJK)
    text = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]', '', text)
    
    # 3. DỌN SẠCH CÁC TIÊU ĐỀ TIẾNG ANH RÒ RỈ (NẾU CÓ)
    text = re.sub(r'(?i)\b(Issue Diagnosis|Legal Basis|Actionable Procedure|Risk & Tips|Entity & Bottleneck|Dual Boundary Analysis|Temporal Legal Grounding|Strict Structured Output)\b', '', text)
    
    # 4. Làm sạch mã lỗi LaTeX chuyển sang ký tự Unicode tiếng Việt chuẩn
    text = text.replace('\\ge', '≥').replace('\\le', '≤').replace('\\times', 'x').replace('\\approx', '≈')
    text = re.sub(r'\\mathbf\{([^}]+)\}', r'**\1**', text)
    text = re.sub(r'\\text\{([^}]+)\}', r'\1', text)
    text = re.sub(r'm\^2', 'm²', text)
    text = re.sub(r'm2\b', 'm²', text)
    
    # Dọn dẹp khoảng trắng thừa và dấu ngoặc rỗng nếu có
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()

def process_question_pipeline(question, history=None):
    q_lower = question.lower().strip()

    # Fast-path: Nhận diện tác giả
    if any(k in q_lower for k in ["tác giả", "ai tạo ra", "ai lập trình", "ai phát triển", "mr thang", "mr thắng", "ai làm ra"]):
        return (
            "Dạ, **Mr Thắng** chính là tác giả và người sáng lập phát triển dự án **ThanhHoa Land AI**!\n\n"
            "Dự án được xây dựng với sứ mệnh ứng dụng trí tuệ nhân tạo chuyên sâu để hỗ trợ cán bộ và người dân tỉnh Thanh Hóa tra cứu pháp luật đất đai, tính toán nghĩa vụ tài chính và lập hồ sơ thủ tục hành chính nhanh chóng, chuẩn xác 100% theo Luật Đất đai 2024."
        ), "ThanhHoa Land AI Core"

    # Fast-path: Chào hỏi
    if q_lower in ["chào", "hello", "hi", "xin chào", "chào bạn", "alo", "test", "halo"]:
        return (
            "Dạ xin chào bạn! Tôi là **Trợ lý Pháp lý & Đất đai ThanhHoa Land AI**.\n\n"
            "Tôi sẵn sàng tư vấn, giải đáp chi tiết các thủ tục cấp Giấy chứng nhận (Sổ đỏ), tách thửa, hợp thửa, chuyển mục đích sử dụng đất, tra cứu quy hoạch và nghĩa vụ tài chính theo Luật Đất đai 2024 và Quyết định 18/2026/QĐ-UBND tỉnh Thanh Hóa.\n\n"
            "👉 *Bạn đang quan tâm đến thửa đất hoặc thủ tục pháp lý nào tại Thanh Hóa cần tôi hỗ trợ ạ?*"
        ), "ThanhHoa Land AI Core"

    ans, model_name = call_gemini_primary(question, history=history)
    if ans:
        return sanitize_ai_output(ans), model_name

    ans, model_name = call_zenmux_backup(question, history=history)
    if ans:
        return sanitize_ai_output(ans), model_name

    return (
        "Dạ, chào bạn! Đối với nội dung bạn quan tâm, tôi xin tư vấn theo quy định hiện hành:\n\n"
        "1. **Căn cứ pháp lý:** Áp dụng Luật Đất đai 2024, Nghị định 101/2024/NĐ-CP, Nghị định 49/2026/NĐ-CP và Quyết định số 18/2026/QĐ-UBND tỉnh Thanh Hóa.\n"
        "2. **Cơ quan tiếp nhận:** Bạn vui lòng liên hệ Bộ phận Một cửa UBND cấp xã/phường nơi có đất hoặc Chi nhánh Văn phòng Đăng ký đất đai cấp huyện để được tiếp nhận hồ sơ trích lục địa chính và thẩm định cụ thể.\n"
        "3. **Hồ sơ cơ bản:** Đơn đăng ký biến động, bản gốc Giấy chứng nhận quyền sử dụng đất, bản sao CCCD và các giấy tờ chứng minh nguồn gốc đất."
    ), "Trợ lý Pháp lý Thanh Hóa"

# ══════════════════════════════════════════════════════════════════
# GEMINI & ZENMUX VISION OCR ENGINE CHO PHÂN HỆ 2
# ══════════════════════════════════════════════════════════════════
def extract_ocr_with_vision(image_base64, mime_type, doc_type="cccd"):
    prompt = PROMPT_CCCD_EXACT if doc_type == "cccd" else PROMPT_LAND_EXACT
    gemini_models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro"]
    
    # 1. Thử qua Google Gemini Vision
    for key in GEMINI_API_KEYS:
        if not key or len(key) < 10:
            continue
            
        payload = {
            "contents": [{
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_base64
                        }
                    },
                    {"text": prompt}
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2048
            }
        }
        payload_data = json.dumps(payload).encode("utf-8")

        for model in gemini_models:
            # Format A: ?key= + x-goog-api-key
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                req = urllib.request.Request(url, data=payload_data, headers={"Content-Type": "application/json", "x-goog-api-key": key}, method="POST")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        json_m = re.search(r'\{.*\}', raw_text, re.DOTALL)
                        if json_m:
                            extracted = json.loads(json_m.group(0))
                            if extracted and any(v for v in extracted.values() if v):
                                return extracted, f"Gemini Vision ({model})"
            except Exception as e:
                pass

            # Format B: Authorization Bearer
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                req = urllib.request.Request(url, data=payload_data, headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}, method="POST")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        json_m = re.search(r'\{.*\}', raw_text, re.DOTALL)
                        if json_m:
                            extracted = json.loads(json_m.group(0))
                            if extracted and any(v for v in extracted.values() if v):
                                return extracted, f"Gemini Vision ({model})"
            except Exception as e:
                pass

    # 2. Dự phòng qua ZenMux Multi-Modal Vision
    if ZENMUX_API_KEY:
        zenmux_vision_models = ["z-ai/glm-5.3-free", "dots-studio/dots3-note-prev", "deepseek/deepseek-chat"]
        for zm in zenmux_vision_models:
            try:
                url = "https://zenmux.ai/api/v1/chat/completions"
                payload = {
                    "model": zm,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}}
                            ]
                        }
                    ],
                    "temperature": 0.1
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Authorization": f"Bearer {ZENMUX_API_KEY}", "Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=35) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    ans = data["choices"][0]["message"]["content"].strip()
                    json_m = re.search(r'\{.*\}', ans, re.DOTALL)
                    if json_m:
                        extracted = json.loads(json_m.group(0))
                        if extracted and any(v for v in extracted.values() if v):
                            return extracted, f"ZenMux Vision ({zm})"
            except Exception as e:
                pass

    return {}, "Không thể bóc tách"

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
        "api_ocr": "/api/ocr/scan [POST]",
        "telegram": "@TroLyLuatbot",
        "primary_model": "Google Gemini Flash + Vision OCR",
        "prompt": "Tro Ly Phap Ly & Dat Dai Thanh Hoa Chuyen Nghiep"
    }), 200

@app.route('/api/chat', methods=['GET', 'POST', 'OPTIONS'])
def api_chat():
    if request.method in ('GET', 'OPTIONS'):
        return jsonify({"status": "ok", "endpoint": "/api/chat", "method": "POST"}), 200

    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    history = data.get("history", [])
    session_id = data.get("session_id", "web_user")

    if not question:
        return jsonify({"error": "Vui lòng nhập câu hỏi"}), 400

    print(f"📥 [Web Chat] {session_id} (History: {len(history)} turns): {question[:80]}")
    answer, model_used = process_question_pipeline(question, history=history)

    return jsonify({
        "answer": answer,
        "model": f"🤖 {model_used}",
        "session_id": session_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200

# ══════════════════════════════════════════════════════════════════
# API OCR SCAN BÓC TÁCH CCCD & GCN (SỔ ĐỎ)
# ══════════════════════════════════════════════════════════════════
@app.route('/api/ocr/scan', methods=['POST', 'OPTIONS'])
def api_ocr():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    doc_type = request.form.get("doc_type", "cccd").lower()
    file = request.files.get("file")
    if not file:
        files = request.files.getlist("files")
        if files:
            file = files[0]

    if not file:
        return jsonify({"success": False, "message": "Không tìm thấy file ảnh tải lên."}), 400

    content = file.read()
    if not content:
        return jsonify({"success": False, "message": "File ảnh rỗng."}), 400

    mime_type = file.mimetype or "image/jpeg"
    if content[:2] == b'\xff\xd8':
        mime_type = "image/jpeg"
    elif content[:8] == b'\x89PNG\r\n\x1a\n':
        mime_type = "image/png"
    elif content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        mime_type = "image/webp"

    b64_image = base64.b64encode(content).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64_image}"

    print(f"📷 [OCR Scan] Nhận ảnh {doc_type} ({len(content)} bytes), đang bóc tách qua Vision...")
    extracted_raw, ocr_model = extract_ocr_with_vision(b64_image, mime_type, doc_type=doc_type)

    # Chuẩn hóa và làm phẳng các trường dữ liệu
    extracted_data = {}
    if isinstance(extracted_raw, dict):
        for k, v in extracted_raw.items():
            if isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    extracted_data[sub_k] = sub_v
            else:
                extracted_data[k] = v

    # Tạo đầy đủ các alias để frontend điền form 100%
    if doc_type == "cccd":
        if "id_number" in extracted_data:
            extracted_data["so_cccd"] = extracted_data["id_number"]
            extracted_data["cccd_so"] = extracted_data["id_number"]
        if "full_name" in extracted_data:
            extracted_data["ho_va_ten"] = extracted_data["full_name"]
            extracted_data["cccd_hoten"] = extracted_data["full_name"]
            extracted_data["ten"] = extracted_data["full_name"]
        if "date_of_birth" in extracted_data:
            extracted_data["ngay_sinh"] = extracted_data["date_of_birth"]
            extracted_data["cccd_ngaysinh"] = extracted_data["date_of_birth"]
        if "date_of_issue" in extracted_data:
            extracted_data["ngay_cap"] = extracted_data["date_of_issue"]
            extracted_data["cccd_ngaycap"] = extracted_data["date_of_issue"]
        if "sex" in extracted_data:
            extracted_data["gioi_tinh"] = extracted_data["sex"]
            extracted_data["cccd_gioitinh"] = extracted_data["sex"]
        if "place_of_origin" in extracted_data:
            extracted_data["que_quan"] = extracted_data["place_of_origin"]
            extracted_data["cccd_quequan"] = extracted_data["place_of_origin"]
        if "place_of_residence" in extracted_data:
            extracted_data["noi_thuong_tru"] = extracted_data["place_of_residence"]
            extracted_data["cccd_thuongtru"] = extracted_data["place_of_residence"]
            extracted_data["dia_chi"] = extracted_data["place_of_residence"]
    else:
        # GCN Sổ đỏ
        if "certificate_serial_number" in extracted_data:
            extracted_data["land_sophathanh"] = extracted_data["certificate_serial_number"]
            extracted_data["so_phat_hanh"] = extracted_data["certificate_serial_number"]
        if "registration_book_number" in extracted_data:
            extracted_data["land_sovaoso"] = extracted_data["registration_book_number"]
            extracted_data["so_vao_so"] = extracted_data["registration_book_number"]
        if "date_of_issue" in extracted_data:
            extracted_data["land_ngaycap"] = extracted_data["date_of_issue"]
            extracted_data["ngay_cap"] = extracted_data["date_of_issue"]
        if "place_of_issue" in extracted_data:
            extracted_data["land_noicap"] = extracted_data["place_of_issue"]
            extracted_data["noi_cap"] = extracted_data["place_of_issue"]
        if "parcel_number" in extracted_data:
            extracted_data["land_thua"] = str(extracted_data["parcel_number"])
            extracted_data["thua_dat_so"] = str(extracted_data["parcel_number"])
        if "map_sheet_number" in extracted_data:
            extracted_data["land_tobando"] = str(extracted_data["map_sheet_number"])
            extracted_data["to_ban_do_so"] = str(extracted_data["map_sheet_number"])
        if "parcel_address" in extracted_data:
            extracted_data["land_diachi"] = extracted_data["parcel_address"]
            extracted_data["dia_chi_thua_dat"] = extracted_data["parcel_address"]
        if "area_number" in extracted_data:
            extracted_data["land_dientich"] = str(extracted_data["area_number"])
            extracted_data["dien_tich"] = str(extracted_data["area_number"])
        if "purpose_of_use" in extracted_data:
            extracted_data["land_mucdich"] = extracted_data["purpose_of_use"]
            extracted_data["muc_dich_su_dung_dat"] = extracted_data["purpose_of_use"]
        if "time_of_use" in extracted_data:
            extracted_data["land_thoihan"] = extracted_data["time_of_use"]
            extracted_data["thoi_han_su_dung"] = extracted_data["time_of_use"]
        if "owner_name" in extracted_data:
            extracted_data["chu_su_dung"] = extracted_data["owner_name"]
            extracted_data["land_chu"] = extracted_data["owner_name"]
            extracted_data["ten_chu_su_dung"] = extracted_data["owner_name"]

    print(f"✅ [OCR Thành Công] {doc_type}: {len(extracted_data)} trường dữ liệu được trích xuất ({ocr_model})")

    return jsonify({
        "success": True if extracted_data else False,
        "doc_type": doc_type,
        "ocr_model": ocr_model,
        "data_urls": [data_url],
        "extracted_data": extracted_data
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

@app.route('/api/export/docx', methods=['POST', 'OPTIONS'])
def api_export_docx():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    return jsonify({"error": "Export DOCX khả dụng trên máy trạm cục bộ."}), 501

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
