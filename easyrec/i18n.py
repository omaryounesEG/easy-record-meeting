# -*- coding: utf-8 -*-
"""Bilingual UI strings (Arabic / English).

Every key must exist in both languages — ``tests/test_i18n.py`` enforces it so a
half-translated build can never ship again.
"""

from __future__ import annotations

from typing import Dict

LANGS = ("ar", "en")
LANG_LABEL = {"ar": "العربية", "en": "English"}
RTL_LANGS = {"ar"}

STRINGS: Dict[str, Dict[str, str]] = {
    # ------------------------------------------------------------------ brand
    "app.title": {
        "ar": "مسجل الاجتماعات الذكي",
        "en": "Smart Meeting Recorder",
    },
    "app.tagline": {
        "ar": "تسجيل صوت وفيديو عالي الجودة مع إنذار انقطاع الصوت",
        "en": "High-quality audio & video capture with a silence alarm",
    },
    "app.version": {"ar": "الإصدار {v}", "en": "Version {v}"},
    "btn.update": {"ar": "تحديث", "en": "Update"},
    "btn.update.tip": {
        "ar": "التحقق من وجود إصدار جديد على GitHub",
        "en": "Check GitHub for a newer release",
    },
    "seg.theme": {"ar": "المظهر", "en": "Theme"},
    "theme.day": {"ar": "نهاري", "en": "Day"},
    "theme.night": {"ar": "ليلي", "en": "Night"},
    "seg.lang": {"ar": "اللغة", "en": "Language"},

    # ---------------------------------------------------------------- setup
    "card.setup": {"ar": "إعداد التسجيل", "en": "Recording setup"},
    "card.setup.hint": {
        "ar": "اختر نوع التسجيل ومخرج الصوت ثم ابدأ",
        "en": "Choose the capture type and audio output, then start",
    },
    "mode.video": {"ar": "فيديو + صوت", "en": "Video + audio"},
    "mode.video.desc": {
        "ar": "تسجيل الشاشة كاملة مع صوت الاجتماع — ملف MP4",
        "en": "Full screen capture with meeting audio — MP4 file",
    },
    "mode.audio": {"ar": "صوت فقط", "en": "Audio only"},
    "mode.audio.desc": {
        "ar": "ملف MP3 خفيف بدون تصوير الشاشة",
        "en": "Lightweight MP3 file, no screen capture",
    },
    "mode.active.video": {
        "ar": "الوضع النشط: فيديو + صوت (MP4)",
        "en": "Active mode: video + audio (MP4)",
    },
    "mode.active.audio": {
        "ar": "الوضع النشط: صوت فقط (MP3)",
        "en": "Active mode: audio only (MP3)",
    },
    "device.label": {"ar": "مخرج الصوت", "en": "Audio output"},
    "device.hint": {
        "ar": "السماعة أو مخرج الاجتماع الذي تسمع منه",
        "en": "The speaker / output you are listening to",
    },
    "device.default": {"ar": "الافتراضي", "en": "default"},
    "device.none": {
        "ar": "لم يتم العثور على أجهزة صوت",
        "en": "No audio devices found",
    },
    "device.loading": {
        "ar": "جارٍ البحث عن أجهزة الصوت…",
        "en": "Looking for audio devices…",
    },
    "btn.test_signal": {"ar": "فحص الإشارة", "en": "Test signal"},
    "btn.refresh_devices": {"ar": "تحديث الأجهزة", "en": "Refresh devices"},
    "tools.vdesk": {"ar": "سطح مكتب افتراضي", "en": "Virtual desktop"},
    "tools.trim": {"ar": "قص تسجيل", "en": "Trim recording"},

    # -------------------------------------------------------------- session
    "card.session": {"ar": "الجلسة والحفظ", "en": "Session & storage"},
    "link.label": {"ar": "رابط الاجتماع (اختياري)", "en": "Meeting link (optional)"},
    "link.placeholder": {
        "ar": "https://… الصق رابط الاجتماع هنا",
        "en": "https://… paste the meeting link here",
    },
    "btn.paste": {"ar": "لصق", "en": "Paste"},
    "opt.auto_open": {"ar": "فتح الرابط عند بدء التسجيل", "en": "Open the link when recording starts"},
    "opt.auto_mini": {"ar": "التصغير إلى شريط عائم", "en": "Minimize to a floating bar"},
    "dir.label": {"ar": "مجلد الحفظ", "en": "Save folder"},
    "btn.browse": {"ar": "تغيير", "en": "Change"},
    "btn.open_folder": {"ar": "فتح المجلد", "en": "Open folder"},

    # -------------------------------------------------------------- monitor
    "card.monitor": {"ar": "الحالة والمؤشر", "en": "Status & level"},
    "status.idle": {"ar": "جاهز للتسجيل", "en": "Ready to record"},
    "status.recording.video": {"ar": "جاري تسجيل الفيديو", "en": "Recording video"},
    "status.recording.audio": {"ar": "جاري تسجيل الصوت", "en": "Recording audio"},
    "status.paused": {"ar": "متوقف مؤقتاً", "en": "Paused"},
    "status.finishing": {"ar": "جاري تجهيز الملف", "en": "Finalizing file"},
    "status.saved": {"ar": "تم حـفظ التسجيل", "en": "Saved"},
    "status.error": {"ar": "توقف بسبب خطأ", "en": "Stopped on error"},
    "monitor.meter": {"ar": "مستوى الإشارة", "en": "Signal level"},
    "monitor.silence": {"ar": "صمت {sec} ث", "en": "silent {sec}s"},
    "monitor.info": {
        "ar": "{size} ميجابايت • {fmt}",
        "en": "{size} MB • {fmt}",
    },
    "notice.audio_reconnect": {
        "ar": "إعادة توصيل الصوت… التسجيل مستمر",
        "en": "Reconnecting audio… recording continues",
    },
    "monitor.idle_hint": {
        "ar": "اضغط «بدء التسجيل» للبدء",
        "en": "Press “Start recording” to begin",
    },
    "alert.warn": {
        "ar": "لا توجد إشارة صوتية منذ {sec} ثانية — تأكد أن الصوت غير مكتوم",
        "en": "No audio signal for {sec}s — check that audio is not muted",
    },
    "alert.critical": {
        "ar": "انقطاع الصوت منذ {sec} ثانية — التسجيل صامت",
        "en": "Audio lost for {sec}s — recording is silent",
    },
    "alert.recovered": {
        "ar": "عادت الإشارة الصوتية — التسجيل مستمر",
        "en": "Audio restored — recording continues",
    },
    "alert.critical.short": {"ar": "انقطاع الصوت!", "en": "Audio lost!"},
    "btn.mute_alarm": {"ar": "كتم التنبيه", "en": "Mute alarm"},
    "alarm.muted": {
        "ar": "تم كتم صوت التنبيه — الصمت ما زال مستمراً",
        "en": "Alarm muted — silence is still ongoing",
    },

    # ------------------------------------------------------------- controls
    "btn.start.video": {"ar": "بدء التسجيل (فيديو)", "en": "Start recording (video)"},
    "btn.start.audio": {"ar": "بدء التسجيل (صوت)", "en": "Start recording (audio)"},
    "btn.pause": {"ar": "إيقاف مؤقت", "en": "Pause"},
    "btn.resume": {"ar": "استئناف", "en": "Resume"},
    "btn.stop": {"ar": "إيقاف وحفظ", "en": "Stop & save"},
    "footer.hint": {
        "ar": "التسجيل يعمل في الخلفية — يمكنك تصغير النافذة بأمان",
        "en": "Recording runs in the background — minimizing is safe",
    },
    "footer.made": {"ar": "صائب للاستشارات", "en": "SAIP Consulting"},

    # --------------------------------------------------------------- dialogs
    "dlg.info": {"ar": "معلومة", "en": "Info"},
    "dlg.warn": {"ar": "تنبيه", "en": "Warning"},
    "dlg.error": {"ar": "خطأ", "en": "Error"},
    "dlg.confirm": {"ar": "تأكيد", "en": "Confirm"},
    "btn.ok": {"ar": "حسناً", "en": "OK"},
    "btn.cancel": {"ar": "إلغاء", "en": "Cancel"},
    "btn.close": {"ar": "إغلاق", "en": "Close"},
    "msg.no_dir": {
        "ar": "يرجى تحديد مجلد حفظ التسجيل أولاً.",
        "en": "Please choose a save folder first.",
    },
    "msg.no_device": {
        "ar": "يرجى اختيار مخرج صوت صالح من القائمة.",
        "en": "Please select a valid audio output from the list.",
    },
    "msg.busy": {
        "ar": "التسجيل قيد التشغيل بالفعل.",
        "en": "Recording is already running.",
    },
    "msg.test_ok": {
        "ar": "إشارة صوتية ممتازة: {pct}%\nالمخرج المختار جاهز للتسجيل.",
        "en": "Audio signal is good: {pct}%\nThe selected output is ready.",
    },
    "msg.test_fail": {
        "ar": "لا توجد إشارة صوتية (0%).\nشغّل صوتاً في الاجتماع أو اختر سماعة أخرى ثم أعد الفحص.",
        "en": "No audio signal (0%).\nPlay sound in the meeting or pick another device and test again.",
    },
    "msg.test_error": {
        "ar": "تعذر فحص الجهاز: {err}",
        "en": "Could not probe the device: {err}",
    },
    "msg.saved.title": {"ar": "تم حفظ التسجيل", "en": "Recording saved"},
    "msg.saved.body": {
        "ar": "تم حفظ الملف:\n{name}\n\nهل تريد قص مقطع منه الآن؟",
        "en": "File saved:\n{name}\n\nTrim a segment now?",
    },
    "msg.exit.title": {"ar": "تأكيد الخروج", "en": "Confirm exit"},
    "msg.exit.body": {
        "ar": "التسجيل ما زال مستمراً. هل تريد حفظ الملف والخروج؟",
        "en": "Recording is still running. Save the file and exit?",
    },
    "msg.start_failed": {
        "ar": "تعذر بدء التسجيل: {err}",
        "en": "Could not start recording: {err}",
    },
    "msg.save_failed": {
        "ar": "تعذر إنهاء الملف: {err}",
        "en": "Could not finalize the file: {err}",
    },
    "msg.folder_missing": {
        "ar": "المجلد غير موجود — سيتم إنشاؤه عند بدء التسجيل.",
        "en": "The folder does not exist yet — it will be created when recording starts.",
    },
    "vdesk.title": {"ar": "سطح المكتب الافتراضي", "en": "Virtual desktop"},
    "vdesk.body": {
        "ar": "1. اضغط «سطح مكتب جديد» في الأعلى.\n"
              "2. اسحب نافذة الاجتماع إلى سطح المكتب الجديد.\n"
              "3. تابع عملك على سطح المكتب الأول دون أن يظهر في الفيديو.\n\n"
              "التنقل بين الأسطح: Ctrl + Win + السهم الأيسر/الأيمن.",
        "en": "1. Click “New desktop” at the top.\n"
              "2. Drag the meeting window onto the new desktop.\n"
              "3. Keep working on the first desktop — it will not appear in the video.\n\n"
              "Switch desktops with Ctrl + Win + Left/Right arrow.",
    },
    "file.choose": {"ar": "اختر ملف فيديو أو صوت", "en": "Choose a video or audio file"},
    "file.media": {"ar": "ملفات الوسائط", "en": "Media files"},
    "file.all": {"ar": "جميع الملفات", "en": "All files"},

    # ------------------------------------------------------------------ trim
    "trim.title": {"ar": "قص مقطع من التسجيل", "en": "Trim a recording"},
    "trim.file": {"ar": "الملف", "en": "File"},
    "trim.duration": {"ar": "المدة الكاملة", "en": "Full length"},
    "trim.play": {"ar": "تشغيل للمعاينة", "en": "Play to preview"},
    "trim.start": {"ar": "وقت البداية", "en": "Start time"},
    "trim.end": {"ar": "وقت النهاية", "en": "End time"},
    "trim.hint": {
        "ar": "الصيغة HH:MM:SS أو MM:SS — القص لا يعيد الترميز فيكون فورياً",
        "en": "Format HH:MM:SS or MM:SS — cuts are stream-copied and instant",
    },
    "trim.keep": {"ar": "إبقاء الملف كاملاً", "en": "Keep full file"},
    "trim.cut": {"ar": "قص وحفظ المقطع", "en": "Cut & save segment"},
    "trim.invalid": {
        "ar": "أوقات غير صحيحة: تأكد أن البداية قبل النهاية وأن الصيغة HH:MM:SS.",
        "en": "Invalid times: the start must be before the end and the format HH:MM:SS.",
    },
    "trim.success": {
        "ar": "تم حفظ المقطع:\n{name}",
        "en": "Segment saved:\n{name}",
    },
    "trim.failed": {
        "ar": "تعذر قص المقطع — تحقق من الأوقات والملف.",
        "en": "Could not cut the segment — check the times and the file.",
    },
    "trim.working": {"ar": "جاري القص…", "en": "Cutting…"},

    # ---------------------------------------------------------------- update
    "update.title": {"ar": "تحديث البرنامج", "en": "Application update"},
    "update.checking": {"ar": "جاري التحقق من الإصدارات…", "en": "Checking for updates…"},
    "update.latest": {
        "ar": "لديك أحدث إصدار ({v}).",
        "en": "You are on the latest version ({v}).",
    },
    "update.available": {
        "ar": "يوجد إصدار جديد {latest} — نسختك {current}.",
        "en": "New version {latest} available — you have {current}.",
    },
    "update.error": {
        "ar": "تعذر الاتصال بـ GitHub: {err}",
        "en": "Could not reach GitHub: {err}",
    },
    "update.open": {"ar": "فتح صفحة الإصدارات", "en": "Open releases page"},

    # ----------------------------------------------------------------- about
    "about.title": {"ar": "عن البرنامج", "en": "About"},
    "btn.about": {"ar": "عن البرنامج", "en": "About"},
    "about.desc.ar": {
        "ar": "«Easy Record Meeting» مسجل ذكي للاجتماعات والمحاضرات والورش:"
              " يسجل صوت الاجتماع من مخرج السماعة مباشرة (Loopback) دون ميكروفون خارجي،"
              " ويسجل الشاشة فيديو عند الحاجة، ويتابع مستوى الإشارة وينبهك بوميض وصوت"
              " إذا انقطع الصوت، ثم يتيح قص المقاطع فوراً.",
        "en": "«Easy Record Meeting» مسجل ذكي للاجتماعات والمحاضرات والورش:"
              " يسجل صوت الاجتماع من مخرج السماعة مباشرة (Loopback) دون ميكروفون خارجي،"
              " ويسجل الشاشة فيديو عند الحاجة، ويتابع مستوى الإشارة وينبهك بوميض وصوت"
              " إذا انقطع الصوت، ثم يتيح قص المقاطع فوراً.",
    },
    "about.desc.en": {
        "ar": "“Easy Record Meeting” records meetings, lectures and workshops: it captures"
              " audio straight from the playback device (loopback) without an external mic,"
              " records the screen to video when needed, watches the signal level and alarms"
              " you with a flashing alert and a beep if the audio drops, then lets you trim"
              " segments instantly.",
        "en": "“Easy Record Meeting” records meetings, lectures and workshops: it captures"
              " audio straight from the playback device (loopback) without an external mic,"
              " records the screen to video when needed, watches the signal level and alarms"
              " you with a flashing alert and a beep if the audio drops, then lets you trim"
              " segments instantly.",
    },
    "about.keywords.ar": {
        "ar": "كلمات مفتاحية: مسجل اجتماعات، تسجيل صوت النظام، تسجيل الشاشة، تسجيل محاضرات،"
              " إنذار انقطاع الصوت، MP3، MP4، تشغيل محمول، عربي/إنجليزي.",
        "en": "كلمات مفتاحية: مسجل اجتماعات، تسجيل صوت النظام، تسجيل الشاشة، تسجيل محاضرات،"
              " إنذار انقطاع الصوت، MP3، MP4، تشغيل محمول، عربي/إنجليزي.",
    },
    "about.keywords.en": {
        "ar": "Keywords: meeting recorder, system audio capture, screen recorder, lecture"
              " recorder, silence alarm, MP3, MP4, portable, Arabic/English.",
        "en": "Keywords: meeting recorder, system audio capture, screen recorder, lecture"
              " recorder, silence alarm, MP3, MP4, portable, Arabic/English.",
    },
    "about.shortcut": {
        "ar": "اختصارات: Ctrl+R بدء/إيقاف • Ctrl+P إيقاف مؤقت • Ctrl+L تغيير اللغة • Ctrl+T تغيير المظهر",
        "en": "Shortcuts: Ctrl+R start/stop • Ctrl+P pause • Ctrl+L language • Ctrl+T theme",
    },
    "minibar.title": {"ar": "شريط التحكم", "en": "Control bar"},
    "minibar.stop": {"ar": "حفظ", "en": "Save"},
    "minibar.pause": {"ar": "إيقاف", "en": "Pause"},
    "minibar.resume": {"ar": "استئناف", "en": "Resume"},
    "minibar.expand": {"ar": "تكبير", "en": "Expand"},
    "minibar.close": {"ar": "إغلاق الشريط", "en": "Close bar"},
}


def tr(lang: str, key: str, **kwargs) -> str:
    """Translate ``key``; unknown keys return the key itself (visible, not silent)."""
    table = STRINGS.get(key)
    text = (table or {}).get(lang) or (table or {}).get("ar") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def missing_keys() -> Dict[str, list]:
    """Keys that are not defined in every language (should always be empty)."""
    out: Dict[str, list] = {}
    for key, table in STRINGS.items():
        absent = [lang for lang in LANGS if not table.get(lang)]
        if absent:
            out[key] = absent
    return out


def is_rtl(lang: str) -> bool:
    return lang in RTL_LANGS
