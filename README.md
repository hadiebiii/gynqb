# بانک سؤالات بورد زنان و زایمان (gynqb)

یک سایت **static** و بدون backend برای مرور آزمونی سؤالات بورد، ارتقا و فلوشیپ زنان و
زایمان بر اساس **رفرنس** و **فصل**. کل سایت با HTML/CSS/JavaScript خالص اجرا می‌شود و
روی **GitHub Pages** قابل انتشار است.

🔗 نسخه‌ی منتشرشده: <https://hadiebiii.github.io/gynqb/>

---

## ۱. پروژه چیست

از یک پایگاه‌دادهٔ سؤالات (`gynecology_1403_final.jsonl`) یک سایت تعاملی فارسی و RTL
ساخته می‌شود که در آن کاربر:

1. یک رفرنس (ویلیامز، نواک، اسپیروف، تلیندز، آپتودیت، سایر) را انتخاب می‌کند،
2. فصل موردنظر را انتخاب می‌کند،
3. سؤال‌های همان فصل را مرور و پاسخ می‌دهد،
4. بعد از انتخاب گزینه، پاسخنامه و رفرنس را می‌بیند،
5. پیشرفتش در مرورگر (`localStorage`) ذخیره می‌شود.

سؤال‌های نیازمند بازبینی علمی حذف نمی‌شوند و با برچسب «نیازمند بازبینی علمی» نمایش
داده می‌شوند.

---

## ۲. فایل‌های اصلی

```text
gynqb/
├── docs/
│   ├── index.html        رابط کاربری کامل (HTML + CSS + JS، بدون فریم‌ورک)
│   ├── questions.json     داده‌ی نرمال‌شده‌ی سؤال‌ها (خروجی build)
│   └── summary.json       خلاصه‌ی آماری: تعداد کل، هر رفرنس، فصل‌ها و review
├── scripts/
│   └── export_static_site.py   اسکریپت تبدیل داده (JSONL → JSON)
├── gynecology_1403_final.jsonl منبع اصلی داده
├── README.md
└── .gitignore
```

> فایل `gynecology_1403_final.sqlite` خام در repo نگه‌داری نمی‌شود (در `.gitignore` قرار
> دارد). سایت فقط از `docs/questions.json` و `docs/summary.json` استفاده می‌کند.

---

## ۳. تبدیل داده از JSONL به JSON

اسکریپت `scripts/export_static_site.py` کارهای زیر را انجام می‌دهد:

- هر خط `gynecology_1403_final.jsonl` را به یک رکورد JSON تبدیل می‌کند.
- رفرنس انگلیسی را به فارسی مپ می‌کند (مثلاً `Williams Obstetrics → ویلیامز`).
- گزینه‌ها را که اغلب به‌صورت inline داخل `raw_question` آمده‌اند جدا می‌کند و در
  صورت نبود، از فیلدهای `option_a..d` استفاده می‌کند.
- پاسخ صحیح را به یکی از حروف `الف/ب/ج/د` نرمال می‌کند (`ا`→`الف`, `A–D`, «گزینه …»,
  `option_x`). اگر قابل نرمال‌سازی نبود، `answer` خالی و مقدار اصلی در `answer_raw`
  نگه‌داری می‌شود.
- پاسخنامه را با اولویت `answer_excerpt` → `classification_reason` →
  `classification_evidence_quote` → `citation_line` می‌سازد.
- خلاصهٔ آماری را در `docs/summary.json` تولید می‌کند.

برای ساخت دوبارهٔ خروجی‌ها:

```bash
python3 scripts/export_static_site.py
```

---

## ۴. تست محلی (Local test)

```bash
python3 scripts/export_static_site.py
python3 -m http.server 8000 --directory docs
```

سپس در مرورگر باز کنید:

```text
http://localhost:8000
```

برای اطمینان از سالم بودن خروجی JSON:

```bash
python3 -m json.tool docs/questions.json > /dev/null
python3 -m json.tool docs/summary.json  > /dev/null
```

---

## ۵. فعال‌سازی GitHub Pages

1. تغییرات را commit و push کنید (شاخهٔ `main`).
2. در مخزن گیت‌هاب به مسیر زیر بروید:

   ```text
   Settings → Pages → Build and deployment → Deploy from a branch
   Branch: main      Folder: /docs
   ```
3. پس از چند دقیقه، سایت روی آدرس زیر در دسترس خواهد بود:

   ```text
   https://hadiebiii.github.io/gynqb/
   ```

---

## ۶. نکات فنی

- بدون backend، بدون دیتابیس سمت سرور، بدون فریم‌ورک سنگین (فقط Vanilla JS).
- فونت **Vazirmatn** و آیکون‌های **Tabler Icons** از CDN بارگذاری می‌شوند.
- کلید ذخیرهٔ پیشرفت در `localStorage`: `gynqb-progress-v1`.
- کاملاً RTL و responsive (موبایل و دسکتاپ).
