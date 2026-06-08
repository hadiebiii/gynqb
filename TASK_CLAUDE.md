تو در محیط Claude Code داخل ریپوزیتوری زیر کار می‌کنی:

```text
/home/ubuntu/gyn/gynqb
```

ریپوزیتوری GitHub:

```text
git@github.com:hadiebiii/gynqb.git
https://github.com/hadiebiii/gynqb
```

وضعیت فعلی repo:

```text
gynqb/
├── README.md
├── gynecology_1403_final.jsonl
└── gynecology_1403_final.sqlite
```

هدف پروژه این است که از فایل داده‌ی موجود، یک سایت static و قابل انتشار روی GitHub Pages بسازی:

```text
docs/index.html
docs/questions.json
docs/summary.json
scripts/export_static_site.py
.gitignore
README.md
```

خروجی اصلی باید یک فایل HTML تعاملی فارسی، RTL، responsive و مناسب موبایل/دسکتاپ برای بانک سؤالات بورد/ارتقا/فلوشیپ زنان و زایمان باشد.

---

# ۱. قوانین کلی اجرای کار

قبل از هر تغییر، این موارد را بررسی کن:

```bash
pwd
ls -la
git status
head -n 3 gynecology_1403_final.jsonl
```

فایل منبع اصلی داده:

```text
/home/ubuntu/gyn/gynqb/gynecology_1403_final.jsonl
```

فایل SQLite خام در نسخه نهایی public نباید در ریشه repo باقی بماند. اگر لازم نیست، آن را از tracking حذف کن و در `.gitignore` قرار بده:

```bash
git rm --cached gynecology_1403_final.sqlite || true
```

سپس در `.gitignore` این موارد را اضافه کن:

```gitignore
*.sqlite
*.sqlite3
*.db
.env
.env.*
*.pem
*.key
__pycache__/
*.pyc
.venv/
venv/
node_modules/
.DS_Store
```

هشدار: فایل JSONL منبع می‌تواند در repo بماند، اما سایت باید از `docs/questions.json` و `docs/summary.json` استفاده کند. هیچ secret، API key، کوکی، token، لاگ خصوصی یا فایل حساس نباید وارد خروجی شود.

---

# ۲. هدف نهایی

یک سایت static بساز که با GitHub Pages از مسیر زیر اجرا شود:

```text
Settings → Pages → Deploy from branch → main / docs
```

لینک نهایی مورد انتظار:

```text
https://hadiebiii.github.io/gynqb/
```

سایت باید بدون backend اجرا شود. استفاده از موارد زیر ممنوع است:

```text
Python server در نسخه نهایی
Flask
Django
Streamlit
SQLite مستقیم در مرورگر
Backend API
Database server
```

اجزای مجاز:

```text
HTML
CSS
JavaScript
JSON
Python فقط برای اسکریپت تبدیل داده قبل از انتشار
```

---

# ۳. ساختار خروجی اجباری

این ساختار را ایجاد کن:

```text
gynqb/
├── docs/
│   ├── index.html
│   ├── questions.json
│   └── summary.json
├── scripts/
│   └── export_static_site.py
├── README.md
└── .gitignore
```

`docs/index.html` باید فایل اصلی UI باشد.

`docs/questions.json` باید داده نرمال‌شده سؤال‌ها باشد.

`docs/summary.json` باید خلاصه آماری شامل تعداد کل، تعداد هر رفرنس، تعداد فصل‌ها و تعداد سؤال‌های review باشد.

---

# ۴. دیتابیس و فیلدهای ورودی

فایل ورودی:

```text
gynecology_1403_final.jsonl
```

تعداد کل سؤالات مورد انتظار:

```text
657
```

فیلدهای احتمالی هر رکورد:

```text
question_id
source_book_final
chapter_final
chapter_title_final
chapter_key_final
stem
raw_question
option_a
option_b
option_c
option_d
answer
answer_excerpt
citation_line
classification_confidence
classification_status
classification_evidence_quote
classification_reason
review_needed_final
label
section
chunk
```

