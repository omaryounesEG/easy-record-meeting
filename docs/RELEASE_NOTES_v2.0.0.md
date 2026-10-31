# Easy Record Meeting 2.0.0 — مسجّل الاجتماعات الذكي

## العربية

**النسخة المحمولة الكاملة** — لا تحتاج تثبيتًا.

### الجديد في 2.0.0

- **إصلاح العيب المُبلَّغ عنه:** الصوت كان ينقطع أثناء التسجيل ويستمر الفيديو وحده
  (وأيضًا بعد الإيقاف المؤقت). الآن:
  - إذا نام منفذ السماعة (USB/بلوتوث) وأخذ يعطي صمتًا رقميًا، **يُعاد توصيل الصوت تلقائيًا**
    وتظهر رسالة «إعادة توصيل الصوت… التسجيل مستمر».
  - إذا تعذّر التوصيل (الجهاز فُصل)، **يتوقف التسجيل برسالة واضحة** ويُحفظ ما تم تصويره —
    لا مزيد من صورة بلا صوت.
  - الإيقاف المؤقت يوقف الصوت والفيديو معًا ويجمعهما، فلا ينفصل الصوت عن الصورة.
- **واجهة جديدة:** نهاري أولًا + وضع ليلي، خطوط **IBM Plex** مضمّنة، أزرار دائرية ناعمة،
  عربي/إنجليزي مع اتجاه RTL كامل.
- **زر تحديث** يفحص آخر إصدار على GitHub.
- **إنذار انقطاع الصوت:** تنبيه عند 10 ثوانٍ صمت، ووميض + نغمة عند 30 ثانية، مع كتم فوري.
- **67 اختبارًا آليًا** ناجحًا (أخطاء، لغة، تباين، محرّك، واجهة، أداء).

### التشغيل

1. فك ضغط الملف في مجلد.
2. شغّل `OMAR_REC.exe` (ومعه `ffmpeg.exe` في نفس المجلد).
3. اختر مخرج الصوت ← **فحص الإشارة** ← **بدء التسجيل**.

### ملاحظات

- Windows 10/11 64-bit.
- النسخة المحمولة تكتب إعداداتها في `%APPDATA%\EasyRecord`.

---

## English

**Complete portable build** — no installation required.

### What's new in 2.0.0

- **Reported defect fixed:** audio used to stop mid-recording while the picture kept
  going (also after pause). Now:
  - If a USB/Bluetooth endpoint sleeps and starts delivering digital silence, the
    audio stream is **reopened automatically** and the window shows *“Reconnecting
    audio… recording continues”*.
  - If it cannot reconnect (device unplugged), the recording **stops with a clear
    message** and keeps what was captured — no more silent videos.
  - Pause stops audio and video together and re-joins them, so sound never drifts.
- **New UI:** light-first with a full dark theme, bundled **IBM Plex**, rounded soft
  buttons, Arabic/English with real RTL mirroring.
- **Update button** that checks the latest GitHub release.
- **Silence alarm:** warning at 10 s, flashing border + beep at 30 s, one-click mute.
- **67 automated tests** passing (bugs, i18n, contrast, engine, UI, performance).

### Run

1. Unzip into a folder.
2. Start `OMAR_REC.exe` (keep `ffmpeg.exe` beside it).
3. Pick the audio output → **Test signal** → **Start recording**.

### Notes

- Windows 10/11 64-bit.
- Settings live in `%APPDATA%\EasyRecord`.

**SHA-256** of the attached archive is listed in the release body below.

---

**Author:** SAIP Consulting — صائب للاستشارات · omaryounesEG
**Docs:** https://github.com/omaryounesEG/easy-record-meeting#readme
