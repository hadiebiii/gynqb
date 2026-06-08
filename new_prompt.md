# new_prompt.md — Task for Claude Code / Web Developer

## نقش و هدف

تو یک توسعه‌دهنده ارشد Frontend + Data Pipeline هستی که باید پروژه static سایت `gynqb` را روی سرور و ریپوزیتوری GitHub اصلاح و نهایی کنی.

هدف نهایی:  
یک سایت HTML/CSS/JavaScript کاملاً static و قابل انتشار روی GitHub Pages برای بانک سؤالات بورد/ارتقا/فلوشیپ زنان و زایمان بساز و اصلاح کن، به‌طوری‌که داده‌ها تمیز، سؤال‌ها و گزینه‌ها خوانا، پاسخنامه‌ها حرفه‌ای و UI مناسب مرور آزمونی باشد.

سایت نهایی باید از این آدرس قابل استفاده باشد:

```text
https://hadiebiii.github.io/gynqb/
```

ریپوزیتوری GitHub:

```text
https://github.com/hadiebiii/gynqb.git
```

---

## مسیرهای احتمالی پروژه روی سرور

ابتدا مسیر واقعی پروژه را پیدا کن. اولویت‌ها:

```bash
/home/ubuntu/gyn/gynqb
/home/hadi/gyn-question-admin
/home/hadi/gyn/gynqb
```

اگر چند مسیر وجود داشت، مسیر دارای فایل‌های زیر را پروژه فعال در نظر بگیر:

```text
docs/index.html
docs/questions.json
docs/summary.json
scripts/export_static_site.py
gynecology_1403_final.jsonl
```

قبل از هر تغییر، وضعیت پروژه را بررسی کن:

```bash
pwd
ls -lah
git status
git remote -v
find . -maxdepth 3 -type f | sort | sed 's#^\./##' | head -200
```

---

## فایل‌های ورودی موجود

در پروژه یا کنار آن این فایل‌ها وجود دارند یا باید کپی شوند:

```text
gynecology_1403_final.jsonl
gyn1403_unresolved_reference_chapter_output(1).jsonl
gyn1403_unresolved_reference_chapter_output.jsonl
gyn1403_remaining21_resolutions.jsonl
gyn1403_server_jsonl_validation_prompt.txt
```

در نسخه سرور ممکن است نام فایل اول یا دوم کمی متفاوت باشد. فایل‌ها را با `ls` و `find` پیدا کن.

---

## وضعیت فعلی داده‌ها

فایل اصلی:

```text
gynecology_1403_final.jsonl
```

دارای ۶۵۷ سؤال است.

تقسیم‌بندی فعلی رفرنس‌ها تقریباً به شکل زیر است:

```json
{
  "Williams Obstetrics": 283,
  "Berek & Novak Gynecology": 139,
  "Speroff CGEI": 122,
  "Te Linde's Operative Gynecology": 84,
  "UpToDate / Guideline": 17,
  "Medical Ethics / Other": 10,
  "Unknown": 2
}
```

وضعیت کیفیت:

```json
{
  "high": 509,
  "medium": 116,
  "low": 32,
  "resolved": 403,
  "review": 254
}
```

فایل ۲۱ سؤال:

```text
gyn1403_remaining21_resolutions.jsonl
```

ساختار منظم‌تری دارد و شامل فیلدهای زیر است:

```text
question_id
stem
option_a
option_b
option_c
option_d
source_book
chapter
chapter_title
confidence
status
evidence_quote
reason
```

این فایل باید به‌عنوان منبع اصلاحی با اولویت بالا استفاده شود.

فایل ۱۹۸ سؤال:

```text
gyn1403_unresolved_reference_chapter_output(1).jsonl
```

یا:

```text
gyn1403_unresolved_reference_chapter_output.jsonl
```

برای اصلاح رفرنس/فصل مفید است، اما نباید کورکورانه اعمال شود؛ چون برخی رکوردها ممکن است استنباطی یا متناقض باشند. نمونه خطرناک: سؤال با متن حاملگی با منشأ نامشخص و پرانتز «اسپیروف» نباید به‌طور کورکورانه به نواک/خوش‌خیم پستان تبدیل شود. بنابراین فایل ۱۹۸تایی فقط وقتی اعمال شود که با متن سؤال، پرانتز رفرنس، original_reference، original_chapter، concept و chapter_title تناقض واضح نداشته باشد.

