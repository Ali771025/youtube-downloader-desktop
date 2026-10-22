"""
YouTube Downloader UI
======================
یک برنامه دسکتاپ ساده با Tkinter برای دانلود ویدئوهای مجاز از YouTube
با استفاده از کتابخانه yt-dlp.

نکته حقوقی:
این برنامه فقط برای دانلود محتوایی طراحی شده که کاربر مالک آن است، اجازه
دانلود آن را دارد یا تحت مجوزهای مجاز منتشر شده است. هیچ مکانیزمی برای دور
زدن DRM یا دسترسی به محتوای خصوصی/محدودشده در این برنامه وجود ندارد.

نصب پیش‌نیازها:
    pip install yt-dlp

همچنین برای ادغام صحیح ویدئو/صدا (MP4) و استخراج صدا (MP3) باید FFmpeg
روی سیستم نصب و در PATH موجود باشد.
    - ویندوز: از https://ffmpeg.org/download.html دانلود و در PATH اضافه کنید.
    - لینوکس: sudo apt install ffmpeg
    - مک: brew install ffmpeg

اجرای برنامه:
    python youtube_downloader_ui.py
"""

import os
import re
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import yt_dlp
except ImportError:
    raise SystemExit(
        "کتابخانه yt-dlp نصب نیست.\n"
        "لطفاً دستور زیر را اجرا کنید:\n"
        "    pip install yt-dlp"
    )


# ---------------------------------------------------------------------------
# اعتبارسنجی لینک YouTube
# ---------------------------------------------------------------------------
YOUTUBE_URL_PATTERN = re.compile(
    r'^(https?://)?(www\.)?'
    r'(youtube\.com/(watch\?v=|embed/)[\w-]{11}.*|youtu\.be/[\w-]{11}.*)$',
    re.IGNORECASE
)


def is_valid_youtube_url(url: str) -> bool:
    """بررسی می‌کند که لینک واردشده یک لینک معتبر YouTube (watch/youtu.be/embed) باشد."""
    if not url:
        return False
    return bool(YOUTUBE_URL_PATTERN.match(url.strip()))


