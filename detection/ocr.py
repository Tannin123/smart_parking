import easyocr
import cv2
import numpy as np

# Khởi tạo mô hình EasyOCR
print("[INFO] Đang khởi tạo bộ đọc chữ EasyOCR...")
reader = easyocr.Reader(['en'], gpu=False) 

def format_vn_plate(raw_text: str) -> str:
    """Nắn lại các lỗi đọc nhầm phổ biến của OCR"""
    text = raw_text.upper().replace(" ", "").replace("-", "").replace(".", "")
    if len(text) < 4 or len(text) > 12:
        return text

    tinh_str = text[:2].replace('B', '8').replace('O', '0').replace('D', '0').replace('S', '5').replace('Z', '2')
    serie_char = text[2].replace('8', 'B').replace('0', 'D').replace('5', 'S').replace('2', 'Z')
    fixed_text = tinh_str + serie_char + text[3:]

    if len(fixed_text) >= 8:
        return f"{fixed_text[:4]}-{fixed_text[4:]}"
    return fixed_text

def read_plate_text(img) -> str:
    """
    Tiền xử lý bằng CLAHE (Giữ nét chữ đặc ruột, tốt nhất cho AI Deep Learning)
    """
    if img is None or img.size == 0:
        return "UNKNOWN"

    # --- 1. TIỀN XỬ LÝ ẢNH ---
    # Phóng to ảnh gấp 2.5 lần để AI nhìn rõ nét
    img_resized = cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    
    # Chuyển sang ảnh xám (Bỏ màu sắc đi)
    gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
    
    # Dùng CLAHE để tăng cường độ tương phản (Làm nét chữ đặc ruột, sáng nền)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced_gray = clahe.apply(gray)

    # ---> ĐÃ THÊM SẴN LỆNH LƯU ẢNH KIỂM TRA TẠI ĐÂY <---
    cv2.imwrite("debug_plate.jpg", enhanced_gray)

    # Chuyển lại RGB cho EasyOCR
    final_img = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2RGB)

    # --- 2. EASYOCR ĐỌC CHỮ ---
    results = reader.readtext(
        final_img, 
        allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. ',
        paragraph=True,
        mag_ratio=2.0 
    )
    
    if len(results) == 0:
        return "UNKNOWN"
    
    raw_plate_text = ""
    for item in results:
        if len(item) == 3:
            bbox, text, prob = item
        else:
            bbox, text = item
        clean_text = ''.join(e for e in text if e.isalnum())
        raw_plate_text += clean_text
    
    # --- 3. ÁP DỤNG QUY TẮC VN ---
    return format_vn_plate(raw_plate_text)