---

## مشکل فعلی سایت

در صفحه منتشرشده، در صورت باز شدن سایت، پیام زیر دیده می‌شود یا ممکن است دیده شود:

```text
خطا در خواندن داده‌ها
فایل سؤالات پیدا نشد یا قابل خواندن نبود.
```

پس باید حتماً بررسی شود:

```text
docs/questions.json وجود دارد؟
مسیر fetch در docs/index.html درست است؟
اگر سایت در GitHub Pages زیرمسیر /gynqb/ است، مسیرهای نسبی مثل ./questions.json استفاده شده‌اند؟
questions.json از نظر JSON معتبر است؟
summary.json از نظر JSON معتبر است؟
```

تست لازم:

```bash
python3 -m json.tool docs/questions.json > /dev/null
python3 -m json.tool docs/summary.json > /dev/null
python3 -m http.server 8000 --directory docs
```

و سپس:

```text
http://localhost:8000
```

---

## هدف دقیق اصلاحات

باید سه سطح اصلاح انجام شود:

1. اصلاح و بازسازی داده‌ها
2. اصلاح UI/UX سایت
3. آماده‌سازی خروجی نهایی برای commit و push به GitHub Pages

---

# بخش ۱ — اصلاح Data Pipeline

فایل زیر را بازبینی و اصلاح کن:

```text
scripts/export_static_site.py
```

اگر لازم است، آن را کامل بازنویسی کن؛ اما API خروجی را حفظ کن:

```bash
python3 scripts/export_static_site.py
```

این دستور باید خروجی‌های زیر را بسازد:

```text
docs/questions.json
docs/summary.json
```

در صورت نیاز، فایل‌های debug هم می‌تواند بسازد، اما نباید در UI استفاده شود:

```text
exports/needs_review.json
exports/data_quality_report.json
```

---

## ۱.۱ قوانین ادغام داده‌ها

منابع داده با ترتیب اولویت:

### اولویت ۱: فایل ۲۱ سؤال

```text
gyn1403_remaining21_resolutions.jsonl
```

اگر `question_id` این فایل با سؤال اصلی یکی بود، این فیلدها باید روی رکورد اصلی اعمال شوند:

```text
stem
option_a
option_b
option_c
option_d
source_book
chapter
chapter_title
confidence
status
evidence_quote
reason
```

اما فقط در صورتی که مقدارشان خالی نباشد.

### اولویت ۲: فایل ۱۹۸ سؤال

```text
gyn1403_unresolved_reference_chapter_output(1).jsonl
```

یا:

```text
gyn1403_unresolved_reference_chapter_output.jsonl
```

از این فایل برای اصلاح فیلدهای زیر استفاده کن:

```text
reference → source_book_final
chapter → chapter_final
chapter_title → chapter_title_final
confidence
method → classification_reason
```

ولی قبل از اعمال، sanity check انجام بده.

اگر متن سؤال یا original_reference با correction تناقض آشکار دارد، correction را اعمال نکن و رکورد را `review_needed=true` نگه دار.

نمونه قوانین sanity check:

```text
اگر question_short یا raw_question شامل «اسپیروف» است ولی correction می‌گوید Berek & Novak و فصل پستان، اعمال نکن.
اگر chapter_title با concept کاملاً بی‌ربط است، اعمال نکن.
اگر correction confidence پایین است، فقط در debug نگه دار مگر اینکه base خالی باشد.
اگر chapter خارج از پلنر است، اعمال نکن.
```

### اولویت ۳: فایل اصلی

```text
gynecology_1403_final.jsonl
```

فیلدهای پایه از این فایل گرفته شود.

---

## ۱.۲ مپ رفرنس‌ها

در UI این رفرنس‌ها نمایش داده شوند:

```json
{
  "Williams Obstetrics": "ویلیامز",
  "Berek & Novak Gynecology": "نواک",
  "Speroff CGEI": "اسپیروف",
  "Te Linde's Operative Gynecology": "تلیندز",
  "UpToDate / Guideline": "آپتودیت",
  "Medical Ethics / Other": "سایر"
}
```

`Unknown` در UI عمومی نمایش داده نشود، مگر در حالت debug یا اگر سؤال واقعاً داخل دیتابیس باقی مانده باشد؛ در آن صورت زیر «سایر / نیازمند بازبینی» قرار گیرد.

---

## ۱.۳ پلنر فصل‌ها

