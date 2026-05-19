# smart_parking
1. Mô hình hệ thống
WEBCAM / ẢNH / VIDEO / IP ( Phần IP nếu dư thời gian thì tui sẽ làm )
↓
FLASK WEB
↓
YOLOv8 DETECTION
↓
EASYOCR
↓
MYSQL DB
↓
DASHBOARD + QUẢN LÝ
- Cơ chế hoạt động
+ Xe vào:
•	Camera: detect biển số -> ocr đọc kí tự -> lưu thời gian vào -> chụp ảnh -> lưu vào sql -> cho vào
+ Xe ra
•	Camera: detect lại biển số -> tìm trong database -> tính thời gian gửi -> tính tiền -> lưu giờ ra -> hiển thị hóa đơn
- KIẾN TRÚC CÁC MODEL
1. Model WEB
- Các công nghệ áp dụng
+ HTML
+ CSS
+ JAVASCRIPT
- Chức năng
+ Login 
+ Dashboard
+ Lịch sử xe
+ Camera
+ upload ảnh / video
2. MODULE BACKEND
- Công nghệ
+ Flask
- Nhiệm vụ
•	xử lý route 
•	session 
•	API 
•	kết nối AI 
•	kết nối MySQL
3. MODULE AI DETECTION
- Công nghệ
+ YOLOv8
- Nhiệm vụ
•	detect biển số 
•	tạo bounding box 
4. MODULE OCR
- Công nghệ
+ EasyOCR
- Nhiệm vụ
•	đọc ký tự biển số 
5. MODULE DATABASE
- Công nghệ
MySQL
- SƠ ĐỒ CÁC MODEL (DỰ KIẾN)
<img width="422" height="1350" alt="image" src="https://github.com/user-attachments/assets/dbb69161-2e73-40ab-9645-8134d5160dc5" />
6. DATABASE 
- BẢNG USERS
- BẢNG EMPLOYEES
- BẢNG PRICING
- BẢNG VEHICLES
7. Model nhận diện video
- Upload video: đọc từng fame -> detect yolo -> ocr -> render video mới -> download
8. Model webcam 
- cv.VideoCapture(0) -> Flask stream -> yolo detect -> easyOCR -> trả về fame web 
9. MODULE NHẬN DIỆN ẢNH
- Uploade image -> detect biển số -> OCR -> lưu database -> hiển thị
10. THƯ VIỆN CẦN CÀI
- pip install flask
- pip install opencv-python
- pip install ultralytics
- pip install easyocr
- pip install pymysql
- pip install flask-socketio

- Giải thích các model:
1. app.py
•	chạy Flask 
•	load route 
•	chạy web 
•	stream webcam 
2. config.py
•	cấu hình hệ thống 
•	secret key 
•	MySQL config 
3. requirements.txt
•	danh sách thư viện cần cài 
4. static/
- Chứa file frontend tĩnh.
5. templates/
•	giao diện HTML Flask 
6. detection/
- chứa các bộ xử lý AI
7. database/
- kết nối vào database
8. routes/
- các chức năng như thêm sửa xóa, …
9. models/
- chứa
•	AI model 



