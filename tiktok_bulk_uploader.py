import os
import threading
import queue
import csv
import time
import datetime
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, ttk, Frame, Label, Listbox, Scrollbar, END, StringVar
from PIL import Image, ImageTk
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ----------------------------- Config -----------------------------
DEFAULT_MAX_WORKERS = 10
UPLOAD_URL = 'https://www.tiktok.com/upload?lang=en'
ACCOUNTS_FILE = "accounts.csv"

# ----------------------------- Selenium Helpers -----------------------------
def create_chrome_driver(profile_dir: str, headless: bool = False):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--remote-debugging-port=0")  # cho Chrome chọn port ngẫu nhiên
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--start-maximized")

    if headless:
        chrome_options.add_argument("--headless=new")

    # đảm bảo mỗi profile là duy nhất
    chrome_options.add_argument(f"--user-data-dir={profile_dir}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def safe_find_input_file(driver):
    elems = driver.find_elements(By.CSS_SELECTOR, 'input[type=file]')
    for e in elems:
        if e.is_displayed():
            return e
    raise NoSuchElementException('File input not found')


def upload_video_with_driver(driver, video_path: str, caption_text: str, timeout=60):
    try:
        driver.get(UPLOAD_URL)
        time.sleep(3)

        input_file = safe_find_input_file(driver)
        input_file.send_keys(str(video_path))

        time_wait = 0
        while time_wait < timeout:
            try:
                caption_area = driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"], textarea')
                if caption_area.is_displayed():
                    break
            except Exception:
                pass
            time.sleep(1)
            time_wait += 1

        try:
            ta = driver.find_elements(By.TAG_NAME, 'textarea')
            if ta:
                ta[0].clear()
                ta[0].send_keys(caption_text)
            else:
                cap_divs = driver.find_elements(By.CSS_SELECTOR, 'div[contenteditable="true"]')
                if cap_divs:
                    cap_divs[0].click()
                    cap_divs[0].send_keys(caption_text)
        except Exception:
            pass

        time.sleep(1)
        btns = driver.find_elements(By.XPATH, "//button")
        for b in btns:
            try:
                txt = b.text.strip().lower()
                if txt in ('post', 'upload', 'publish', 'share') or 'post' in txt:
                    b.click()
                    time.sleep(2)
                    return True
            except Exception:
                continue
        return False
    except Exception as e:
        print('Upload error:', e)
        return False

# ----------------------------- Worker -----------------------------
def worker_upload(task_q: queue.Queue, result_q: queue.Queue, headless=False, log_func=print):
    while True:
        try:
            task = task_q.get_nowait()
        except queue.Empty:
            break
        profile_dir, display_name, video_path, caption_template = task
        caption = caption_template.replace('{filename}', Path(video_path).stem)
        try:
            log_func(f'[{display_name}] Bắt đầu (profile: {profile_dir})')
            driver = create_chrome_driver(profile_dir, headless=headless)
            success = upload_video_with_driver(driver, video_path, caption)
            driver.quit()
            result_q.put((display_name, video_path, success))
            log_func(f'[{display_name}] Kết thúc - success={success}')
        except WebDriverException as e:
            log_func(f'[{display_name}] Lỗi WebDriver: {e}')
            result_q.put((display_name, video_path, False))
        except Exception as e:
            log_func(f'[{display_name}] Lỗi khác: {e}')
            result_q.put((display_name, video_path, False))
        finally:
            task_q.task_done()

# ----------------------------- GUI -----------------------------
class AppGUI:
    def __init__(self, root):
        self.root = root
        root.title('TikTok Bulk Uploader - Demo')
        root.geometry("900x600")
        root.configure(bg="#f9f9f9")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#f9f9f9", borderwidth=0)
        style.configure("TNotebook.Tab", padding=[12, 6], font=("Segoe UI", 11))
        style.configure("Treeview", font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))

        self.accounts = []
        self.videos = []
        self.max_workers = 5

        self._stop_event = threading.Event()
        self._task_thread = None

        self.build_ui()

    def build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_upload = Frame(notebook, bg="#f9f9f9")
        notebook.add(self.tab_upload, text="📤 Upload")
        self.build_upload_tab()

        self.tab_accounts = Frame(notebook, bg="#f9f9f9")
        notebook.add(self.tab_accounts, text="👤 Accounts")
        self.build_accounts_tab()

    def build_upload_tab(self):
        frm = Frame(self.tab_upload, bg="#f9f9f9")
        frm.pack(padx=10, pady=10, fill="x")

        Label(frm, text='Accounts', bg="#f9f9f9", font=("Segoe UI", 11)).grid(row=0, column=0, sticky='w')
        ttk.Button(frm, text='Reload accounts', command=self.load_accounts_file).grid(row=0, column=1, padx=5)

        Label(frm, text='Thư mục chứa video', bg="#f9f9f9", font=("Segoe UI", 11)).grid(row=1, column=0, sticky='w', pady=4)
        ttk.Button(frm, text='Chọn thư mục', command=self.load_videos_folder).grid(row=1, column=1, padx=5)

        Label(frm, text='Số lượng tài khoản tối đa:', bg="#f9f9f9", font=("Segoe UI", 11)).grid(row=2, column=0, sticky='w', pady=4)
        self.workers_var = StringVar(value=str(self.max_workers))
        ttk.Entry(frm, textvariable=self.workers_var, width=6).grid(row=2, column=1, sticky='w')

        ttk.Button(frm, text='▶ Bắt đầu tải lên', command=self.start_upload).grid(row=3, column=0, pady=6, sticky="w")
        ttk.Button(frm, text='⏹ Dừng', command=self.stop_upload).grid(row=3, column=1, pady=6, sticky="w")

        Label(self.tab_upload, text='Nhật ký:', bg="#f9f9f9", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 0))
        log_frame = Frame(self.tab_upload)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.logbox = Listbox(log_frame, width=120, height=18, font=("Consolas", 10), bg="white")
        self.logbox.pack(side="left", fill="both", expand=True)

        scrollbar = Scrollbar(log_frame, orient='vertical', command=self.logbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.logbox.config(yscrollcommand=scrollbar.set)

    def build_accounts_tab(self):
        frm = Frame(self.tab_accounts, bg="#f9f9f9")
        frm.pack(padx=10, pady=10, fill="x")

        self.profile_var = StringVar()
        self.display_var = StringVar()
        self.caption_var = StringVar()

        Label(frm, text="Thư mục chứa profile:", bg="#f9f9f9").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.profile_var, width=40).grid(row=0, column=1)
        ttk.Button(frm, text="🔑 Đăng nhập TikTok", command=self.login_account).grid(row=3, column=2, pady=5, sticky="w")

        Label(frm, text="Tên hiển thị:", bg="#f9f9f9").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.display_var, width=40).grid(row=1, column=1)

        Label(frm, text="Mẫu chú thích:", bg="#f9f9f9").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.caption_var, width=40).grid(row=2, column=1)

        ttk.Button(frm, text="➕ Thêm tài khoản", command=self.add_account).grid(row=3, column=0, pady=5, sticky="w")
        ttk.Button(frm, text="🗑 Xóa tài khoản đã chọn", command=self.delete_account).grid(row=3, column=1, pady=5, sticky="w")

        Label(self.tab_accounts, text="Danh sách tài khoản:", bg="#f9f9f9", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 0))

        self.acc_list = ttk.Treeview(self.tab_accounts, columns=("profile", "display", "caption"), show="headings")
        self.acc_list.heading("profile", text="Profile Dir")
        self.acc_list.heading("display", text="Display Name")
        self.acc_list.heading("caption", text="Caption Template")
        self.acc_list.pack(fill="both", expand=True, padx=10, pady=5)

    # ---------------- Account Manager ----------------
    def login_account(self, max_retries=1):
        temp_base = Path(tempfile.gettempdir()) / "tiktok_profiles"
        temp_base.mkdir(exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        attempt = 0
        driver = None
        profile_dir = None
        display_name = None

        while attempt < max_retries:
            try:
                # tạo path duy nhất trong temp, KHÔNG mkdir trước
                profile_dir = temp_base / f"profile_{timestamp}_{attempt}"
                if profile_dir.exists():
                    shutil.rmtree(profile_dir, ignore_errors=True)

                self.log(f"[Try {attempt+1}] Opening Chrome for login with profile: {profile_dir}")
                driver = create_chrome_driver(str(profile_dir), headless=False)

                driver.get("https://www.tiktok.com/login")
                messagebox.showinfo(
                    "Login",
                    "Hãy đăng nhập TikTok trong cửa sổ Chrome.\nSau khi đăng nhập thành công, bấm OK để tool lấy username."
                )

                driver.get("https://www.tiktok.com/@me")
                time.sleep(5)
                profile_url = driver.current_url
                username = profile_url.split("@")[-1].strip("/")
                display_name = username if username else f"Account_{timestamp}"
                break  # login ok → thoát retry loop

            except Exception as e:
                self.log(f"Lỗi khi mở Chrome attempt {attempt+1}: {e}")
                attempt += 1

                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                driver = None

                # xoá profile lỗi trong temp
                if profile_dir and profile_dir.exists():
                    shutil.rmtree(profile_dir, ignore_errors=True)
                    self.log(f"Đã xoá profile_dir lỗi: {profile_dir}")

                profile_dir = None
                time.sleep(2)  # delay rồi thử lại

        if not profile_dir:
            messagebox.showerror("Login", f"Không thể mở Chrome sau {max_retries} lần thử.")
            return

        if driver:
            try:
                driver.quit()
            except:
                pass

        caption = "{username}"
        self.accounts.append({
            "profile_dir": str(profile_dir),
            "display_name": display_name,
            "caption_template": caption
        })
        self.save_accounts_file()
        self.refresh_account_list()

        self.profile_var.set(str(profile_dir))
        self.display_var.set(display_name)
        self.caption_var.set(caption)

        self.log(f"Đã thêm account {display_name} với profile {profile_dir}")

    def add_account(self):
        profile = self.profile_var.get().strip()
        display = self.display_var.get().strip() or profile
        caption = self.caption_var.get().strip() or "{username}"
        if not profile:
            messagebox.showerror("Error", "Profile dir không được rỗng")
            return
        self.accounts.append({"profile_dir": profile, "display_name": display, "caption_template": caption})
        self.save_accounts_file()
        self.refresh_account_list()

    def delete_account(self):
        selected = self.acc_list.selection()
        if not selected:
            return
        for sel in selected:
            vals = self.acc_list.item(sel, "values")
            self.accounts = [a for a in self.accounts if a["profile_dir"] != vals[0]]
        self.save_accounts_file()
        self.refresh_account_list()

    def load_accounts_file(self):
        self.accounts = []
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue
                    profile = row[0].strip()
                    display = row[1].strip() if len(row) > 1 else profile
                    caption = row[2].strip() if len(row) > 2 else "{filename}"
                    self.accounts.append({"profile_dir": profile, "display_name": display, "caption_template": caption})
        self.refresh_account_list()
        self.log(f'Loaded {len(self.accounts)} accounts')

    def save_accounts_file(self):
        with open(ACCOUNTS_FILE, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            for acc in self.accounts:
                writer.writerow([acc["profile_dir"], acc["display_name"], acc["caption_template"]])

    def refresh_account_list(self):
        for i in self.acc_list.get_children():
            self.acc_list.delete(i)
        for acc in self.accounts:
            self.acc_list.insert("", END, values=(acc["profile_dir"], acc["display_name"], acc["caption_template"]))

    # ---------------- Upload Manager ----------------
    def log(self, text):
        ts = time.strftime('%H:%M:%S')
        self.logbox.insert(END, f'[{ts}] {text}')
        self.logbox.yview_moveto(1)

    def load_videos_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        p = Path(folder)
        self.videos = sorted([str(x) for x in p.glob('**/*.mp4')])
        self.log(f'Loaded {len(self.videos)} videos from {folder}')

    def start_upload(self):
        if not self.accounts:
            messagebox.showerror('Error', 'Chưa có accounts')
            return
        if not self.videos:
            messagebox.showerror('Error', 'Chưa load videos')
            return
        try:
            self.max_workers = int(self.workers_var.get())
            if self.max_workers < 1:
                raise ValueError()
        except ValueError:
            messagebox.showerror('Error', 'Max workers không hợp lệ')
            return

        tasks = []
        vid_idx = 0
        for acc in self.accounts:
            if vid_idx >= len(self.videos):
                break
            tasks.append((acc['profile_dir'], acc['display_name'], self.videos[vid_idx], acc['caption_template']))
            vid_idx += 1

        if not tasks:
            messagebox.showerror('Error', 'Không có đủ video để gán cho accounts')
            return

        self._stop_event.clear()
        task_q = queue.Queue()
        result_q = queue.Queue()
        for t in tasks:
            task_q.put(t)

        self.log(f'Starting upload for {task_q.qsize()} accounts with {self.max_workers} workers')

        def run_workers():
            with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                for _ in range(self.max_workers):
                    ex.submit(worker_upload, task_q, result_q, False, self.log)
                task_q.join()
            res_list = []
            while not result_q.empty():
                res_list.append(result_q.get())
            self.log('All tasks finished')
            success = sum(1 for r in res_list if r[2])
            self.log(f'Successful uploads: {success}/{len(res_list)}')

        self._task_thread = threading.Thread(target=run_workers, daemon=True)
        self._task_thread.start()

    def stop_upload(self):
        if self._task_thread and self._task_thread.is_alive():
            self.log('Stop requested (soft). Workers will finish current job then stop')
            self._stop_event.set()
        else:
            self.log('Không có tác vụ nào đang chạy')

    def on_close(self):
        if messagebox.askokcancel('Quit', 'Bạn có chắc muốn thoát?'):
            self.stop_upload()
            self.root.destroy()


if __name__ == '__main__':
    root = Tk()
    app = AppGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()