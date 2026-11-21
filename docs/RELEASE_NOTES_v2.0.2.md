# Easy Record Meeting 2.0.2 — سامع | SAME3

**مسجّل اجتماعات يعمل بدون إنترنت — صوت وصورة وسطح المكتب، بواجهة عربية وإنجليزية.**

## ما الجديد في هذا الإصدار

- **إنذار انقطاع الصوت يعمل دائمًا**: إذا توقّف الصوت أثناء الاجتماع تظهر الرسالة
  «الصوت متوقف — جارٍ إعادة المحاولة» مع وميض أحمر ونغمة تنبيه، بدل أن يستمر التسجيل
  صورةً فقط بصمت.
- **إعادة توصيل أذكى**: نفس المنفذ ← مخرج النظام الافتراضي ← أول منفذ يُرجع صوتًا فعليًا
  (يفيد عند فصل هيدسِت USB أو تغيّر ترقيم الأجهزة).
- **قفل الشاشة لم يعد يُفقد التسجيل**: إذا تعذّر تصوير الشاشة يستمر الصوت ويُحفظ مع إطار
  أسود، ثم يعود الفيديو تلقائيًا عند إمكانية التصوير.
- **سجل تشخيصي** في `%APPDATA%\EasyRecord\recorder.log` (سطر كل 30 ثانية + كل إعادة
  توصيل + ملخص كل جلسة) — يُرسل عند الحاجة إلى دعم.
- **تدوير تلقائي للملفات الكبيرة** عند 3.5 جيجابايت لتجاوز حد WAV (4 جيجا).

## الميزات

| # | الميزة |
|---|---|
| 1 | تسجيل صوت الاجتماع من مخرج الصوت نفسه (Loopback) — تسمع ما يُشغَّل على الجهاز بوضوح رقمي |
| 2 | تسجيل فيديو MP4 لسطح المكتب + الصوت في ملف واحد |
| 3 | وضع الصوت فقط — MP3 صغير الحجم |
| 4 | إيقاف مؤقت واستكمال بدون فقدان تزامن الصوت والصورة |
| 5 | إشعار «لا يوجد صوت» بعد 10 ثوانٍ، ووميض أحمر + نغمة بعد 30 ثانية |
| 6 | شريط تحكم عائم عند تصغير النافذة (بدء/إيقاف/مؤقت) |
| 7 | واجهة عربية وإنجليزية كاملة (RTL/LTR) وخط IBM Plex |
| 8 | وضع نهاري وآخر ليلي |
| 9 | قصّ الملف الصوتي من داخل البرنامج |
| 10 | زر «تحديث» يفحص إصدارات GitHub |
| 11 | نسخة محمولة بملف تنفيذي واحد — لا تثبيت ولا إنترنت |

## الترخيص

**مجاني ومفتوح المصدر — MIT.** استخدمه ووزّعه وعدّله بحرية مع حفظ نص الترخيص.
الخطوط: IBM Plex (SIL OFL 1.1). الفيديو: ffmpeg (LGPL/GPL).

## المتطلبات

Windows 10/11 (64-bit) · لا يحتاج Python ولا اتصالًا بالإنترنت.

## الملفات

```
OMAR_REC.exe     البرنامج (محمول)
ffmpeg.exe       محرّك الفيديو — يبقى بجانب البرنامج
README.md        نظرة عامة
USER_GUIDE.md    دليل الاستخدام
```

## التشغيل

1. فُكّ ضغط الأرشيف في مجلد واحد (مثلًا `H:\EasyRecordMeeting`).
2. شغّل `OMAR_REC.exe`.
3. اختر **فيديو + صوت** أو **صوت فقط**، ثم مخرج الصوت، ثم **فحص الإشارة**.
4. **بدء التسجيل** ← وعند الانتهاء **إيقاف وحفظ**.

---

# Easy Record Meeting 2.0.2 — سامع | SAME3

**An offline meeting recorder — audio, screen video, Arabic and English UI.**

## What's new

- **The silence alarm always fires**: if the audio dies mid-meeting you get
  “Audio is down — retrying” with a red flash and a tone instead of a silent
  picture-only recording.
- **Smarter reconnection**: same endpoint → system default speaker → the first
  endpoint that actually returns sound (covers USB headset unplug / renumbering).
- **A locked screen no longer loses the recording**: audio keeps recording and is
  saved on a black frame; video resumes automatically once capture is possible.
- **Diagnostic log** at `%APPDATA%\EasyRecord\recorder.log` (one line every 30 s,
  every reconnect, and a per-session summary).
- **Automatic rollover at 3.5 GB** to stay under the WAV 4 GB limit.

## Features

1. Records the meeting sound straight from the output device (loopback).
2. MP4 screen video with the audio in one file.
3. Audio-only mode — small MP3.
4. Pause and resume without losing A/V sync.
5. “No sound” notice after 10 s; red flash + tone after 30 s.
6. Floating control bar when the window is minimised.
7. Full Arabic and English UI (RTL/LTR) in IBM Plex.
8. Day and night modes.
9. Trim the audio file inside the app.
10. Update button that checks GitHub releases.
11. Single portable exe — no install, no internet.

## Licence

**Free and open source — MIT.** Use, share and modify freely, keeping the licence
text. Fonts: IBM Plex (SIL OFL 1.1). Video: ffmpeg (LGPL/GPL).

## Requirements

Windows 10/11 (64-bit). No Python, no internet connection required.

## Run

1. Unzip into one folder (e.g. `H:\EasyRecordMeeting`).
2. Start `OMAR_REC.exe`.
3. Pick **Video + audio** or **Audio only**, choose the output device, press **Check signal**.
4. **Start recording** — and **Stop and save** when done.
