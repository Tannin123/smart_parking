import sys
import os
import cv2
import numpy as np
import easyocr
import re
import sqlite3
from datetime import datetime
from PIL import Image

# Đường dẫn gốc dự án (luôn đúng dù chạy từ đâu)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.stdout.reconfigure(encoding='utf-8')

# Thêm thư mục detection vào sys.path để import plate_detector
sys.path.insert(0, os.path.join(_BASE_DIR, 'detection'))
import plate_detector

# ── Khởi tạo EasyOCR một lần duy nhất (tốn vài giây lần đầu) ─────────────
print("[INFO] Đang khởi tạo bộ đọc chữ EasyOCR...")
reader = easyocr.Reader(['en'], gpu=False)


# ── Sửa lỗi nhận nhầm phổ biến của OCR trên biển số VN ──────────────────
def format_vn_plate(raw_text: str) -> str:
    """
    Nắn lại các ký tự nhầm lẫn phổ biến của OCR.
    Hỗ trợ cả biển dài (7-8 ký tự) và biển vuông 2 dòng (9-10 ký tự).
    Luôn trả về dạng có dấu '-' để phân tách dòng khi hiển thị.
    """
    text = raw_text.upper().replace(" ", "").replace("-", "").replace(".", "")

    # Sửa 2 ký tự tỉnh (số)
    tinh_str = text[:2].replace('B', '8').replace('O', '0').replace('D', '0') \
                        .replace('S', '5').replace('Z', '2')

    # Ký tự seri (chữ cái)
    if len(text) >= 3:
        serie_char = text[2].replace('8', 'B').replace('0', 'D') \
                             .replace('5', 'S').replace('2', 'Z')
    else:
        return text

    fixed_text = tinh_str + serie_char + text[3:]

    # ── Biển dài: XX-X-NNNNN hoặc XXX-NNNNN (7-8 ký tự) ──
    # ── Biển vuông 2 dòng: XXXN-NNNNN (9-10 ký tự) ─────────
    length = len(fixed_text)

    if length == 7:
        # VD: 51F1234 → 51F-1234
        return f"{fixed_text[:3]}-{fixed_text[3:]}"
    elif length == 8:
        # VD: 51F12345 → 51F1-2345  (biển vuông)
        # hoặc 51AB1234 → 51A-B1234 (biển chữ đôi)
        return f"{fixed_text[:4]}-{fixed_text[4:]}"
    elif length == 9:
        # VD: 51F123456 → 51F1-23456
        return f"{fixed_text[:4]}-{fixed_text[4:]}"
    elif length == 10:
        # VD: 51AB123456 → 51AB-123456 (biển xe tải, xe khách)
        return f"{fixed_text[:4]}-{fixed_text[4:]}"
    else:
        # Quá ngắn hoặc quá dài: trả về nguyên
        return fixed_text


# ── Tiền xử lý ảnh + EasyOCR đọc chữ ───────────────────────────────────
def read_plate_text(img) -> str:
    """
    Tiền xử lý ảnh chuyên sâu (Nhị phân hóa Otsu) và đọc chữ bằng EasyOCR.
    """
    if img is None or img.size == 0:
        return "UNKNOWN"

    # 1. Phóng to 3x để rõ nét hơn
    img_resized = cv2.resize(img, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    # 2. Chuyển sang ảnh xám
    gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
    # 3. Làm mờ nhẹ khử nhiễu
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    # 4. Nhị phân hoá Otsu
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # 5. Dilation nối nét đứt
    kernel = np.ones((3, 3), np.uint8)
    processed = cv2.dilate(thresh, kernel, iterations=1)
    # 6. Chuyển lại RGB cho EasyOCR
    final_img = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)

    results = reader.readtext(
        final_img,
        allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. ',
        paragraph=False,
        mag_ratio=2.0
    )

    if not results:
        return "UNKNOWN"

    # Ghép tất cả ký tự alnum từ các vùng OCR phát hiện được
    raw = "".join(''.join(e for e in text if e.isalnum()) for (_, text, _) in results)
    return format_vn_plate(raw)