# ---------------------------------------------------------------------------
# کلاس اصلی برنامه
# ---------------------------------------------------------------------------
class YouTubeDownloaderApp:
    """کلاس اصلی مدیریت رابط کاربری و منطق دانلود ویدئو با yt-dlp."""

    # نگاشت گزینه‌های نمایشی ComboBox به کلیدهای داخلی کیفیت
    QUALITY_DISPLAY_TO_KEY = {
        "بهترین کیفیت": "best",
        "1080p": "1080p",
        "720p": "720p",
        "480p": "480p",
        "فقط صدا - MP3": "audio_mp3",
    }

    # نگاشت کلید کیفیت به فرمت انتخاب yt-dlp
    FORMAT_SELECTORS = {
        "best": "bv*+ba/best",
        "1080p": "bv*[height<=1080]+ba/b[height<=1080]/best[height<=1080]",
        "720p": "bv*[height<=720]+ba/b[height<=720]/best[height<=720]",
        "480p": "bv*[height<=480]+ba/b[height<=480]/best[height<=480]",
        "audio_mp3": "bestaudio/best",
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("560x380")
        self.root.resizable(False, False)

        # وضعیت داخلی
        self.is_downloading = False
        self.save_path_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        self.url_var = tk.StringVar()
        self.quality_var = tk.StringVar(value="بهترین کیفیت")
        self.status_var = tk.StringVar(value="آماده برای دانلود")

        self._build_ui()

    # -----------------------------------------------------------------
    # ساخت رابط کاربری
    # -----------------------------------------------------------------
    def _build_ui(self):
        padding = {"padx": 10, "pady": 6}

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # عنوان
        title_label = ttk.Label(
            main_frame, text="YouTube Downloader", font=("Segoe UI", 14, "bold")
        )
        title_label.pack(anchor="center", pady=(0, 10))

        # فیلد لینک
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill="x", **padding)
        ttk.Label(url_frame, text="لینک ویدئو:").pack(anchor="w")
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        self.url_entry.pack(fill="x", pady=(2, 0))
        self._enable_context_menu(self.url_entry)

        # فیلد مسیر ذخیره
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill="x", **padding)
        ttk.Label(path_frame, text="مسیر ذخیره:").pack(anchor="w")

        path_row = ttk.Frame(path_frame)
        path_row.pack(fill="x", pady=(2, 0))
        self.path_entry = ttk.Entry(path_row, textvariable=self.save_path_var)
        self.path_entry.pack(side="left", fill="x", expand=True)
        self._enable_context_menu(self.path_entry)
        self.browse_button = ttk.Button(path_row, text="انتخاب مسیر", command=self.browse_path)
        self.browse_button.pack(side="left", padx=(6, 0))

        # انتخاب کیفیت
        quality_frame = ttk.Frame(main_frame)
        quality_frame.pack(fill="x", **padding)
        ttk.Label(quality_frame, text="کیفیت دانلود:").pack(anchor="w")
        self.quality_combo = ttk.Combobox(
            quality_frame,
            textvariable=self.quality_var,
            values=list(self.QUALITY_DISPLAY_TO_KEY.keys()),
            state="readonly",
        )
        self.quality_combo.pack(fill="x", pady=(2, 0))

        # دکمه‌های Download و Clear
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", **padding)
        self.download_button = ttk.Button(
            button_frame, text="دانلود", command=self.start_download
        )
        self.download_button.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.clear_button = ttk.Button(
            button_frame, text="پاک کردن", command=self.clear_fields
        )
        self.clear_button.pack(side="left", expand=True, fill="x", padx=(5, 0))

        # نوار پیشرفت
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill="x", **padding)
        self.progress_bar = ttk.Progressbar(
            progress_frame, orient="horizontal", mode="determinate", maximum=100
        )
        self.progress_bar.pack(fill="x")

        # لیبل وضعیت
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", **padding)
        self.status_label = ttk.Label(
            status_frame, textvariable=self.status_var, foreground="#333333"
        )
        self.status_label.pack(anchor="w")

    # -----------------------------------------------------------------
    # منوی راست‌کلیک (Cut/Copy/Paste) برای فیلدهای ورودی
    # -----------------------------------------------------------------
    def _enable_context_menu(self, entry_widget: ttk.Entry):
        """
        ttk.Entry به‌صورت پیش‌فرض منوی راست‌کلیک ندارد، بنابراین این تابع یک
        منوی Cut/Copy/Paste/Select All به فیلد اضافه می‌کند و همچنین مطمئن
        می‌شود کلیدهای میان‌بر Ctrl+V ،Ctrl+C ،Ctrl+X و Ctrl+A کار می‌کنند.
        """
        menu = tk.Menu(entry_widget, tearoff=0)
        menu.add_command(label="برش (Cut)", command=lambda: entry_widget.event_generate("<<Cut>>"))
        menu.add_command(label="کپی (Copy)", command=lambda: entry_widget.event_generate("<<Copy>>"))
        menu.add_command(label="چسباندن (Paste)", command=lambda: entry_widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="انتخاب همه (Select All)", command=lambda: entry_widget.select_range(0, "end"))

        def show_menu(event):
            entry_widget.focus_set()
            menu.tk_popup(event.x_root, event.y_root)

        # راست‌کلیک ماوس برای نمایش منو
        entry_widget.bind("<Button-3>", show_menu)

        # اطمینان از کارکرد کلیدهای میان‌بر حتی با چیدمان‌های مختلف کیبورد
        entry_widget.bind("<Control-v>", lambda e: (entry_widget.event_generate("<<Paste>>"), "break"))
        entry_widget.bind("<Control-V>", lambda e: (entry_widget.event_generate("<<Paste>>"), "break"))
        entry_widget.bind("<Control-c>", lambda e: (entry_widget.event_generate("<<Copy>>"), "break"))
        entry_widget.bind("<Control-x>", lambda e: (entry_widget.event_generate("<<Cut>>"), "break"))
        entry_widget.bind("<Control-a>", lambda e: (entry_widget.select_range(0, "end"), "break"))

    # -----------------------------------------------------------------
    # رویدادهای UI
    # -----------------------------------------------------------------
    def browse_path(self):
        selected_dir = filedialog.askdirectory(initialdir=self.save_path_var.get() or os.getcwd())
        if selected_dir:
            self.save_path_var.set(selected_dir)

    def clear_fields(self):
        if self.is_downloading:
            return
        self.url_var.set("")
        self.quality_var.set("بهترین کیفیت")
        self.progress_bar["value"] = 0
        self.status_var.set("آماده برای دانلود")

    def start_download(self):
        if self.is_downloading:
            return

        url = self.url_var.get().strip()
        save_path = self.save_path_var.get().strip()

        # اعتبارسنجی لینک
        if not url:
            messagebox.showerror("خطا", "لطفاً یک لینک YouTube وارد کنید.")
            return
        if not is_valid_youtube_url(url):
            messagebox.showerror(
                "خطا",
                "لینک واردشده معتبر نیست.\n"
                "لینک باید به یکی از قالب‌های زیر باشد:\n"
                "https://www.youtube.com/watch?v=...\n"
                "https://youtu.be/...\n"
                "https://www.youtube.com/embed/...",
            )
            return

        # اعتبارسنجی مسیر ذخیره
        if not save_path:
            messagebox.showerror("خطا", "لطفاً مسیر ذخیره فایل را انتخاب کنید.")
            return
        if not os.path.isdir(save_path):
            messagebox.showerror("خطا", "مسیر ذخیره واردشده معتبر نیست یا وجود ندارد.")
            return
        if not os.access(save_path, os.W_OK):
            messagebox.showerror("خطا", "دسترسی نوشتن به مسیر ذخیره وجود ندارد.")
            return

        quality_key = self.QUALITY_DISPLAY_TO_KEY.get(self.quality_var.get(), "best")

        # آماده‌سازی UI برای شروع دانلود
        self.is_downloading = True
        self.download_button.config(state="disabled")
        self.progress_bar["value"] = 0
        self.status_var.set("در حال شروع دانلود...")

        # اجرای دانلود در Thread جداگانه تا UI هنگ نکند
        download_thread = threading.Thread(
            target=self.download_worker,
            args=(url, save_path, quality_key),
            daemon=True,
        )
        download_thread.start()

    # -----------------------------------------------------------------
    # منطق دانلود (در Thread جدا اجرا می‌شود)
    # -----------------------------------------------------------------
    def download_worker(self, url: str, save_path: str, quality_key: str):
        try:
            outtmpl = os.path.join(save_path, "%(title)s.%(ext)s")

            ydl_opts = {
                "format": self.FORMAT_SELECTORS.get(quality_key, self.FORMAT_SELECTORS["best"]),
                "outtmpl": outtmpl,
                "noplaylist": True,          # جلوگیری از دانلود کامل پلی‌لیست به‌صورت پیش‌فرض
                "windowsfilenames": True,    # نام فایل امن برای ویندوز
                "restrictfilenames": False,
                "progress_hooks": [self.progress_hook],
                "postprocessor_hooks": [self.postprocessor_hook],
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 20,
                # اجازه دانلود خودکار اسکریپت‌های حل‌کننده چالش جاوااسکریپت YouTube.
                # بدون این، برخی/همه فرمت‌های ویدئو ممکن است در دسترس نباشند
                # (فقط storyboard نمایش داده می‌شود).
                "remote_components": {"ejs:github"},
                # اگر از VPN/پروکسی (مثل v2rayN) استفاده می‌کنید، پورت زیر را با پورت
                # واقعی SOCKS یا HTTP نرم‌افزار خودتان جایگزین کنید.
                # اگر مستقیم به اینترنت متصل هستید (بدون پروکسی)، این خط را حذف یا
                # با "" مقداردهی کنید.
                "proxy": "socks5://127.0.0.1:10810",
                # برای رفع خطای "Sign in to confirm you're not a bot"، فایل کوکی
                # صادرشده از مرورگر (با اکستنشن "Get cookies.txt LOCALLY") استفاده می‌شود.
                # مسیر زیر را با مسیر واقعی فایل cookies.txt خودتان جایگزین کنید.
                "cookiefile": r"C:\Users\ali\Downloads\yotube.txt",
            }

            if quality_key == "audio_mp3":
                ydl_opts["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ]
            else:
                ydl_opts["merge_output_format"] = "mp4"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.root.after(0, self.on_download_success)

        except yt_dlp.utils.DownloadError as e:
            error_message = str(e)
            self.root.after(0, lambda: self.on_download_error(error_message))
        except Exception as e:
            error_message = str(e)
            self.root.after(0, lambda: self.on_download_error(error_message))

    # -----------------------------------------------------------------
    # Progress Hook (فراخوانی‌شده توسط yt-dlp حین دانلود)
    # -----------------------------------------------------------------
    def progress_hook(self, d: dict):
        status = d.get("status")

        if status == "downloading":
            downloaded = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            speed = d.get("speed")
            eta = d.get("eta")

            percent = (downloaded / total * 100) if total else 0
            speed_text = f"{speed / 1024 / 1024:.2f} MB/s" if speed else "نامشخص"
            eta_text = f"{eta} ثانیه" if eta is not None else "نامشخص"

            self.root.after(
                0,
                self.update_progress_ui,
                percent,
                f"در حال دانلود... {percent:.1f}%  |  سرعت: {speed_text}  |  زمان باقی‌مانده: {eta_text}",
            )

        elif status == "finished":
            self.root.after(
                0, self.update_progress_ui, 100, "دانلود کامل شد. در حال پردازش نهایی..."
            )

    def postprocessor_hook(self, d: dict):
        status = d.get("status")
        if status == "started":
            self.root.after(0, self.update_progress_ui, 100, "در حال پردازش نهایی فایل...")
        elif status == "finished":
            self.root.after(0, self.update_progress_ui, 100, "پردازش نهایی انجام شد.")

    # -----------------------------------------------------------------
    # به‌روزرسانی امن UI (فقط از Thread اصلی توسط root.after فراخوانی می‌شود)
    # -----------------------------------------------------------------
    def update_progress_ui(self, percent: float, status_text: str):
        self.progress_bar["value"] = percent
        self.status_var.set(status_text)

    def on_download_success(self):
        self.progress_bar["value"] = 100
        self.status_var.set("دانلود با موفقیت انجام شد.")
        self.is_downloading = False
        self.download_button.config(state="normal")
        messagebox.showinfo("موفقیت", "دانلود با موفقیت به پایان رسید.")

    def on_download_error(self, error_message: str):
        self.status_var.set("خطا در دانلود.")
        self.is_downloading = False
        self.download_button.config(state="normal")
        messagebox.showerror("خطا در دانلود", f"دانلود با خطا مواجه شد:\n{error_message}")


# ---------------------------------------------------------------------------
# اجرای برنامه
# ---------------------------------------------------------------------------
def main():
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()