در خروجی `questions.json` هر رکورد باید این فیلدها را داشته باشد:

```json
{
  "question_id": "Q1403-0001",
  "book_en": "Williams Obstetrics",
  "book_fa": "ویلیامز",
  "chapter": "60",
  "chapter_title": "دیابت",
  "chapter_label": "فصل ۶۰ - دیابت",
  "exam_type": "ارتقا / بورد / فلوشیپ / نامشخص",
  "exam_region": "",
  "year": "۱۴۰۳",
  "question_number": 1,
  "stem": "...",
  "options": {
    "الف": "...",
    "ب": "...",
    "ج": "...",
    "د": "..."
  },
  "answer": "الف",
  "answer_raw": "...",
  "explanation": "...",
  "reference_text": "...",
  "confidence": "high",
  "status": "resolved",
  "review_needed": false,
  "source_question_id": "Q1403-0001"
}
```

هیچ رکوردی با `chapter` خالی وارد `questions.json` نشود. اگر فصل واقعاً مشخص نیست:

```json
{
  "chapter": "NEEDS_REVIEW",
  "chapter_title": "نیازمند بازبینی علمی"
}
```

---

# بخش ۲ — پاکسازی متن سؤال و گزینه‌ها

مشکل فعلی: در بعضی سؤال‌ها علامت `*`، headingهای Markdown، فریم‌ها و متن‌های اضافی داخل سؤال یا گزینه‌ها مانده‌اند.

برای هر سؤال، تابع پاکسازی بنویس:

```text
cleanQuestionText()
cleanOptionText()
cleanExplanationText()
```

## ۲.۱ پاکسازی عمومی متن

موارد زیر حذف یا نرمال شوند:

```text
*
#### فریم:
〔F1〕 تا 〔F12〕
{#...}
!!! info
!!! note
!!! warning
کدبلاک‌های ```json و ```markdown
HTML comments
QUALITY_GATE_ISSUES
## ثبت مفاهیم (برای Dedup)
عبارت‌های OCR زائد مثل «کم گزینه»، «که گزینه»، «call» فقط اگر در پاسخنامه/گزینه معنی را خراب می‌کنند
فاصله‌های تکراری
نیم‌فاصله و کاراکترهای مخفی
```

اما اصطلاحات پزشکی انگلیسی مانند `NST`, `BPP`, `AGC`, `DCIS`, `IUD`, `hCG`, `FSH`, `DHEAS`, `TVH`, `TAH`, `POP`, `PCO` حفظ شوند.

## ۲.۲ جدا کردن گزینه‌ها از raw_question

در خیلی از رکوردها `option_a` خالی است و گزینه «الف» داخل `stem` یا `raw_question` آمده است.

باید الگوریتم استخراج گزینه‌ها داشته باشی:

1. اگر `option_a..option_d` معتبر هستند، همان‌ها را استفاده کن.
2. اگر بعضی گزینه‌ها خالی‌اند، از `raw_question` یا `stem` با الگوهای زیر استخراج کن:

```text
الف)
ب)
ج)
د)

الف )
ب )
ج )
د )

الف-
ب-
ج-
د-

الف)
ب)
ج)
د)
```

3. پس از استخراج گزینه‌ها، متن سؤال باید فقط صورت سؤال باشد و گزینه‌ها از آن حذف شوند.
4. اگر گزینه‌ای هنوز خالی ماند، رکورد را `review_needed=true` کن ولی سؤال را حذف نکن.

## ۲.۳ نرمال‌سازی گزینه صحیح

مقادیر پاسخ در دیتابیس ممکن است این‌ها باشند:

```text
ا
الف
ب
ج
د
A
B
C
D
option_a
option_b
گزینه الف
گزینه ب
```

همه را به یکی از این چهار مقدار تبدیل کن:

```text
الف
ب
ج
د
```

اگر قابل نرمال‌سازی نبود:

```text
answer = ""
answer_raw = مقدار اصلی
review_needed = true
```

---

# بخش ۳ — پاکسازی و حرفه‌ای‌سازی پاسخنامه

مشکل فعلی نمونه:

```text
پاسخنامه
گزینه الف (اسپیروف ۲۰۲۰، فصل ۱۰) معاینه سینه نیازمند توجه دقیق است...
#### فریم: تصاویر پزشکی 〔F11〕 {#medical-images}
!!! info "تصویر ۹.۴: مراحل رشد
```