# ── Lưu kết quả vào database ─────────────────────────────────────────────
def save_to_database(bien_so_text, loai_bien):
    # Dùng đường dẫn tuyệt đối → luôn lưu đúng chỗ dù chạy từ thư mục nào
    db_path = os.path.join(_BASE_DIR, 'smart_parking.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bang_bien_so (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bien_so TEXT,
            loai_bien TEXT,
            thoi_gian TEXT
        )
    ''')

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        'INSERT INTO bang_bien_so (bien_so, loai_bien, thoi_gian) VALUES (?, ?, ?)',
        (bien_so_text, loai_bien, now)
    )
    conn.commit()
    conn.close()
    print(f"[DATABASE] Đã lưu: '{bien_so_text}' ({loai_bien}) lúc {now}")


# ── Hàm chính ─────────────────────────────────────────────────────────────
def dec_img(image_path=None):
    """Nhận diện biển số từ ảnh."""
    if image_path is None:
        image_path = os.path.join(_BASE_DIR, 'static', 'image', 'xe5.jpg')

    img = cv2.imread(image_path)

    if img is None:
        print(f"Không thể mở ảnh: '{image_path}'. Vui lòng kiểm tra lại đường dẫn!")
        return

    print("Đang xử lý theo luồng: Detect → OCR → Database → Hiển thị...")

    # Hàm vẽ text nổi bật: nền tối + viền vàng + chữ trắng
    def draw_highlighted_text(image, text, pos):
        font       = cv2.FONT_HERSHEY_DUPLEX
        font_scale = 1.2
        thickness  = 2
        pad        = 8

        (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        tx, ty = pos

        # Clamp để không vẽ ra ngoài ảnh
        tx = max(pad, min(tx, image.shape[1] - tw - pad))
        ty = max(th + pad, min(ty, image.shape[0] - pad))

        # Nền đen mờ
        overlay = image.copy()
        cv2.rectangle(overlay,
                      (tx - pad, ty - th - pad),
                      (tx + tw + pad, ty + baseline + pad),
                      (0, 0, 0), cv2.FILLED)
        cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)

        # Viền vàng quanh nền
        cv2.rectangle(image,
                      (tx - pad, ty - th - pad),
                      (tx + tw + pad, ty + baseline + pad),
                      (0, 215, 255), 2)

        # Bóng chữ (shadow)
        cv2.putText(image, text, (tx + 2, ty + 2), font, font_scale, (0, 0, 0), thickness + 2)
        # Chữ chính màu vàng sáng
        cv2.putText(image, text, (tx, ty), font, font_scale, (0, 215, 255), thickness)

    # BƯỚC 1: AI tự dò tìm biển số
    plate_crops, annotated_image, boxes_list = plate_detector.detect_license_plate(img)

    if not boxes_list:
        print("DETECT thất bại: AI YOLO không tự động tìm thấy biển số trong ảnh này.")
        return

    # BƯỚC 2: Cắt ảnh và OCR từng biển số phát hiện được
    line_height = 45
    for plate_img, box in zip(plate_crops, boxes_list):
        x1, y1, x2, y2 = box[:4]
        w = x2 - x1
        h = y2 - y1

        # Phân loại biển dựa trên tỷ lệ khung
        ty_le = w / h if h > 0 else 0
        print(f"Tỷ lệ khung hình (w/h): {ty_le:.2f}")
        if ty_le > 2.5:
            print("=> Phân loại: Biển dài (1 dòng)")
            loai_bien = "Biển dài"
        else:
            print("=> Phân loại: Biển vuông (2 dòng)")
            loai_bien = "Biển vuông"

        # BƯỚC 2a: EasyOCR đọc biển số
        clean_text = read_plate_text(plate_img)
        print(f"KẾT QUẢ OCR: {clean_text}")

        if clean_text and clean_text != "UNKNOWN":
            # FIX: split theo '-' — format_vn_plate luôn trả về dạng có '-'
            lines = clean_text.split('-')

            save_to_database(clean_text, loai_bien)

            # ── NUMPY SCAN EFFECT trên vùng biển số ──────────────────
            roi = img[y1:y2, x1:x2].astype(np.float32)

            # Lớp phủ xanh cyan bán trong suốt
            cyan_overlay = np.full_like(roi, (255, 255, 0), dtype=np.float32)
            roi = cv2.addWeighted(roi, 0.75, cyan_overlay, 0.25, 0)

            # Scan lines: tối mỗi hàng
            roi[::4, :]  = roi[::4, :]  * 0.45
            roi[1::4, :] = roi[1::4, :] * 0.65

            # Dải sáng ngang ở giữa (highlight sweep)
            mid   = h // 2
            sweep = max(3, h // 10)
            band  = roi[max(0, mid-sweep):min(h, mid+sweep), :]
            bright = np.clip(band * 1.6 + 40, 0, 255)
            roi[max(0, mid-sweep):min(h, mid+sweep), :] = bright

            img[y1:y2, x1:x2] = np.clip(roi, 0, 255).astype(np.uint8)
            # ──────────────────────────────────────────────────────────

            # Khung biển số: viền xanh lá dày + góc nổi bật
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)

            # Vẽ 4 góc vàng nổi bật
            corner_len   = 15
            corner_color = (0, 255, 255)
            corner_thick = 4
            for (cx, cy) in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]:
                dx = corner_len if cx == x1 else -corner_len
                dy = corner_len if cy == y1 else -corner_len
                cv2.line(img, (cx, cy), (cx + dx, cy), corner_color, corner_thick)
                cv2.line(img, (cx, cy), (cx, cy + dy), corner_color, corner_thick)

            # FIX: Hiển thị đúng số dòng theo số phần sau khi split '-'
            if len(lines) >= 2:
                # Có ít nhất 2 phần → hiển thị 2 dòng (dòng 1 và dòng 2)
                if y1 >= line_height * 2 + 10:
                    y_line1 = y1 - line_height - 5
                    y_line2 = y1 - 5
                else:
                    y_line1 = y2 + line_height
                    y_line2 = y2 + line_height * 2
                draw_highlighted_text(img, lines[0], (x1, y_line1))
                draw_highlighted_text(img, lines[1], (x1, y_line2))
            else:
                # Chỉ 1 phần → hiển thị 1 dòng
                y_text = y1 - 10 if y1 >= 20 else y2 + line_height
                draw_highlighted_text(img, lines[0], (x1, y_text))
        else:
            print("OCR thất bại: EasyOCR không đọc được chữ trên biển số này.")

    # BƯỚC 3: Hiển thị (dùng PIL để tránh xung đột opencv-headless)
    out_path = os.path.join(_BASE_DIR, 'static', 'image', 'result.jpg')
    cv2.imwrite(out_path, img)
    Image.open(out_path).show()
    print(f"[Đã lưu kết quả] {out_path}")


if __name__ == "__main__":
    dec_img()