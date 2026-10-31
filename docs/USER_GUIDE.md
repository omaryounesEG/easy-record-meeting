# دليل الاستخدام · User Guide

**Easy Record Meeting 2.0.0** — مسجّل الاجتماعات الذكي

---

## العربية

### 1. قبل البدء

| المتطلب | التفاصيل |
|---|---|
| النظام | Windows 10 أو 11 (64-bit) |
| الملفات | `OMAR_REC.exe` + `ffmpeg.exe` في نفس المجلد |
| اختياري | `assets/` (خطوط وأيقونة) — تُقرأ من داخل الـ exe في النسخة المحمولة |

### 2. خطوات التسجيل

1. **نوع التسجيل** — «فيديو + صوت» لتسجيل الشاشة، أو «صوت فقط» لملف MP3 خفيف.
2. **مخرج الصوت** — اختر السماعة التي تسمع منها الاجتماع، واضغط **فحص الإشارة**:
   * «إشارة صوتية ممتازة: 84%» ⇒ جاهز.
   * «لا توجد إشارة (0%)» ⇒ شغّل صوتًا أو اختر جهازًا آخر.
3. **رابط الاجتماع** (اختياري) — الصقه وسيُفتح تلقائيًا عند بدء التسجيل.
4. **مجلد الحفظ** — الافتراضي `D:\DBA_Records`، ويُنشأ تلقائيًا.
5. **بدء التسجيل** — تتحول النافذة إلى الشريط العائم (يمكن تعطيل ذلك من المفتاح).
6. **إيقاف وحفظ** — ثم اختر «قص مقطع» أو «إبقاء الملف كاملًا».

### 3. الإنذار الحرج

| المدة | ما يحدث |
|---|---|
| 10 ثوانٍ صمت | تحذير أصفر: «لا توجد إشارة صوتية منذ 10 ثانية» |
| 30 ثانية صمت | إطار أحمر وامض + نغمة كل ثانيتين + زر «كتم التنبيه» |
| عودة الصوت | «عادت الإشارة الصوتية — التسجيل مستمر» تلقائيًا |

> الإنذار لا يوقف التسجيل — بل ينبّهك قبل أن تكتشف بعد ساعة أن الملف صامت.

### 3.1 إعادة توصيل الصوت تلقائيًا

إذا نامت السماعة (USB/بلوتوث) وتوقّف الصوت فعليًا بينما الصورة تُسجَّل، يعيد البرنامج
فتح منفذ الصوت من نفسه ويظهر: «إعادة توصيل الصوت… التسجيل مستمر». وإذا تعذّر ذلك
(الجهاز فُصل مثلًا) يتوقف التسجيل برسالة واضحة ويُحفظ ما تم تصويره — بدل أن تكمل
بصورة بلا صوت.

**ملاحظة:** إعادة التوصيل تحدث فقط إذا مرّ صوت حقيقي أولًا ثم انقطع **24 ثانية متصلة**،
فالصمت العادي في الاجتماع لا يُشغّل إعادة التوصيل.

### 4. الشريط العائم

`⣿` للسحب · المؤقت · شارة MP4/MP3 · أزرار: كتم (عند الإنذار) · إيقاف مؤقت · حفظ ·
تكبير · إغلاق. يبقى فوق كل النوافذ، ويمكن سحبه إلى أي ركن.

### 5. القص

1. اضغط «قص تسجيل» (أو من نافذة نهاية التسجيل).
2. أدخل وقت البداية والنهاية `HH:MM:SS`.
3. «تشغيل للمعاينة» للمراجعة، ثم «قص وحفظ المقطع».
4. يُحفظ بجانب الأصل باسم يحمل الأوقات، بدون إعادة ترميز.

### 6. المظهر واللغة

* **المظهر**: نهاري / ليلي — بالزر أعلى النافذة أو `Ctrl+T`.
* **اللغة**: العربية / English — بالزر أو `Ctrl+L`؛ ينعكس اتجاه الواجهة بالكامل.

### 7. التحديث من GitHub

اضغط **تحديث**: يفحص آخر إصدار على GitHub. إن وُجد أحدث تظهر نسخته وملاحظاته وزر
لفتح صفحة الإصدارات، وتنزيل النسخة الجديدة يكون يدويًا (البرنامج محمول بلا مثبّت).

### 8. حل المشكلات

| المشكلة | الحل |
|---|---|
| القائمة فارغة | اضغط ⟳ أو تأكد أن مخرج صوت يعمل في النظام |
| إشارة 0% والصوت يعمل | اختر مخرجًا آخر (بلوتوث/شاشة/USB) وأعد الفحص |
| الملف صامت | راقب مؤشر الإشارة أول 10 ثوانٍ من أي اجتماع |
| فيديو لا يبدأ | قد تكون دقة الشاشة تغيّرت أثناء التسجيل؛ أعد التشغيل |
| القص يفشل | تأكد أن البداية < النهاية وأن النهاية ≤ مدة الملف |

---

## English

### 1. Requirements

Windows 10/11 (64-bit). Keep `OMAR_REC.exe` and `ffmpeg.exe` in the same folder.
The `assets/` folder (fonts, icon) is optional for the portable build — it is read
from inside the executable.

### 2. Recording steps

1. **Capture type** — *Video + audio* (screen + meeting sound) or *Audio only* (light MP3).
2. **Audio output** — pick the device you are listening to, then **Test signal**:
   a percentage above 1% means the output works; 0% means silence or the wrong device.
3. **Meeting link** (optional) — opened automatically when recording starts.
4. **Save folder** — defaults to `D:\DBA_Records`, created on demand.
5. **Start recording** — the window collapses to the floating bar (toggleable).
6. **Stop & save** — then choose to trim or keep the full file.

### 3. Silence alarm

10 s of silence → amber warning. 30 s → flashing red border, a beep every two
seconds and a *Mute alarm* button. When audio returns, the banner confirms it.
**The alarm never stops the recording** — it prevents an hour of silence.

### 3.1 Automatic audio reconnect

If a USB/Bluetooth endpoint sleeps and stops delivering sound while the picture keeps
recording, the app reopens the audio stream by itself and shows *“Reconnecting audio…
recording continues”*. If that fails (device unplugged), the recording stops with a
clear message and keeps what was captured — instead of a video with no sound.

The reconnect only triggers after real audio was captured and then **24 continuous
seconds** of digital silence, so ordinary quiet moments do not restart the stream.

### 4. Floating bar

Drag handle · timer · MP4/MP3 badge · mute (during alarm) · pause · save ·
expand · close. Always on top.

### 5. Trimming

Open *Trim recording*, enter start/end as `HH:MM:SS`, preview with the system
player, then cut. The new file is written next to the original with the times in
its name, using stream-copy (no re-encode).

### 6. Theme & language

Day/night via the top-bar control or `Ctrl+T`. Arabic/English via `Ctrl+L`; the
whole layout mirrors for RTL.

### 7. Updating

The **Update** button queries the latest GitHub release, shows its version and
notes, and opens the releases page. Download the new portable build manually.

### 8. Troubleshooting

| Symptom | Fix |
|---|---|
| Device list empty | Press the refresh button; make sure a playback device exists |
| Signal 0% while sound plays | Select another output (Bluetooth/USB/HDMI) and retest |
| File is silent | Watch the level meter for the first 10 seconds |
| Video will not start | Screen resolution may have changed mid-session; restart the app |
| Trim fails | Ensure start < end and end ≤ full length |