اگر فیلدی خالی بود، از fallback استفاده کن:

```text
متن سؤال:
اولویت ۱: stem
اولویت ۲: raw_question

رفرنس:
source_book_final

شماره فصل:
chapter_final

عنوان فصل:
chapter_title_final

پاسخنامه:
اولویت ۱: answer_excerpt
اولویت ۲: classification_reason
اولویت ۳: classification_evidence_quote
اولویت ۴: citation_line
```

---

# ۵. تبدیل داده به JSON قابل مصرف

در `scripts/export_static_site.py` یک اسکریپت Python بنویس که:

1. فایل `gynecology_1403_final.jsonl` را بخواند.
2. هر خط را به JSON تبدیل کند.
3. رکوردها را normalize کند.
4. خروجی را در `docs/questions.json` بسازد.
5. خلاصه آماری را در `docs/summary.json` بسازد.
6. فیلدهای ناموجود را با مقدار امن و خوانا جایگزین کند.
7. اگر گزینه یا پاسخ خالی بود، UI خراب نشود.

ساختار خروجی هر سؤال در `docs/questions.json` باید این شکل باشد:

```json
{
  "question_id": "Q1403-0001",
  "book_en": "Williams Obstetrics",
  "book_fa": "ویلیامز",
  "chapter": "60",
  "chapter_title": "دیابت",
  "chapter_key": "Williams Obstetrics::60::دیابت",
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
  "citation": "...",
  "confidence": "high / medium / low / unknown",
  "status": "resolved / review",
  "review_needed": false
}
```

---

# ۶. مپ رفرنس‌ها

رفرنس‌های انگلیسی دیتابیس را به فارسی تبدیل کن:

```text
Williams Obstetrics → ویلیامز
Berek & Novak Gynecology → نواک
Speroff CGEI → اسپیروف
Te Linde's Operative Gynecology → تلیندز
UpToDate / Guideline → آپتودیت
Medical Ethics / Other → سایر
Unknown → سایر
```

در UI انتخاب رفرنس این موارد نمایش داده شوند:

```text
ویلیامز
نواک
اسپیروف
تلیندز
آپتودیت
سایر
```

چهار رفرنس اصلی در اولویت و برجسته‌تر باشند:

```text
ویلیامز
نواک
اسپیروف
تلیندز
```

آپتودیت و سایر نیز در UI نمایش داده شوند اما به‌عنوان گروه‌های تکمیلی.

---

# ۷. تشخیص پاسخ صحیح

فیلد `answer` ممکن است به شکل‌های مختلف باشد. در اسکریپت تبدیل داده تلاش کن آن را به یکی از این حروف normalize کنی:

```text
الف
ب
ج
د
```

الگوهای قابل قبول:

```text
A, B, C, D
a, b, c, d
option_a, option_b, option_c, option_d
الف، ب، ج، د
گزینه الف، گزینه ب، گزینه ج، گزینه د
```

اگر پاسخ قابل normalize نبود:

```json
"answer": "",
"answer_raw": "مقدار اصلی answer"
```

در UI اگر `answer` خالی بود بنویس:

```text
پاسخ صحیح در دیتابیس به‌صورت ساختاریافته مشخص نشده است.
```

ولی همچنان پاسخنامه/توضیح را نمایش بده.

---

# ۸. UI اصلی سایت

فایل `docs/index.html` باید یک فایل کامل HTML باشد و خودش CSS و JavaScript لازم را داشته باشد. داده‌ها را با `fetch('./questions.json')` و `fetch('./summary.json')` بخوان.

HTML باید این مشخصات را داشته باشد:

```html
<html lang="fa" dir="rtl">
```

عنوان صفحه:

```text
بانک سؤالات بورد زنان و زایمان
```

زیرعنوان:

```text
مرور آزمونی بر اساس رفرنس و فصل
```

مراحل UI:

1. انتخاب رفرنس
2. انتخاب فصل
3. شروع مرور سؤال‌ها
4. پاسخ‌دهی و مشاهده پاسخنامه

---

# ۹. فونت و ظاهر

در `<head>` از Vazirmatn با Google Fonts استفاده کن:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
```

از Tabler Icons استفاده کن:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/dist/tabler-icons.min.css">
```

CSS باید با Design Tokens نوشته شود:

```css
:root {
  --font-primary: 'Vazirmatn', 'IRANSans', 'Tahoma', 'Arial', sans-serif;

  --c-white: #FFFFFF;
  --c-page: #F0F2F5;

  --c-text: #1A1D23;
  --c-text-2: #4A5060;
  --c-text-3: #8A90A0;

  --c-navy: #1B2A4A;
  --c-navy-mid: #243659;
  --c-blue: #2B5BA8;
  --c-blue-light: #EBF1FB;
  --c-blue-soft: #D5E4F7;

  --c-green: #1A7A4A;
  --c-green-bg: #EBF7F1;
  --c-green-border: #A3DBBE;

  --c-red: #B22222;
  --c-red-bg: #FDEDED;
  --c-red-border: #F0AAAA;

  --c-accent: #C8870A;
  --c-accent-bg: #FFF8EC;
  --c-gold: #B8960A;

  --radius: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-pill: 999px;

  --shadow-sm: 0 1px 3px rgba(27,42,74,0.06), 0 1px 2px rgba(27,42,74,0.04);
  --shadow-card: 0 2px 12px rgba(27,42,74,0.09), 0 1px 3px rgba(27,42,74,0.06);
  --shadow-hover: 0 4px 20px rgba(27,42,74,0.13), 0 2px 6px rgba(27,42,74,0.08);

  --ease-standard: cubic-bezier(0.4, 0, 0.2, 1);
  --dur-fast: 150ms;
  --dur-normal: 220ms;
  --dur-slow: 350ms;
}
```

قواعد تایپوگرافی:

```css
body {
  font-family: var(--font-primary);
  direction: rtl;
  background: var(--c-page);
  color: var(--c-text);
}

.q-body { line-height: 1.85; }
.q-stem { line-height: 1.75; }
.opt-text { line-height: 1.65; }
.explain-text { line-height: 1.82; }
```

اندازه‌های پیشنهادی:

```css
--text-xs: 10px;
--text-sm: 11px;
--text-base: 12px;
--text-md: 13px;
--text-body: 14px;
--text-stem: 14.5px;
--text-h3: 16px;
--text-h2: 18px;
--text-h1: 22px;
```

---

# ۱۰. طراحی صفحه

ظاهر باید:

```text
RTL کامل
فارسی رسمی
تمیز و علمی
responsive
مناسب موبایل و دسکتاپ
بدون شلوغی
بدون backend
قابل اجرا روی GitHub Pages
```

ساختار پیشنهادی:

```text
هدر بالا:
- عنوان سایت
- تعداد کل سؤال‌ها
- تعداد رفرنس‌ها
- تعداد فصل‌ها

بخش انتخاب رفرنس:
- کارت‌های انتخاب رفرنس با تعداد سؤال هر رفرنس

بخش انتخاب فصل:
- بعد از انتخاب رفرنس، فصل‌های همان رفرنس نمایش داده شوند
- قالب فصل:
  فصل [شماره] - [عنوان] - [تعداد سؤال]

محیط سؤال:
- اطلاعات کتاب و فصل
- اطلاعات آزمون
- آمار پیشرفت
- کارت سؤال
- گزینه‌ها
- پاسخنامه بعد از انتخاب گزینه
- دکمه‌های قبلی/بعدی/برو به سؤال
```

---

# ۱۱. اطلاعات بالای محیط سؤال

وقتی کاربر وارد یک فصل شد، بالای صفحه باید نشان بدهد:

```text
نام کتاب: [نام فارسی کتاب]
فصل: فصل [شماره فصل] - [عنوان فصل]
نوع آزمون: [ارتقا / بورد / فلوشیپ / نامشخص]
جزئیات آزمون: [نام قطب] - [سال]
```

اگر نوع آزمون/قطب/سال قابل استخراج نبود:

```text
نوع آزمون: نامشخص
سال: ۱۴۰۳
```

برای استخراج احتمالی از فیلدهای زیر تلاش کن:

```text
label
section
chunk
citation_line
raw_question
question_id
```

---

# ۱۲. قالب نمایش سؤال

هر سؤال باید به شکل زیر باشد:

```text
شماره سؤال: [عدد سؤال]

[صورت سؤال]

گزینه‌ها:
الف) ...
ب) ...
ج) ...
د) ...
```

گزینه‌ها باید کارت‌های قابل انتخاب باشند، نه فقط radio ساده.

رفتار انتخاب گزینه:

1. قبل از انتخاب، پاسخنامه پنهان باشد.
2. پس از انتخاب:

   * گزینه انتخاب‌شده مشخص شود.
   * گزینه صحیح مشخص شود.
   * اگر پاسخ درست بود، پیام مثبت نمایش داده شود.
   * اگر غلط بود، پاسخ صحیح نمایش داده شود.
   * پاسخنامه و رفرنس نمایش داده شود.

ساختار پاسخنامه:

```text
پاسخ صحیح:
گزینه [الف/ب/ج/د]

پاسخنامه:
[explanation]

رفرنس:
[نام کتاب] - فصل [شماره فصل] - [عنوان فصل]
```

اگر سؤال review باشد، برچسب کوچک نمایش داده شود:

```text
نیازمند بازبینی علمی
```

---

# ۱۳. ناوبری سؤال‌ها

زیر هر سؤال این کنترل‌ها وجود داشته باشد:

```text
[سؤال قبلی]    برو به سؤال: [input عددی] [برو]    [سؤال بعدی]
```

و نوشته شود:

```text
سؤال [شماره فعلی] از [تعداد کل سؤال‌های این فصل]
```

رفتار:

```text
قبلی: سؤال قبلی همان فصل
بعدی: سؤال بعدی همان فصل
برو: پرش به شماره سؤال در همان فصل
اگر عدد خارج از محدوده بود، پیام خطا بده
```

---

# ۱۴. پیشرفت کاربر

با `localStorage` ذخیره کن:

```text
تعداد کل سؤالات این فصل
تعداد پاسخ داده‌شده
تعداد درست
تعداد غلط
درصد پیشرفت
پاسخ انتخاب‌شده کاربر برای هر سؤال
```

کلید localStorage باید scoped باشد، مثلاً:

```javascript
gynqb-progress-v1
```

اگر کاربر صفحه را بست و دوباره باز کرد، پاسخ‌ها حفظ شوند.

یک دکمه کوچک برای پاک کردن پیشرفت فصل فعلی اضافه کن:

```text
پاک کردن پیشرفت این فصل
```

قبل از پاک کردن، confirm بگیر.

---

# ۱۵. امکانات تکمیلی لازم

در UI این امکانات را هم اضافه کن:

1. دکمه بازگشت به انتخاب فصل
2. دکمه بازگشت به انتخاب رفرنس
3. جستجوی ساده در فصل‌ها بر اساس عنوان فصل
4. نمایش تعداد سؤال هر رفرنس
5. نمایش تعداد سؤال هر فصل
6. نمایش تعداد سؤال‌های نیازمند بازبینی
7. حالت خطای خواندن JSON با پیام فارسی
8. loading state هنگام fetch داده‌ها
9. graceful fallback اگر `questions.json` پیدا نشد

---

# ۱۶. کیفیت کدنویسی JavaScript

کد JS را خوانا و ماژولار داخل همان `index.html` بنویس.

توابع پیشنهادی:

```javascript
loadData()
normalizeText()
renderBookCards()
renderChapterList()
selectBook(bookEn)
selectChapter(chapterKey)
renderQuestion()
handleAnswer(choice)
renderProgress()
saveProgress()
loadProgress()
goNext()
goPrev()
jumpToQuestion()
resetChapterProgress()
```

از event delegation استفاده کن تا کد سبک بماند.

هیچ library سنگینی مثل React/Vue/Tailwind اضافه نکن. فقط HTML/CSS/Vanilla JS.

---

# ۱۷. انیمیشن‌ها

انیمیشن‌ها سبک باشند:

```css
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes opt-correct {
  0% { transform: scale(0.98); }
  60% { transform: scale(1.015); }
  100% { transform: scale(1); }
}

@keyframes opt-shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}
```

برای موبایل سنگین نباشد.

---

# ۱۸. README

فایل `README.md` را به‌روزرسانی کن و توضیح بده:

1. پروژه چیست.
2. فایل‌های اصلی کدام‌اند.
3. چطور داده از JSONL به JSON تبدیل می‌شود.
4. چطور local test انجام شود.
5. چطور GitHub Pages فعال شود.

دستور local test:

```bash
python3 scripts/export_static_site.py
python3 -m http.server 8000 --directory docs
```

سپس:

```text
http://localhost:8000
```

---

# ۱۹. اجرای اسکریپت و تست

بعد از ساخت اسکریپت:

```bash
python3 scripts/export_static_site.py
```

بعد بررسی کن:

```bash
ls -lah docs
python3 -m json.tool docs/questions.json > /dev/null
python3 -m json.tool docs/summary.json > /dev/null
```

اگر خطا نبود، یک تست ساده با Python انجام بده که تعداد سؤال‌ها را گزارش کند:

```bash
python3 - <<'PY'
import json
from collections import Counter
qs=json.load(open("docs/questions.json", encoding="utf-8"))
print("questions:", len(qs))
print(Counter(q["book_fa"] for q in qs))
PY
```

---

# ۲۰. معیار پذیرش نهایی

کار زمانی کامل است که:

1. `docs/index.html` ساخته شده باشد.
2. `docs/questions.json` ساخته شده باشد.
3. `docs/summary.json` ساخته شده باشد.
4. سایت بدون backend اجرا شود.
5. UI کاملاً فارسی و RTL باشد.
6. Vazirmatn و Tabler Icons در HTML استفاده شده باشند.
7. رفرنس‌ها قابل انتخاب باشند:

   * ویلیامز
   * نواک
   * اسپیروف
   * تلیندز
   * آپتودیت
   * سایر
8. فصل‌های هر رفرنس از روی دیتابیس ساخته شوند.
9. با انتخاب فصل، سؤال‌های همان فصل نمایش داده شوند.
10. گزینه‌ها قابل انتخاب باشند.
11. پاسخنامه فقط بعد از انتخاب گزینه نمایش داده شود.
12. دکمه‌های قبلی، بعدی و برو به سؤال کار کنند.
13. پیشرفت کاربر در localStorage ذخیره شود.
14. سؤال‌های review حذف نشوند و برچسب «نیازمند بازبینی علمی» داشته باشند.
15. فایل SQLite خام در خروجی public نهایی track نشود.
16. `git status` در پایان واضح باشد و فایل‌های ساخته‌شده قابل commit باشند.

---

# ۲۱. خروجی نهایی که باید گزارش کنی

در پایان کار، گزارش بده:

```text
فایل‌های ساخته‌شده:
- docs/index.html
- docs/questions.json
- docs/summary.json
- scripts/export_static_site.py
- README.md
- .gitignore

تعداد سؤال‌های export شده:
[...]

تعداد سؤال بر اساس رفرنس:
[...]

دستورهای پیشنهادی commit:
git status
git add docs scripts README.md .gitignore
git commit -m "Build interactive gynecology question bank site"
git push
```

لطفاً خودت بدون نیاز به سؤال اضافه، بهترین پیاده‌سازی static و قابل انتشار روی GitHub Pages را انجام بده.