این نوع متن نباید خام در UI نمایش داده شود.

## ۳.۱ ساخت explanation نهایی

برای هر سؤال explanation را با این اولویت بساز:

```text
answer_excerpt
classification_reason
classification_evidence_quote
citation_line
reason از فایل ۲۱ سؤال
evidence_quote از فایل ۲۱ سؤال
```

سپس خروجی را پاکسازی کن.

## ۳.۲ حذف ساختارهای فنی از پاسخنامه

از explanation حذف کن:

```text
#### فریم: ...
〔F..〕
{#...}
!!! info
!!! note
!!! warning
کدبلاک‌ها
## ثبت مفاهیم
JSON مفاهیم
عبارات مربوط به pipeline یا Gemini/API error
```

اگر explanation بعد از پاکسازی خیلی کوتاه شد، از `citation_line` یا `classification_evidence_quote` کمک بگیر.

اگر هیچ پاسخنامه مفید وجود نداشت:

```text
explanation = "پاسخنامه این سؤال نیازمند بازبینی علمی است."
review_needed = true
```

## ۳.۳ قالب حرفه‌ای پاسخنامه در UI

در `docs/index.html` پاسخنامه را به شکل کارت جدا نمایش بده:

```text
پاسخ صحیح: گزینه [الف/ب/ج/د]

توضیح:
[متن تمیز پاسخنامه]

رفرنس:
[نام کتاب فارسی] - فصل [شماره] - [عنوان فصل]

وضعیت علمی:
[تأییدشده / نیازمند بازبینی علمی]
```

اگر سؤال `review_needed=true` دارد، با badge کوچک نمایش بده:

```text
نیازمند بازبینی علمی
```

---

# بخش ۴ — اصلاح UI سایت

فایل اصلی:

```text
docs/index.html
```

باید اصلاح شود.

## ۴.۱ مشکل بارگذاری داده‌ها

بررسی و اصلاح کن:

```javascript
fetch('./questions.json')
fetch('./summary.json')
```

از مسیرهای absolute مثل `/questions.json` استفاده نکن، چون GitHub Pages زیرمسیر `/gynqb/` دارد.

باید در GitHub Pages کار کند:

```text
https://hadiebiii.github.io/gynqb/
```

## ۴.۲ ساختار UI

صفحه باید شامل این بخش‌ها باشد:

### Header

```text
بانک سؤالات بورد زنان و زایمان
مرور آزمونی بر اساس رفرنس و فصل
```

### انتخاب رفرنس

گزینه‌ها:

```text
ویلیامز
نواک
اسپیروف
تلیندز
آپتودیت
سایر
```

### انتخاب فصل

بعد از انتخاب رفرنس، فصل‌ها نمایش داده شوند:

```text
فصل [شماره] - [عنوان] - [تعداد سؤال]
```

برای UpToDate، به جای «فصل» از «موضوع» استفاده شود:

```text
موضوع: cervical cancer screening - ۳ سؤال
```

### محیط سؤال

بالای کارت سؤال:

```text
نام کتاب: ...
فصل: فصل ... - ...
نوع آزمون: ...
سال: ...
سؤال X از Y
```

کارت سؤال:

```text
شماره سؤال
صورت سؤال
گزینه‌های قابل انتخاب
```

بعد از انتخاب گزینه:

```text
پاسخ صحیح
پاسخنامه
رفرنس
نیازمند بازبینی علمی اگر لازم بود
```

### ناوبری

زیر سؤال:

```text
[قبلی]  برو به سؤال: [input] [برو]  [بعدی]
```

### پیشرفت

در بالا یا کنار صفحه:

```text
پاسخ داده‌شده
درست
غلط
درصد پیشرفت
```

از `localStorage` با کلید زیر استفاده کن:

```text
gynqb-progress-v1
```

## ۴.۳ طراحی ظاهری

ظاهر باید حرفه‌ای‌تر شود:

```text
RTL کامل
فونت Vazirmatn
layout دو ستونه در دسکتاپ: sidebar فیلترها + main question
layout تک‌ستونه در موبایل
کارت‌های تمیز با border-radius
رنگ‌های ملایم
پاسخنامه با باکس جدا
گزینه درست سبز
گزینه غلط قرمز
گزینه انتخاب‌شده آبی
badge کوچک برای review
```

اگر CDN در دسترس بود، Vazirmatn از CDN قابل استفاده است. اگر نه، fallback به system-ui باشد.

