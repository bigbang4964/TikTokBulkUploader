# TikTokBulkUploader
"""
TikTok Bulk Uploader - Python (Tkinter + Selenium)

Mục đích: demo tool chạy cục bộ để đăng hàng loạt video lên nhiều kênh TikTok.
Hướng tiếp cận: tự động hóa trình duyệt (Selenium + Chrome) sử dụng Chrome profiles
(hoặc cookie/session đã đăng nhập) — mỗi profile tương ứng 1 tài khoản.

LƯU Ý QUAN TRỌNG:
- Đây là ví dụ kỹ thuật. Việc tự động hóa upload có thể vi phạm Điều khoản dịch vụ của TikTok.
- Chạy đồng thời 100 trình duyệt sẽ tiêu tốn rất nhiều RAM/CPU. Cấu hình đề xuất test ban đầu: 2-5 workers.
- Bạn cần chuẩn bị sẵn profile Chrome đã đăng nhập TikTok (một thư mục user-data-dir cho mỗi account)

Yêu cầu:
- Python 3.9+
- pip install selenium pillow
- Chrome browser + chromedriver tương thích (đặt vào PATH hoặc chỉ định đường dẫn)

Hướng dẫn ngắn:
1. Tạo Chrome profile cho mỗi tài khoản (hoặc xuất cookies/đăng nhập thủ công)
2. Chuẩn bị một thư mục chứa video (.mp4)
3. Chuẩn bị CSV accounts: profile_dir,display_name,caption_template
4. Mở GUI, load CSV accounts và load folder videos
5. Map hoặc để tool auto-assign 1 video / account
6. Start (bắt đầu worker). Theo dõi logs.

Không cam kết upload thành công trên chính TikTok — bạn phải test và điều chỉnh selectors theo trang TikTok tại thời điểm chạy.

"""