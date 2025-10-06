📤 TikTok Bulk Uploader

Tool hỗ trợ đăng video hàng loạt lên nhiều tài khoản TikTok bằng Selenium + Tkinter GUI.
Mỗi tài khoản sẽ có một thư mục profile riêng (tạo trong thư mục Temp của Windows) để lưu session login, giúp bạn không phải đăng nhập lại nhiều lần.

🚀 Tính năng chính
Đăng nhập nhiều tài khoản TikTok (mỗi account lưu session riêng).
Lấy username tự động sau khi login.
Quản lý danh sách tài khoản (thêm, xoá, lưu vào accounts.csv).
Chọn thư mục chứa video để upload hàng loạt.
Template caption động (sử dụng {username} thay bằng tên video).
Hỗ trợ chạy song song nhiều worker (upload cùng lúc).
Giao diện trực quan bằng Tkinter.
⚙️ Cài đặt
Yêu cầu
Windows 10/11
Python 3.9+
Google Chrome (phiên bản mới nhất)
Cài thư viện cần thiết
pip install selenium webdriver-manager pillow

🖥️ Sử dụng
1. Mở tool
python tiktok_bulk_uploader.py

2. Đăng nhập tài khoản TikTok
Vào tab 👤 Accounts → bấm 🔑 Login TikTok.
Chrome sẽ mở ra với profile tạm trong thư mục Temp.
Đăng nhập TikTok → bấm OK trong cửa sổ thông báo.
Tool sẽ tự lấy username và lưu vào danh sách account.
3. Quản lý tài khoản
Thêm account thủ công: nhập Profile Dir + Display Name + Caption Template rồi bấm ➕ Add Account.
Xoá account đã chọn: bấm 🗑 Delete Selected.
Tất cả account được lưu trong file accounts.csv.
4. Chọn video
Vào tab 📤 Upload → bấm Chọn folder để load toàn bộ video .mp4.
5. Upload hàng loạt
Nhập số Max concurrent workers (số Chrome chạy song song).
Bấm ▶ Start Upload để bắt đầu.
Theo dõi tiến trình trong phần Logs.
6. Dừng upload
Bấm ⏹ Stop → tool sẽ dừng sau khi các worker hiện tại hoàn thành.
📂 Cấu trúc file
tiktok_bulk_uploader.py   # Tool chính
accounts.csv              # File chứa danh sách account

📝 Ghi chú
Profile login được lưu trong thư mục tạm (C:\Users\<User>\AppData\Local\Temp\tiktok_profiles).
Nếu Chrome bị crash khi login, tool sẽ xoá profile hỏng để tránh chiếm dung lượng.
Có thể cần đăng nhập lại TikTok nếu session hết hạn.
🔒 Lưu ý
Đây là tool cá nhân hỗ trợ quản lý kênh, không cam kết an toàn tuyệt đối với chính sách TikTok.
Sử dụng nhiều tài khoản song song có thể dẫn đến checkpoint hoặc captcha.
👨‍💻 Tác giả
Viết bằng Python + Selenium + Tkinter
Tối ưu để chạy trên Windows