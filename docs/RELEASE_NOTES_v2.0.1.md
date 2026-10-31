# Easy Record Meeting 2.0.1 — حرّاس عدم انقطاع الصوت والصورة

## العربية

إصدار تحصيني يدمج حلّ النسخة `NEW` (إعادة محاولة لا نهائية + إعادة تعداد منفذ الصوت
بالاسم) مع حل هذه النسخة (كشف الصمت الرقمي + إيقاف الفيديو عند الفشل).

### ما الجديد

- **حارس الصوت:** إذا توقّفت قراءة الصوت تمامًا (تعليق WASAPI — لا خطأ ولا بيانات)
  لمدة 20 ثانية، يُغلق المقطع الحالي ويبدأ مقطع جديد تلقائيًا. قراءة معلّقة لا يمكن
  مقاطعتها، فبدل أن يضيع بقية الاجتماع يكمل التسجيل من نقطة جديدة.
- **حارس الفيديو:** إذا مات `ffmpeg` أو توقّف عن الكتابة 12 ثانية، يبدأ تصوير جديد فورًا.
- **ملكية المقطع (token):** الخيط القديم لا يستطيع الكتابة في مقطع أُغلق ⇒ لا تلف للملفات.
- **مطابقة أسماء الأجهزة دون رقم النسخة:** «Speakers (2- …)» و«Speakers (3- …)» جهاز واحد،
  فإعادة التوصيل تنجح حتى لو غيّر Windows رقم المنفذ.
- **رسائل واضحة:** «إعادة توصيل الصوت… التسجيل مستمر» · «إعادة تشغيل تصوير الشاشة… التسجيل
  مستمر» · «حُفظ مقطع بدون صوت — الصورة محفوظة».

### التحقق الفعلي على العتاد

| الحالة | النتيجة |
|---|---|
| تسجيل 42.7 ثانية متصلة (فيديو + صوت) | **مقطع واحد**، لا تدخّل من الحرّاس، الصوت −11.7 dB في كل النوافذ |
| تسجيل 22.2 ثانية بإيقاف مؤقت 4 ثوانٍ | مقطعين مدموجين، الصوت متصل بعد الاستئناف (−11.8 dB) |
| تعليق قراءة الصوت (محاكاة) | يُنهى المقطع ويبدأ جديد، الحالة «جاري التسجيل» |
| موت ffmpeg (محاكاة) | تصوير جديد يبدأ، لا فقدان لبقية الاجتماع |
| جهاز يعطي صمتًا رقميًا | إعادة توصيل تلقائي ×3 ثم رسالة واضحة وإيقاف نظيف |

**70 اختبارًا آليًا** ناجحًا (7 منها للصوت والحرّاس).

---

## English

A hardening release that merges the `NEW` build's solution (endless reconnect loop plus
re-enumerating the endpoint by name) with this build's solution (digital-silence
detection and stopping the video on failure).

### What's new

- **Audio watchdog:** a fully wedged read (no exception, no data) for 20 s closes the
  segment and starts a new one — a blocked WASAPI read cannot be interrupted, so the
  recording continues instead of losing the rest of the meeting.
- **Video watchdog:** if `ffmpeg` dies or stops writing for 12 s, capture restarts at once.
- **Segment ownership token:** an abandoned reader can never write into a closed segment.
- **Index-insensitive device matching:** `Speakers (2- …)` and `Speakers (3- …)` are the
  same endpoint, so reconnecting survives the changing Windows instance number.
- **Clear notices:** reconnecting audio · restarting the screen capture · a segment saved
  without sound.

### Verified on real hardware

| Case | Result |
|---|---|
| 42.7 s continuous video + audio | **1 segment**, watchdogs never fired, −11.7 dB in every window |
| 22.2 s with a 4 s pause | two segments joined, audio continuous after resume |
| Wedged audio read (simulated) | segment rolled, still recording |
| Dead ffmpeg (simulated) | capture restarted, nothing lost |
| Endpoint delivering digital silence | automatic reconnect ×3, then a clear message and a clean stop |

**70 automated tests** passing (7 of them for audio and the watchdogs).

**Author:** SAIP Consulting — صائب للاستشارات · omaryounesEG