---

# بخش ۵ — گزارش کیفیت داده

بعد از اجرای `scripts/export_static_site.py`، یک گزارش کیفیت بساز:

```text
exports/data_quality_report.json
```

شامل:

```json
{
  "total": 657,
  "exported": 657,
  "by_book": {},
  "by_chapter": {},
  "missing_options": [],
  "missing_answer": [],
  "missing_explanation": [],
  "review_needed": [],
  "raw_markdown_artifacts": [],
  "unknown_reference": [],
  "fetch_ready": true
}
```

همچنین یک نسخه خلاصه در ترمینال چاپ کن.

---

# بخش ۶ — تست‌های الزامی

پس از تغییرات، این دستورها را اجرا کن:

```bash
python3 scripts/export_static_site.py

python3 -m json.tool docs/questions.json > /dev/null
python3 -m json.tool docs/summary.json > /dev/null

python3 -m http.server 8000 --directory docs
```

در یک ترمینال دیگر یا با curl:

```bash
curl -I http://localhost:8000/
curl -I http://localhost:8000/questions.json
curl -I http://localhost:8000/summary.json
```

باید `200 OK` برگردد.

همچنین با grep بررسی کن که artifactهای Markdown در questions.json کم یا صفر شده باشند:

```bash
grep -n "#### فریم\|!!! info\|{#\|〔F" docs/questions.json | head
```

اگر خروجی داشت، باید علت را بررسی و پاکسازی را کامل‌تر کنی.

---

# بخش ۷ — فایل‌هایی که باید تغییر کنند

مجاز به تغییر:

```text
scripts/export_static_site.py
docs/index.html
docs/questions.json
docs/summary.json
README.md
new_prompt.md
.gitignore
```

در صورت نیاز، فایل‌های کمکی جدید:

```text
exports/data_quality_report.json
exports/needs_review.json
```

نباید commit شوند مگر لازم باشد.

نباید public شود:

```text
*.sqlite
.env
cookies.txt
API keys
raw logs
```

---

# بخش ۸ — خروجی نهایی و Git

بعد از اصلاح:

```bash
git status
git add scripts/export_static_site.py docs/index.html docs/questions.json docs/summary.json README.md new_prompt.md .gitignore
git commit -m "Clean question data and improve exam UI"
git push origin main
```

سپس GitHub Pages را بررسی کن:

```text
https://hadiebiii.github.io/gynqb/
```

اگر صفحه هنوز خطای خواندن داده‌ها داد، اول `questions.json` و مسیر fetch را بررسی کن.

---

# معیار پذیرش نهایی

کار زمانی پذیرفته می‌شود که:

1. سایت در GitHub Pages بدون خطای `فایل سؤالات پیدا نشد` باز شود.
2. رفرنس‌های ویلیامز، نواک، اسپیروف، تلیندز، آپتودیت و سایر قابل انتخاب باشند.
3. فصل‌ها/موضوعات هر رفرنس با تعداد سؤال درست نمایش داده شوند.
4. سؤال‌ها بدون `*` اضافی، بدون `#### فریم`، بدون `{#...}` و بدون `!!! info` نمایش داده شوند.
5. گزینه‌ها از متن سؤال جدا شده باشند.
6. با انتخاب گزینه، پاسخنامه نمایش داده شود.
7. پاسخنامه‌ها از نظر ظاهری و متنی تمیز باشند و artifactهای pipeline حذف شده باشند.
8. موارد ناقص حذف نشوند، بلکه با badge «نیازمند بازبینی علمی» مشخص شوند.
9. دکمه‌های قبلی، بعدی و برو به سؤال درست کار کنند.
10. پیشرفت کاربر در localStorage ذخیره شود.
11. `docs/questions.json` و `docs/summary.json` JSON معتبر باشند.
12. SQLite و secretها وارد GitHub نشوند.

---

# نکته اجرایی مهم

اگر لازم شد داده‌های اصلاحی ۱۹۸تایی و ۲۱تایی با فایل اصلی merge شوند، این کار را داخل `scripts/export_static_site.py` انجام بده تا هر بار با اجرای یک دستور خروجی نهایی بازسازی شود:

```bash
python3 scripts/export_static_site.py
```

این پروژه backend ندارد؛ بنابراین همه اصلاحات باید در مرحله build انجام شوند و خروجی نهایی static در `docs/` قرار بگیرد.

