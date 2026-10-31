# -*- coding: utf-8 -*-
import os
import sys
import time
import signal
import shutil
import threading
import subprocess
import webbrowser
import warnings
import winsound
from datetime import datetime
import numpy as np
import soundcard as sc
import soundfile as sf
import lameenc
import imageio_ffmpeg
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

warnings.filterwarnings('ignore', category=sc.SoundcardRuntimeWarning)

try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

def get_ffmpeg_binary():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_bin = os.path.join(script_dir, "ffmpeg.exe")
    if os.path.exists(local_bin):
        return local_bin
    user_bin = os.path.join(os.environ.get('USERPROFILE', ''), 'bin', 'ffmpeg.exe')
    if os.path.exists(user_bin):
        return user_bin
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'

def open_in_explorer(path, select=True):
    try:
        norm = os.path.normpath(path)
        if select and os.path.exists(norm):
            subprocess.Popen(['explorer.exe', f'/select,{norm}'])
        elif os.path.exists(norm):
            os.startfile(norm)
        else:
            parent = os.path.dirname(norm)
            if os.path.exists(parent):
                os.startfile(parent)
    except Exception as e:
        print(f"Error opening explorer: {e}")

class TrimDialog(tk.Toplevel):
    def __init__(self, parent, file_path, on_save_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.file_path = file_path
        self.on_save_callback = on_save_callback
        self.title("✂️ أداة استقطاع وتعديل التسجيلات - OMAR_REC")
        self.geometry("560x460")
        self.resizable(False, False)
        self.configure(bg="#0F172A")
        self.transient(parent)
        self.grab_set()

        self.total_duration = self._get_duration()
        self.total_str = self._format_sec(self.total_duration)

        self._build_ui()

    def _get_duration(self):
        try:
            exe = get_ffmpeg_binary()
            cmd = [exe, '-i', self.file_path]
            p = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            for line in p.stderr.split('\n'):
                if 'Duration:' in line:
                    part = line.split('Duration:')[1].split(',')[0].strip()
                    h, m, s = part.split(':')
                    return float(h) * 3600 + float(m) * 60 + float(s)
        except Exception:
            pass
        return 0.0

    def _format_sec(self, seconds):
        mins, secs = divmod(int(seconds), 60)
        hrs, mins = divmod(mins, 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"

    def _build_ui(self):
        header = tk.Frame(self, bg="#1E293B", pady=10)
        header.pack(fill="x")
        
        tk.Label(
            header,
            text="✂️ استقطاع وقص المقطع بدون إعادة رندرة (Fast Cut)",
            font=("Segoe UI", 12, "bold"),
            fg="#38BDF8",
            bg="#1E293B"
        ).pack()
        
        body = tk.Frame(self, bg="#0F172A", padx=20, pady=12)
        body.pack(fill="both", expand=True)

        info_card = tk.Frame(body, bg="#1E293B", padx=12, pady=10, highlightthickness=1, highlightbackground="#334155")
        info_card.pack(fill="x", pady=(0, 10))

        fname = os.path.basename(self.file_path)
        tk.Label(info_card, text=f"الملف المحدد: {fname}", font=("Segoe UI", 9, "bold"), fg="#E2E8F0", bg="#1E293B", anchor="w").pack(fill="x")
        tk.Label(info_card, text=f"المدة الإجمالية للملف: {self.total_str}", font=("Segoe UI", 10, "bold"), fg="#10B981", bg="#1E293B", anchor="w").pack(fill="x", pady=(2, 0))

        play_btn = tk.Button(
            body,
            text="▶️ تشغيل ومعاينة المقطع الآن لمعرفة أوقات القص",
            font=("Segoe UI", 9, "bold"),
            bg="#0284C7",
            fg="#FFFFFF",
            relief="flat",
            cursor="hand2",
            pady=6,
            command=self._play_file
        )
        play_btn.pack(fill="x", pady=(0, 12))

        cut_box = tk.LabelFrame(
            body,
            text=" حدد وقت البداية والنهاية للجزء المراد حفظه (HH:MM:SS) ",
            font=("Segoe UI", 9, "bold"),
            fg="#F59E0B",
            bg="#1E293B",
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground="#334155"
        )
        cut_box.pack(fill="x", pady=(0, 12))

        start_row = tk.Frame(cut_box, bg="#1E293B")
        start_row.pack(fill="x", pady=2)
        tk.Label(start_row, text="وقت البدء (Start):", font=("Segoe UI", 9, "bold"), fg="#E2E8F0", bg="#1E293B", width=16, anchor="w").pack(side="left")
        self.start_entry = tk.Entry(start_row, font=("Consolas", 10, "bold"), width=12, justify="center")
        self.start_entry.insert(0, "00:00:00")
        self.start_entry.pack(side="left")

        end_row = tk.Frame(cut_box, bg="#1E293B")
        end_row.pack(fill="x", pady=2)
        tk.Label(end_row, text="وقت النهاية (End):", font=("Segoe UI", 9, "bold"), fg="#E2E8F0", bg="#1E293B", width=16, anchor="w").pack(side="left")
        self.end_entry = tk.Entry(end_row, font=("Consolas", 10, "bold"), width=12, justify="center")
        self.end_entry.insert(0, self.total_str)
        self.end_entry.pack(side="left")

        act_frame = tk.Frame(body, bg="#0F172A")
        act_frame.pack(fill="x", pady=(5, 0))

        save_orig_btn = tk.Button(
            act_frame,
            text="✔ إبقاء الملف كاملاً بدون قص",
            font=("Segoe UI", 9, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            relief="flat",
            cursor="hand2",
            pady=7,
            command=self._keep_original
        )
        save_orig_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        cut_btn = tk.Button(
            act_frame,
            text="✂️ استقطاع وحفظ الجزء المحدد",
            font=("Segoe UI", 9, "bold"),
            bg="#D97706",
            fg="#FFFFFF",
            relief="flat",
            cursor="hand2",
            pady=7,
            command=self._perform_cut
        )
        cut_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))

    def _play_file(self):
        try:
            os.startfile(self.file_path)
        except Exception as e:
            messagebox.showerror("خطأ", f"تعذر تشغيل الملف: {e}")

    def _keep_original(self):
        if self.on_save_callback:
            self.on_save_callback(self.file_path)
        self.destroy()

    def _perform_cut(self):
        st = self.start_entry.get().strip()
        et = self.end_entry.get().strip()
        
        base, ext = os.path.splitext(self.file_path)
        trimmed_path = f"{base}_مستقطع_{st.replace(':', '-')}_إلى_{et.replace(':', '-')}{ext}"

        exe = get_ffmpeg_binary()
        cmd = [
            exe, '-y',
            '-ss', st,
            '-to', et,
            '-i', self.file_path,
            '-c', 'copy',
            trimmed_path
        ]

        try:
            p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            if p.returncode == 0 and os.path.exists(trimmed_path):
                messagebox.showinfo("تم الاستقطاع بنجاح", f"تم قص وحفظ المقطع المستقطع بنجاح في:\n{trimmed_path}")
                if self.on_save_callback:
                    self.on_save_callback(trimmed_path)
                open_in_explorer(trimmed_path, select=True)
                self.destroy()
            else:
                messagebox.showerror("خطأ", "تعذر قص المقطع، يرجى التأكد من صحة أوقات البدء والنهاية!")
        except Exception as ex:
            messagebox.showerror("خطأ", f"حدث استثناء أثناء القص: {ex}")

class MiniBar(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("OMAR_REC - شريط التحكم المصغر")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#0F172A", highlightthickness=2, highlightbackground="#0284C7")

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 570, 60
        x = sw - w - 25
        y = sh - h - 60
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._build_ui()
        self._bind_drag()

    def _build_ui(self):
        self.main_frame = tk.Frame(self, bg="#0F172A", padx=8, pady=4)
        self.main_frame.pack(fill="both", expand=True)

        self.drag_lbl = tk.Label(self.main_frame, text="⠿ REC", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#0F172A", cursor="fleur")
        self.drag_lbl.pack(side="left", padx=(0, 6))

        mode = self.app.record_mode_var.get()
        if mode == "video":
            mode_text = "🎥 صوت وصورة (MP4)"
            mode_fg = "#34D399"
            mode_bg = "#064E3B"
            mode_border = "#059669"
        else:
            mode_text = "🎙️ صوت فقط (MP3)"
            mode_fg = "#38BDF8"
            mode_bg = "#1E293B"
            mode_border = "#0284C7"

        self.mode_lbl = tk.Label(
            self.main_frame,
            text=mode_text,
            font=("Segoe UI", 9, "bold"),
            fg=mode_fg,
            bg=mode_bg,
            highlightthickness=1,
            highlightbackground=mode_border,
            padx=8,
            pady=3
        )
        self.mode_lbl.pack(side="left", padx=(0, 6))

        self.timer_lbl = tk.Label(self.main_frame, text="00:00:00", font=("Consolas", 14, "bold"), fg="#F8FAFC", bg="#1E293B", padx=6, pady=2)
        self.timer_lbl.pack(side="left", padx=(0, 6))

        self.pause_btn = tk.Button(
            self.main_frame,
            text="⏸️",
            font=("Segoe UI", 10, "bold"),
            bg="#D97706",
            fg="#FFFFFF",
            relief="flat",
            cursor="hand2",
            width=3,
            command=self.app.toggle_pause
        )
        self.pause_btn.pack(side="left", padx=(0, 4))

        self.stop_btn = tk.Button(
            self.main_frame,
            text="⏹ حفظ",
            font=("Segoe UI", 9, "bold"),
            bg="#EF4444",
            fg="#FFFFFF",
            relief="flat",
            cursor="hand2",
            padx=6,
            command=self.app.stop_recording
        )
        self.stop_btn.pack(side="left", padx=(0, 4))

        # زر كتم / إيقاف الإنذار عند الصمت
        self.mute_alarm_btn = tk.Button(
            self.main_frame,
            text="🔕 كتم التنبيه",
            font=("Segoe UI", 8, "bold"),
            bg="#DC2626",
            fg="#FFFFFF",
            relief="flat",
            cursor="hand2",
            padx=6,
            command=self.app.silence_alarm
        )

        self.expand_btn = tk.Button(
            self.main_frame,
            text="🗖 تكبير",
            font=("Segoe UI", 8, "bold"),
            bg="#334155",
            fg="#CBD5E1",
            relief="flat",
            cursor="hand2",
            padx=6,
            command=self.app.restore_from_mini
        )
        self.expand_btn.pack(side="right")

    def update_state(self, timer_str, is_paused):
        self.timer_lbl.config(text=timer_str)
        if is_paused:
            self.pause_btn.config(text="▶️", bg="#0284C7")
        else:
            self.pause_btn.config(text="⏸️", bg="#D97706")

    def set_alert_mode(self, active, flash_state=False):
        if active:
            color = "#EF4444" if flash_state else "#7F1D1D"
            self.configure(highlightbackground=color, highlightthickness=3)
            self.main_frame.configure(bg=color)
            self.drag_lbl.configure(bg=color, text="🚨 انقطاع الصوت!")
            if not self.mute_alarm_btn.winfo_ismapped():
                self.mute_alarm_btn.pack(side="right", padx=(0, 4))
        else:
            self.configure(highlightbackground="#0284C7", highlightthickness=2)
            self.main_frame.configure(bg="#0F172A")
            self.drag_lbl.configure(bg="#0F172A", text="⠿ REC")
            if self.mute_alarm_btn.winfo_ismapped():
                self.mute_alarm_btn.pack_forget()

    def _bind_drag(self):
        self.drag_lbl.bind("<ButtonPress-1>", self._start_move)
        self.drag_lbl.bind("<B1-Motion>", self._do_move)

    def _start_move(self, event):
        self.x = event.x
        self.y = event.y

    def _do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

class OmarRecApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OMAR_REC - مسجل الاجتماعات والمحاضرات الذكي")
        self.root.geometry("620x830")
        self.root.resizable(True, True)
        self.root.minsize(580, 750)
        self.root.configure(bg="#0F172A")

        icon_path = os.path.join(os.path.dirname(__file__), "mic_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        primary_dir = r"D:\DBA_Records"
        try:
            os.makedirs(primary_dir, exist_ok=True)
            default_dir = primary_dir
        except Exception:
            self.desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            default_dir = os.path.join(self.desktop, "تسجيلات_الورش")
            os.makedirs(default_dir, exist_ok=True)

        self.config_path = os.path.join(os.path.expanduser("~"), ".omar_rec_config.json")
        saved_mode = "video"
        saved_dir = default_dir
        if os.path.exists(self.config_path):
            try:
                import json
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    saved_mode = cfg.get("mode", "video")
                    if os.path.exists(cfg.get("dir", "")):
                        saved_dir = cfg.get("dir")
            except Exception:
                pass

        self.output_dir_var = tk.StringVar(value=saved_dir)
        self.record_mode_var = tk.StringVar(value=saved_mode)
        self.record_mode_var.trace_add("write", self._on_mode_change)
        self.output_dir_var.trace_add("write", lambda *_: self._save_config())
        self.auto_mini_var = tk.BooleanVar(value=True)

        self.devices_dict = {}
        self.selected_device_var = tk.StringVar()
        
        self.is_recording = False
        self.is_paused = False
        self.stop_event = threading.Event()
        
        self.active_period_start = 0.0
        self.accumulated_time = 0.0
        
        self.current_output_path = None
        self.segments = []  # list of (video_segment_path, audio_segment_path)
        self.current_segment_idx = 0
        self.active_segment_stop_event = None
        self.active_audio_thread = None
        self.target_dir = None
        self.session_timestamp = None
        self.mic = None
        self.video_proc = None
        self.record_thread = None

        self.mini_bar = None
        self.current_volume = 0.0
        self.silence_counter = 0

        # متغيرات الإنذار والوميض الأحمر
        self.alarm_active = False
        self.alarm_dismissed_until_sound = False
        self.flash_state = False

        self._build_ui()
        self._refresh_audio_devices()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#1E293B", pady=10)
        header.pack(fill="x")

        tk.Label(
            header,
            text="🎙️ OMAR_REC",
            font=("Segoe UI", 17, "bold"),
            fg="#38BDF8",
            bg="#1E293B"
        ).pack()

        tk.Label(
            header,
            text="المسجل الذكي للاجتماعات والمحاضرات (مع نظام الإنذار الحرج عند انقطاع الصوت)",
            font=("Segoe UI", 8),
            fg="#94A3B8",
            bg="#1E293B"
        ).pack(pady=(1, 0))

        body = tk.Frame(self.root, bg="#0F172A", padx=20, pady=10)
        body.pack(fill="both", expand=True)

        # 1. نوع التسجيل
        mode_card = tk.Frame(body, bg="#1E293B", padx=12, pady=8, highlightthickness=1, highlightbackground="#334155")
        mode_card.pack(fill="x", pady=(0, 6))

        tk.Label(
            mode_card,
            text="اختر نوع التسجيل المطلوب:",
            font=("Segoe UI", 9, "bold"),
            fg="#94A3B8",
            bg="#1E293B"
        ).pack(anchor="e", pady=(0, 4))

        modes_box = tk.Frame(mode_card, bg="#1E293B")
        modes_box.pack(fill="x")

        rb_video = tk.Radiobutton(
            modes_box,
            text="🎥 صوت وصورة (MP4 ذكي)",
            variable=self.record_mode_var,
            value="video",
            font=("Segoe UI", 10, "bold"),
            fg="#10B981",
            bg="#1E293B",
            activebackground="#1E293B",
            activeforeground="#10B981",
            selectcolor="#0F172A",
            cursor="hand2"
        )
        rb_video.pack(side="right", expand=True, fill="x", padx=4)

        rb_audio = tk.Radiobutton(
            modes_box,
            text="🎙️ صوت فقط (MP3 خفيف)",
            variable=self.record_mode_var,
            value="audio",
            font=("Segoe UI", 10, "bold"),
            fg="#38BDF8",
            bg="#1E293B",
            activebackground="#1E293B",
            activeforeground="#38BDF8",
            selectcolor="#0F172A",
            cursor="hand2"
        )
        rb_audio.pack(side="left", expand=True, fill="x", padx=4)

        self.mode_notice_lbl = tk.Label(
            mode_card,
            text="",
            font=("Segoe UI", 8, "bold"),
            bg="#1E293B",
            pady=3
        )
        self.mode_notice_lbl.pack(fill="x", pady=(3, 0))

        # 2. أدوات سريعة
        tools_card = tk.Frame(body, bg="#1E293B", padx=8, pady=6, highlightthickness=1, highlightbackground="#0284C7")
        tools_card.pack(fill="x", pady=(0, 8))

        vdesk_btn = tk.Button(
            tools_card,
            text="🖥️ عزل نافذة الورشة (Virtual Desktop)",
            font=("Segoe UI", 9, "bold"),
            bg="#0284C7",
            fg="#FFFFFF",
            activebackground="#0369A1",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            pady=6,
            command=self._open_virtual_desktop_guide
        )
        vdesk_btn.pack(side="left", fill="x", expand=True, padx=(0, 3))

        edit_prev_btn = tk.Button(
            tools_card,
            text="✂️ استقطاع / قص فيديو أو صوت سابق",
            font=("Segoe UI", 9, "bold"),
            bg="#D97706",
            fg="#FFFFFF",
            activebackground="#B45309",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            pady=6,
            command=self.open_trim_existing_file
        )
        edit_prev_btn.pack(side="right", fill="x", expand=True, padx=(3, 0))

        # 3. مخرج الصوت
        dev_lbl_frame = tk.Frame(body, bg="#0F172A")
        dev_lbl_frame.pack(fill="x")
        
        tk.Label(
            dev_lbl_frame,
            text="مخرج الصوت (السماعة التي تسمع منها الاجتماع):",
            font=("Segoe UI", 9, "bold"),
            fg="#38BDF8",
            bg="#0F172A"
        ).pack(anchor="e")

        self.device_combo = ttk.Combobox(
            body,
            textvariable=self.selected_device_var,
            state="readonly",
            font=("Segoe UI", 9)
        )
        self.device_combo.pack(fill="x", pady=(2, 4))

        dev_btns_frame = tk.Frame(body, bg="#0F172A")
        dev_btns_frame.pack(fill="x", pady=(0, 8))

        test_sound_btn = tk.Button(
            dev_btns_frame,
            text="🔍 فحص إشارة الصوت",
            font=("Segoe UI", 9, "bold"),
            bg="#0369A1",
            fg="#F8FAFC",
            activebackground="#0284C7",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            pady=4,
            command=self._test_audio_signal
        )
        test_sound_btn.pack(side="left", fill="x", expand=True, padx=(0, 3))

        refresh_btn = tk.Button(
            dev_btns_frame,
            text="🔄 تحديث الأجهزة",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#F8FAFC",
            activebackground="#475569",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            pady=4,
            command=self._refresh_audio_devices
        )
        refresh_btn.pack(side="right", fill="x", expand=True, padx=(3, 0))

        # 4. الرابط والشريط المصغر
        tk.Label(
            body,
            text="رابط الاجتماع أو الويب (اختياري):",
            font=("Segoe UI", 9, "bold"),
            fg="#E2E8F0",
            bg="#0F172A"
        ).pack(anchor="e")

        url_input_frame = tk.Frame(body, bg="#0F172A")
        url_input_frame.pack(fill="x", pady=(2, 3))

        self.url_entry = tk.Entry(
            url_input_frame,
            font=("Segoe UI", 9),
            bg="#1E293B",
            fg="#FFFFFF",
            insertbackground="#38BDF8",
            relief="flat",
            highlightthickness=1,
            highlightcolor="#38BDF8",
            highlightbackground="#334155"
        )
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 6))

        tk.Button(
            url_input_frame,
            text="📋 لصق",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#F8FAFC",
            relief="flat",
            cursor="hand2",
            padx=8,
            command=self._paste_clipboard
        ).pack(side="right")

        opts_frame = tk.Frame(body, bg="#0F172A")
        opts_frame.pack(fill="x", pady=(0, 4))

        self.auto_open_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            opts_frame,
            text="فتح الرابط تلقائياً",
            variable=self.auto_open_var,
            font=("Segoe UI", 8),
            fg="#94A3B8",
            bg="#0F172A",
            activebackground="#0F172A",
            activeforeground="#38BDF8",
            selectcolor="#1E293B",
            cursor="hand2"
        ).pack(side="left")

        tk.Checkbutton(
            opts_frame,
            text="📌 تصغير إلى شريط عائم في الأسفل (Minimized Bar)",
            variable=self.auto_mini_var,
            font=("Segoe UI", 8, "bold"),
            fg="#38BDF8",
            bg="#0F172A",
            activebackground="#0F172A",
            activeforeground="#38BDF8",
            selectcolor="#1E293B",
            cursor="hand2"
        ).pack(side="right")

        # 5. مكان الحفظ
        tk.Label(
            body,
            text="مكان حفظ التسجيل:",
            font=("Segoe UI", 9, "bold"),
            fg="#E2E8F0",
            bg="#0F172A"
        ).pack(anchor="e")

        dir_frame = tk.Frame(body, bg="#0F172A")
        dir_frame.pack(fill="x", pady=(2, 6))

        self.dir_entry = tk.Entry(
            dir_frame,
            textvariable=self.output_dir_var,
            font=("Segoe UI", 9),
            bg="#1E293B",
            fg="#94A3B8",
            relief="flat",
            highlightthickness=1,
            highlightcolor="#38BDF8",
            highlightbackground="#334155"
        )
        self.dir_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 6))

        tk.Button(
            dir_frame,
            text="📂 تغيير...",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#F8FAFC",
            relief="flat",
            cursor="hand2",
            padx=8,
            command=self._browse_directory
        ).pack(side="right")

        # 6. بطاقة العداد والـ VU Meter (تدعم إطار التحذير الأحمر الوامض)
        self.monitor_card = tk.Frame(body, bg="#1E293B", padx=12, pady=8, highlightthickness=2, highlightbackground="#334155")
        self.monitor_card.pack(fill="x", pady=2)

        self.status_badge = tk.Label(
            self.monitor_card,
            text="⚪ في وضع الاستعداد",
            font=("Segoe UI", 10, "bold"),
            fg="#94A3B8",
            bg="#1E293B"
        )
        self.status_badge.pack()

        self.timer_lbl = tk.Label(
            self.monitor_card,
            text="00:00:00",
            font=("Consolas", 24, "bold"),
            fg="#F8FAFC",
            bg="#1E293B"
        )
        self.timer_lbl.pack(pady=1)

        meter_header = tk.Frame(self.monitor_card, bg="#1E293B")
        meter_header.pack(fill="x", pady=(2, 2))
        
        self.meter_text = tk.Label(
            meter_header,
            text="مؤشر الإشارة الصوتية الحية: 0%",
            font=("Segoe UI", 8, "bold"),
            fg="#94A3B8",
            bg="#1E293B"
        )
        self.meter_text.pack(side="left")

        self.meter_canvas = tk.Canvas(self.monitor_card, height=12, bg="#0F172A", highlightthickness=1, highlightbackground="#334155")
        self.meter_canvas.pack(fill="x", pady=(0, 2))

        # تنبيه الصمت الحرج مع زر الكتم داخل البطاقة
        self.alert_banner_frame = tk.Frame(self.monitor_card, bg="#1E293B")
        self.alert_banner_frame.pack(fill="x", pady=(2, 0))

        self.silence_warning_lbl = tk.Label(
            self.alert_banner_frame,
            text="",
            font=("Segoe UI", 9, "bold"),
            fg="#EF4444",
            bg="#1E293B"
        )
        self.silence_warning_lbl.pack(side="left", fill="x", expand=True)

        self.main_mute_alarm_btn = tk.Button(
            self.alert_banner_frame,
            text="🔕 إيقاف التنبيه الصوتي",
            font=("Segoe UI", 8, "bold"),
            bg="#DC2626",
            fg="#FFFFFF",
            relief="flat",
            cursor="hand2",
            padx=8,
            command=self.silence_alarm
        )

        self.info_lbl = tk.Label(
            self.monitor_card,
            text="الحجم: 0.00 MB  |  الصيغة: MP3 / MP4 ذكي",
            font=("Segoe UI", 8),
            fg="#64748B",
            bg="#1E293B"
        )
        self.info_lbl.pack(pady=(1, 0))

        # 7. أزرار التحكم
        btn_frame = tk.Frame(body, bg="#0F172A", pady=8)
        btn_frame.pack(fill="x")

        self.start_btn = tk.Button(
            btn_frame,
            text="▶️ بدء التسجيل",
            font=("Segoe UI", 11, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            activebackground="#059669",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            pady=9,
            command=self.start_recording
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.pause_btn = tk.Button(
            btn_frame,
            text="⏸️ إيقاف مؤقت",
            font=("Segoe UI", 11, "bold"),
            bg="#475569",
            fg="#FFFFFF",
            activebackground="#D97706",
            activeforeground="#FFFFFF",
            relief="flat",
            state="disabled",
            cursor="hand2",
            pady=9,
            command=self.toggle_pause
        )
        self.pause_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.stop_btn = tk.Button(
            btn_frame,
            text="⏹ إيقاف وحفظ",
            font=("Segoe UI", 11, "bold"),
            bg="#475569",
            fg="#FFFFFF",
            activebackground="#DC2626",
            activeforeground="#FFFFFF",
            relief="flat",
            state="disabled",
            cursor="hand2",
            pady=9,
            command=self.stop_recording
        )
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(0, 0))

        tk.Button(
            body,
            text=r"📁 فتح مجلد الحفظ الحالي (D:\DBA_Records)",
            font=("Segoe UI", 8),
            bg="#1E293B",
            fg="#94A3B8",
            relief="flat",
            cursor="hand2",
            pady=4,
            command=self.open_folder
        ).pack(fill="x", pady=(2, 0))

        self._on_mode_change()

    def _save_config(self):
        try:
            import json
            cfg = {
                "mode": self.record_mode_var.get(),
                "dir": self.output_dir_var.get()
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False)
        except Exception:
            pass

    def _on_mode_change(self, *args):
        mode = self.record_mode_var.get()
        if mode == "video":
            if hasattr(self, 'mode_notice_lbl'):
                self.mode_notice_lbl.config(
                    text="🎥 الوضع المفعل: تسجيل شاشة كاملة + صوت (فيديو MP4 عالي الكفاءة)",
                    fg="#10B981"
                )
            if hasattr(self, 'start_btn') and not self.is_recording:
                self.start_btn.config(text="▶️ بدء تسجيل (فيديو + صوت MP4)", bg="#10B981")
        else:
            if hasattr(self, 'mode_notice_lbl'):
                self.mode_notice_lbl.config(
                    text="🎵 الوضع المفعل: تسجيل صوت فقط بدون تصوير شاشة (MP3 خفيف)",
                    fg="#38BDF8"
                )
            if hasattr(self, 'start_btn') and not self.is_recording:
                self.start_btn.config(text="▶️ بدء تسجيل (صوت فقط MP3)", bg="#0284C7")
        self._save_config()

    def silence_alarm(self):
        self.alarm_dismissed_until_sound = True
        self.silence_warning_lbl.config(text="🔕 تم كتم صوت التنبيه مؤقتاً (الصمت ما زال مستمراً!)", fg="#F59E0B")
        if self.main_mute_alarm_btn.winfo_ismapped():
            self.main_mute_alarm_btn.pack_forget()
        if self.mini_bar:
            self.mini_bar.set_alert_mode(False)

    def open_trim_existing_file(self):
        initial = self.output_dir_var.get().strip()
        if not os.path.exists(initial):
            initial = r"D:\DBA_Records" if os.path.exists(r"D:\DBA_Records") else self.desktop

        file_path = filedialog.askopenfilename(
            parent=self.root,
            initialdir=initial,
            title="اختر ملف فيديو أو صوت لاستقطاعه",
            filetypes=[
                ("ملفات الوسائط", "*.mp4;*.mp3;*.wav;*.mkv;*.m4a;*.webm;*.avi"),
                ("فيديو MP4", "*.mp4"),
                ("صوت MP3", "*.mp3"),
                ("جميع الملفات", "*.*")
            ]
        )
        if file_path:
            TrimDialog(self.root, file_path, self._on_final_saved)

    def _open_virtual_desktop_guide(self):
        try:
            subprocess.Popen("explorer.exe shell:::{3080F90E-D7AD-11D9-BD98-0000947B0257}", shell=True)
        except Exception:
            pass

        guide_msg = (
            "🖥️ ميزة عزل التسجيل في سطح مكتب افتراضي (Virtual Desktop):\n\n"
            "تم الآن فتح شاشة أسطح المكتب المتعددة (Task View) في ويندوز:\n\n"
            "1. اضغط في الأعلى على (+ New Desktop / سطح مكتب جديد).\n"
            "2. اسحب نافذة الورشة (Webex أو المتصفح) وضعها في سطح المكتب الجديد (Desktop 2).\n"
            "3. يمكنك الآن متابعة عملك الخاص على (Desktop 1) بحرية تامة دون أن تشغل شاشتك ودون أن يظهر عملك في الفيديو المسجل!\n\n"
            "ملاحظة: يمكنك التنقل بين أسطح المكتب في أي وقت بالضغط على (Ctrl + Win + السهم الأيمن/الأيسر)."
        )
        messagebox.showinfo("عزل التسجيل (Virtual Desktop)", guide_msg)

    def _refresh_audio_devices(self):
        try:
            mics = sc.all_microphones(include_loopback=True)
            loopbacks = [m for m in mics if m.isloopback]
            default_spk = sc.default_speaker()
            
            self.devices_dict.clear()
            device_names = []
            default_selection = ""

            for m in loopbacks:
                name = m.name
                if default_spk and default_spk.name in name:
                    display_name = f"⭐ {name} (الافتراضي)"
                    default_selection = display_name
                else:
                    display_name = f"🔊 {name}"
                
                self.devices_dict[display_name] = m
                device_names.append(display_name)

            self.device_combo['values'] = device_names
            if default_selection and default_selection in device_names:
                self.selected_device_var.set(default_selection)
            elif device_names:
                self.selected_device_var.set(device_names[0])
            else:
                self.selected_device_var.set("لم يتم العثور على أجهزة صوت!")
        except Exception as e:
            print(f"Error refreshing devices: {e}")

    def _test_audio_signal(self):
        if self.is_recording:
            messagebox.showinfo("تنبيه", "التسجيل قيد التشغيل بالفعل!")
            return

        selected_name = self.selected_device_var.get()
        mic = self.devices_dict.get(selected_name)
        if not mic:
            messagebox.showwarning("خطأ", "يرجى اختيار مخرج صوت أولاً!")
            return

        self.meter_text.config(text="🔍 جاري فحص الإشارة (ثانيتان)...", fg="#38BDF8")
        self.root.update()

        def worker():
            try:
                samplerate = 44100
                with mic.recorder(samplerate=samplerate, channels=2) as rec:
                    data = rec.record(numframes=samplerate)
                    rms = float(np.sqrt(np.mean(data**2)))
                    peak = float(np.max(np.abs(data)))

                pct = min(100, int(rms * 400))
                self.root.after(0, lambda: self._show_test_result(pct, peak))
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("خطأ", f"تعذر فحص الجهاز: {ex}"))

        threading.Thread(target=worker, daemon=True).start()

    def _show_test_result(self, pct, peak):
        self._update_meter_bar(pct)
        if pct > 1 or peak > 0.01:
            self.meter_text.config(text=f"✔ إشارة ممتازة! المستوى: {pct}% (الصوت يعمل)", fg="#10B981")
            messagebox.showinfo("نجاح الفحص", f"تم التقاط إشارة الصوت بنجاح! ({pct}%)\nالمخرج المختار جاهز للتسجيل بدون أي مشاكل.")
        else:
            self.meter_text.config(text="⚠️ الإشارة: 0% (صمت تام)", fg="#EF4444")
            messagebox.showwarning(
                "تنبيه: لا يوجد صوت!",
                "لم يتم رصد أي صوت يخرج من هذا الجهاز حالياً (الإشارة 0%)!\n\n"
                "• تأكد من تشغيل صوت في الورشة أو مقطع فيديو الآن.\n"
                "• إذا كنت تستخدم سماعة بلوتوث أو خارجية، اخترها من القائمة واضغط فحص مجدداً."
            )

    def _update_meter_bar(self, pct):
        self.meter_canvas.delete("all")
        width = self.meter_canvas.winfo_width()
        if width <= 1:
            width = 480
        height = self.meter_canvas.winfo_height()
        if height <= 1:
            height = 12

        fill_width = int((pct / 100.0) * width)
        
        if pct < 60:
            color = "#10B981"
        elif pct < 85:
            color = "#F59E0B"
        else:
            color = "#EF4444"

        if fill_width > 0:
            self.meter_canvas.create_rectangle(0, 0, fill_width, height, fill=color, width=0)

    def _paste_clipboard(self):
        try:
            text = self.root.clipboard_get()
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, text.strip())
        except Exception:
            pass

    def _browse_directory(self):
        try:
            current = self.output_dir_var.get().strip()
            initial = current if (current and os.path.exists(current)) else r"D:\DBA_Records"
            self.root.update_idletasks()
            chosen = filedialog.askdirectory(
                parent=self.root,
                initialdir=initial,
                title="اختر مجلد حفظ التسجيلات",
                mustexist=False
            )
            if chosen:
                norm = os.path.normpath(chosen)
                os.makedirs(norm, exist_ok=True)
                self.output_dir_var.set(norm)
        except Exception as e:
            messagebox.showerror("خطأ", f"تعذر استعراض المجلد: {e}")
        finally:
            self.root.update_idletasks()

    def start_recording(self):
        target_dir = self.output_dir_var.get().strip()
        if not target_dir:
            messagebox.showwarning("تنبيه", "يرجى تحديد مجلد حفظ التسجيل أولاً!")
            return
        os.makedirs(target_dir, exist_ok=True)

        selected_name = self.selected_device_var.get()
        mic = self.devices_dict.get(selected_name)
        if not mic:
            messagebox.showerror("خطأ", "يرجى اختيار مخرج صوت صالح من القائمة!")
            return

        url = self.url_entry.get().strip()
        if url and self.auto_open_var.get():
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            webbrowser.open(url)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        mode = self.record_mode_var.get()
        self.session_timestamp = timestamp
        self.target_dir = target_dir
        self.mic = mic
        self.record_mode = mode
        self.segments = []
        self.current_segment_idx = 0

        ext = ".mp4" if mode == "video" else ".mp3"
        filename = f"تسجيل_{timestamp}{ext}"
        self.current_output_path = os.path.join(target_dir, filename)

        self.is_recording = True
        self.is_paused = False
        self.stop_event.clear()
        
        self.active_period_start = time.time()
        self.accumulated_time = 0.0
        self.silence_counter = 0

        # تصفير الإنذارات
        self.alarm_active = False
        self.alarm_dismissed_until_sound = False
        self.flash_state = False

        self.start_btn.config(state="disabled", bg="#475569")
        self.pause_btn.config(state="normal", bg="#D97706", text="⏸️ إيقاف مؤقت")
        self.stop_btn.config(state="normal", bg="#EF4444")
        
        self.device_combo.config(state="disabled")
        self.dir_entry.config(state="disabled")
        
        mode_text = "فيديو + صوت (MP4)" if mode == "video" else "صوت فقط (MP3)"
        self.status_badge.config(text=f"🔴 جاري تسجيل {mode_text} الآن...", fg="#EF4444")
        self.silence_warning_lbl.config(text="")
        if self.main_mute_alarm_btn.winfo_ismapped():
            self.main_mute_alarm_btn.pack_forget()

        if mode == "video":
            self._start_video_segment()
        else:
            self.record_thread = threading.Thread(target=self._record_worker_audio, args=(mic,), daemon=True)
            self.record_thread.start()

        if self.auto_mini_var.get():
            self._show_mini_bar()

        self._update_timer()

    def _show_mini_bar(self):
        if not self.mini_bar:
            self.mini_bar = MiniBar(self)
        self.root.withdraw()

    def restore_from_mini(self):
        if self.mini_bar:
            self.mini_bar.destroy()
            self.mini_bar = None
        self.root.deiconify()
        self.root.lift()

    def _start_video_segment(self):
        try:
            self.current_segment_idx += 1
            idx = self.current_segment_idx
            seg_vid = os.path.join(self.target_dir, f"_temp_v_{self.session_timestamp}_{idx}.mp4")
            seg_aud = os.path.join(self.target_dir, f"_temp_a_{self.session_timestamp}_{idx}.wav")
            self.segments.append((seg_vid, seg_aud))

            exe = get_ffmpeg_binary()
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                w = ctypes.windll.user32.GetSystemMetrics(0)
                h = ctypes.windll.user32.GetSystemMetrics(1)
            except Exception:
                w, h = 1920, 1080

            cmd = [
                exe, '-y',
                '-f', 'gdigrab',
                '-framerate', '15',
                '-video_size', f'{w}x{h}',
                '-i', 'desktop',
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '26',
                '-pix_fmt', 'yuv420p',
                seg_vid
            ]

            self.video_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

            self.active_segment_stop_event = threading.Event()
            self.active_audio_thread = threading.Thread(
                target=self._record_audio_segment,
                args=(self.mic, seg_aud, self.active_segment_stop_event),
                daemon=True
            )
            self.active_audio_thread.start()
        except Exception as e:
            print(f"Error starting video segment: {e}")

    def _stop_video_segment(self):
        # 1. إيقاف مسجل الصوت لهذا المقطع بأمان
        if self.active_segment_stop_event:
            self.active_segment_stop_event.set()
        if self.active_audio_thread and self.active_audio_thread.is_alive():
            self.active_audio_thread.join(timeout=3.0)
        self.active_audio_thread = None
        self.active_segment_stop_event = None

        # 2. إيقاف عملية تسجيل الفيديو بـ CTRL_BREAK_EVENT لحفظ وترميز الإطارات بنجاح
        if self.video_proc:
            try:
                self.video_proc.send_signal(signal.CTRL_BREAK_EVENT)
                self.video_proc.wait(timeout=4.0)
            except Exception:
                try:
                    self.video_proc.terminate()
                    self.video_proc.wait(timeout=3.0)
                except Exception:
                    try:
                        self.video_proc.kill()
                    except Exception:
                        pass
            self.video_proc = None

    def toggle_pause(self):
        if not self.is_recording:
            return

        if not self.is_paused:
            self.accumulated_time += time.time() - self.active_period_start
            self.is_paused = True
            
            self.pause_btn.config(text="▶️ استئناف التسجيل", bg="#0284C7")
            self.status_badge.config(text="⏸️ التسجيل متوقف مؤقتاً (استراحة)", fg="#F59E0B")
            self.meter_text.config(text="مؤشر الإشارة: متوقف مؤقتاً (استراحة)", fg="#F59E0B")
            self.silence_warning_lbl.config(text="")
            if self.main_mute_alarm_btn.winfo_ismapped():
                self.main_mute_alarm_btn.pack_forget()
            self._update_meter_bar(0)
            self._set_alert_mode(False)

            # في وضع الفيديو: إيقاف تسجيل الفيديو والصوت تماماً أثناء الاستراحة
            if self.record_mode_var.get() == "video":
                self._stop_video_segment()
        else:
            self.active_period_start = time.time()
            self.is_paused = False
            self.silence_counter = 0
            
            self.pause_btn.config(text="⏸️ إيقاف مؤقت", bg="#D97706")
            mode_text = "فيديو + صوت (MP4)" if self.record_mode_var.get() == "video" else "صوت فقط (MP3)"
            self.status_badge.config(text=f"🔴 جاري تسجيل {mode_text} الآن...", fg="#EF4444")
            self.meter_text.config(text="مؤشر الإشارة الصوتية الحية: 0%", fg="#94A3B8")

            # في وضع الفيديو: بدء مقطع متزامن جديد للشاشة والصوت فور الاستئناف
            if self.record_mode_var.get() == "video":
                self._start_video_segment()

        if self.mini_bar:
            elapsed = int(self.accumulated_time if self.is_paused else (self.accumulated_time + (time.time() - self.active_period_start)))
            mins, secs = divmod(elapsed, 60)
            hrs, mins = divmod(mins, 60)
            self.mini_bar.update_state(f"{hrs:02d}:{mins:02d}:{secs:02d}", self.is_paused)

    def _record_audio_segment(self, loopback_mic, audio_path, stop_event):
        samplerate = 44100
        chunk_frames = samplerate // 4

        try:
            with sf.SoundFile(audio_path, mode='w', samplerate=samplerate, channels=2, format='WAV', subtype='PCM_16') as wav_file:
                while not stop_event.is_set() and not self.stop_event.is_set():
                    try:
                        with loopback_mic.recorder(samplerate=samplerate, channels=2) as rec:
                            while not stop_event.is_set() and not self.stop_event.is_set():
                                data = rec.record(numframes=chunk_frames)
                                rms = float(np.sqrt(np.mean(data**2)))
                                self.current_volume = min(100.0, rms * 400.0)
                                wav_file.write(data)
                    except Exception as ex:
                        if stop_event.is_set() or self.stop_event.is_set():
                            break
                        print(f"Transient audio device glitch: {ex}. Reconnecting...")
                        time.sleep(0.3)
                        try:
                            mics = sc.all_microphones(include_loopback=True)
                            for m in mics:
                                if m.isloopback and (loopback_mic.name in m.name or m.name in loopback_mic.name):
                                    loopback_mic = m
                                    break
                        except Exception:
                            pass
        except Exception as e:
            print(f"Fatal error in audio segment recording: {e}")

    def _record_worker_audio(self, loopback_mic):
        samplerate = 44100
        chunk_frames = samplerate // 4
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(128)
        encoder.set_in_sample_rate(samplerate)
        encoder.set_channels(2)
        encoder.set_quality(2)

        try:
            with open(self.current_output_path, 'wb') as mp3_file:
                while not self.stop_event.is_set():
                    try:
                        with loopback_mic.recorder(samplerate=samplerate, channels=2) as rec:
                            while not self.stop_event.is_set():
                                data = rec.record(numframes=chunk_frames)
                                if self.is_paused:
                                    self.current_volume = 0.0
                                    time.sleep(0.05)
                                    continue

                                rms = float(np.sqrt(np.mean(data**2)))
                                self.current_volume = min(100.0, rms * 400.0)

                                int16_data = (data * 32767).clip(-32768, 32767).astype(np.int16)
                                mp3_bytes = encoder.encode(int16_data.tobytes())
                                mp3_file.write(mp3_bytes)
                    except Exception as ex:
                        if self.stop_event.is_set():
                            break
                        print(f"Transient audio error in MP3 mode: {ex}. Reconnecting...")
                        time.sleep(0.3)
                        try:
                            mics = sc.all_microphones(include_loopback=True)
                            for m in mics:
                                if m.isloopback and (loopback_mic.name in m.name or m.name in loopback_mic.name):
                                    loopback_mic = m
                                    break
                        except Exception:
                            pass

                final_bytes = encoder.flush()
                if final_bytes:
                    mp3_file.write(final_bytes)
        except Exception as e:
            print(f"Fatal error in MP3 recording: {e}")

    def _set_alert_mode(self, active):
        self.alarm_active = active
        if not active:
            self.monitor_card.config(highlightbackground="#334155", highlightthickness=2)
            if self.main_mute_alarm_btn.winfo_ismapped():
                self.main_mute_alarm_btn.pack_forget()
            if self.mini_bar:
                self.mini_bar.set_alert_mode(False)

    def _update_timer(self):
        if self.is_recording:
            if self.is_paused:
                elapsed = int(self.accumulated_time)
                mins, secs = divmod(elapsed, 60)
                hrs, mins = divmod(mins, 60)
                time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
                self.timer_lbl.config(text=time_str)
                self._update_meter_bar(0)
                if self.mini_bar:
                    self.mini_bar.update_state(time_str, True)
                self.root.after(500, self._update_timer)
                return

            elapsed = int(self.accumulated_time + (time.time() - self.active_period_start))
            mins, secs = divmod(elapsed, 60)
            hrs, mins = divmod(mins, 60)
            time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
            self.timer_lbl.config(text=time_str)

            if self.mini_bar:
                self.mini_bar.update_state(time_str, False)

            vol_pct = int(self.current_volume)
            self._update_meter_bar(vol_pct)
            
            # فحص الصمت الحرج (> 30 ثانية)
            if vol_pct < 1:
                self.silence_counter += 0.5
                self.meter_text.config(text=f"مؤشر الإشارة: 0% (صمت متواصل {int(self.silence_counter)} ثانية)", fg="#94A3B8")
                
                # إذا استمر الصمت أكثر من 30 ثانية متواصلة
                if self.silence_counter >= 30.0:
                    self.flash_state = not self.flash_state
                    self._set_alert_mode(True)
                    
                    # إطار أحمر متكرر ووميض مستمر
                    card_border = "#EF4444" if self.flash_state else "#7F1D1D"
                    self.monitor_card.config(highlightbackground=card_border, highlightthickness=3)

                    self.silence_warning_lbl.config(
                        text=f"🚨 إنذار حرج: انقطاع تام للصوت منذ {int(self.silence_counter)} ثانية!\nتأكد من اختيار السماعة الصحيحة أو إعادة وصلها."
                    )
                    if not self.alarm_dismissed_until_sound:
                        if not self.main_mute_alarm_btn.winfo_ismapped():
                            self.main_mute_alarm_btn.pack(side="right", padx=(4, 0))
                        
                        # نغمة تنبيه صوتية متكررة كل ثانيتين
                        if int(self.silence_counter) % 2 == 0:
                            try:
                                winsound.MessageBeep(winsound.MB_ICONHAND)
                            except Exception:
                                pass

                    if self.mini_bar:
                        self.mini_bar.set_alert_mode(not self.alarm_dismissed_until_sound, self.flash_state)

                elif self.silence_counter >= 10.0:
                    self.silence_warning_lbl.config(
                        text=f"⚠️ تنبيه: لا توجد إشارة صوتية منذ {int(self.silence_counter)} ثانية (تأكد من عدم كتم الصوت)."
                    )
            else:
                # عودة الصوت تلقائياً -> إلغاء الإنذار وإعادة تعيين الحالة
                if self.silence_counter >= 30.0:
                    self.silence_warning_lbl.config(text="✔ تم رصد واستئناف إشارة الصوت بنجاح!", fg="#10B981")
                else:
                    self.silence_warning_lbl.config(text="", fg="#EF4444")

                self.silence_counter = 0
                self.alarm_dismissed_until_sound = False
                self._set_alert_mode(False)
                self.meter_text.config(text=f"مؤشر الإشارة: {vol_pct}% (الصوت يعمل بوضوح)", fg="#10B981")

            if self.record_mode_var.get() == "audio":
                if self.current_output_path and os.path.exists(self.current_output_path):
                    size_mb = os.path.getsize(self.current_output_path) / (1024 * 1024)
                    self.info_lbl.config(text=f"الحجم التقريبي: {size_mb:.2f} MB  |  الصيغة: MP3")
            else:
                total_bytes = 0
                for v_seg, a_seg in self.segments:
                    if os.path.exists(v_seg): total_bytes += os.path.getsize(v_seg)
                    if os.path.exists(a_seg): total_bytes += os.path.getsize(a_seg)
                size_mb = total_bytes / (1024 * 1024)
                self.info_lbl.config(text=f"الحجم التقريبي: {size_mb:.2f} MB  |  الصيغة: MP4 ذكي")

            self.root.after(500, self._update_timer)

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self.stop_event.set()

        self.restore_from_mini()
        self._set_alert_mode(False)

        self.start_btn.config(state="normal")
        self._on_mode_change()
        self.pause_btn.config(state="disabled", bg="#475569", text="⏸️ إيقاف مؤقت")
        self.stop_btn.config(state="disabled", bg="#475569")
        
        self.device_combo.config(state="readonly")
        self.dir_entry.config(state="normal")
        
        self.status_badge.config(text="⏳ جاري دمج وتجهيز التسجيل...", fg="#38BDF8")
        self.root.update()

        if self.record_mode_var.get() == "video":
            if not self.is_paused:
                self._stop_video_segment()
            self._mux_all_segments()
        else:
            if self.record_thread and self.record_thread.is_alive():
                self.record_thread.join(timeout=3.0)

        self.status_badge.config(text="✔ تم حفظ التسجيل بنجاح", fg="#10B981")
        self.silence_warning_lbl.config(text="")
        if self.main_mute_alarm_btn.winfo_ismapped():
            self.main_mute_alarm_btn.pack_forget()
        self._update_meter_bar(0)
        self.meter_text.config(text="مؤشر الإشارة الصوتية: 0%", fg="#94A3B8")

        if self.current_output_path and os.path.exists(self.current_output_path):
            fname = os.path.basename(self.current_output_path)
            ans = messagebox.askyesno(
                "تم حفظ التسجيل بنجاح",
                f"تم حفظ التسجيل الجديد بنجاح:\n{fname}\n\nهل ترغب في استقطاع أو قص جزء معين من التسجيل الآن قبل الاعتماد النهائي؟"
            )
            if ans:
                TrimDialog(self.root, self.current_output_path, self._on_final_saved)
            else:
                self._on_final_saved(self.current_output_path)

    def _mux_all_segments(self):
        if not self.segments:
            return

        exe = get_ffmpeg_binary()

        # حالة عدم استخدام Pause إطلاقاً (مقطع وحيد)
        if len(self.segments) == 1:
            seg_vid, seg_aud = self.segments[0]
            if os.path.exists(seg_vid) and os.path.exists(seg_aud):
                cmd = [
                    exe, '-y',
                    '-i', seg_vid,
                    '-i', seg_aud,
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    self.current_output_path
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            elif os.path.exists(seg_vid):
                shutil.move(seg_vid, self.current_output_path)
        else:
            # حالة استخدام Pause عدة مرات: دمج كل مقطع ثم جمع المقاطع معاً بـ Concat
            muxed_segment_paths = []
            for idx, (seg_vid, seg_aud) in enumerate(self.segments, 1):
                if not os.path.exists(seg_vid):
                    continue
                seg_muxed = os.path.join(self.target_dir, f"_temp_mux_{self.session_timestamp}_{idx}.mp4")
                if os.path.exists(seg_aud):
                    cmd = [
                        exe, '-y',
                        '-i', seg_vid,
                        '-i', seg_aud,
                        '-c:v', 'copy',
                        '-c:a', 'aac',
                        '-b:a', '128k',
                        '-movflags', '+faststart',
                        seg_muxed
                    ]
                else:
                    cmd = [
                        exe, '-y',
                        '-i', seg_vid,
                        '-c:v', 'copy',
                        '-movflags', '+faststart',
                        seg_muxed
                    ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
                if os.path.exists(seg_muxed):
                    muxed_segment_paths.append(seg_muxed)

            if len(muxed_segment_paths) == 1:
                shutil.move(muxed_segment_paths[0], self.current_output_path)
            elif len(muxed_segment_paths) > 1:
                concat_list_file = os.path.join(self.target_dir, f"_concat_{self.session_timestamp}.txt")
                with open(concat_list_file, 'w', encoding='utf-8') as f:
                    for p in muxed_segment_paths:
                        norm = p.replace('\\', '/')
                        f.write(f"file '{norm}'\n")

                cmd_concat = [
                    exe, '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_list_file,
                    '-c', 'copy',
                    '-movflags', '+faststart',
                    self.current_output_path
                ]
                subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)

                if os.path.exists(concat_list_file):
                    try: os.remove(concat_list_file)
                    except Exception: pass

                for p in muxed_segment_paths:
                    if os.path.exists(p):
                        try: os.remove(p)
                        except Exception: pass

        # تنظيف ملفات المقاطع الخام المؤقتة
        for seg_vid, seg_aud in self.segments:
            if os.path.exists(seg_vid):
                try: os.remove(seg_vid)
                except Exception: pass
            if os.path.exists(seg_aud):
                try: os.remove(seg_aud)
                except Exception: pass

    def _on_final_saved(self, final_path):
        if os.path.exists(final_path):
            size_mb = os.path.getsize(final_path) / (1024 * 1024)
            fmt = "فيديو MP4" if final_path.endswith('.mp4') else "صوت MP3"
            self.info_lbl.config(text=f"تم حفظ {fmt} بنجاح! ({size_mb:.2f} MB)")
            open_in_explorer(final_path, select=True)

    def open_folder(self):
        target_dir = self.output_dir_var.get().strip()
        if os.path.exists(target_dir):
            open_in_explorer(target_dir, select=False)
        else:
            messagebox.showinfo("تنبيه", "المجلد غير موجود حالياً، سيتم إنشاؤه عند بدء التسجيل.")

    def _on_close(self):
        if self.is_recording:
            if messagebox.askyesno("تأكيد الخروج", "التسجيل ما زال مستمراً أو متوقفاً مؤقتاً! هل تريد حفظ الملف والخروج؟"):
                self.stop_recording()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = OmarRecApp(root)
    root.mainloop()
