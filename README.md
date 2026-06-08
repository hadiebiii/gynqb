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
│   └── export_static_site.py   اسکریپت ادغام + پاکسازی + تبدیل داده (JSONL → JSON)
├── gynecology_1403_final.jsonl                      منبع پایه (۶۵۷ سؤال)
├── gyn1403_remaining21_resolutions.jsonl           اصلاح دستی high (اولویت ۱)
├── gyn1403_unresolved_reference_chapter_output.jsonl اصلاح رفرنس/فصل (اولویت ۲)
├── exports/              گزارش‌های debug (در .gitignore، در UI استفاده نمی‌شوند)
├── README.md
└── .gitignore
```

> فایل `gynecology_1403_final.sqlite` خام و هر secret/log در repo نگه‌داری نمی‌شود (در
> `.gitignore` قرار دارد). سایت فقط از `docs/questions.json` و `docs/summary.json`
> استفاده می‌کند که هر دو با مسیر **نسبی** (`./questions.json`) بارگذاری می‌شوند تا روی
> زیرمسیر `/gynqb/` در GitHub Pages هم کار کنند.

---

## ۳. تبدیل داده از JSONL به JSON

اسکریپت `scripts/export_static_site.py` کارهای زیر را انجام می‌دهد:

- **ادغام سه منبع با اولویت**: ابتدا فایل پایه، سپس اصلاح دستی ۲۱تایی (اولویت ۱)،
  سپس اصلاح رفرنس/فصل ۱۹۸تایی (اولویت ۲) **با sanity-check**. اصلاح ۱۹۸تایی فقط وقتی
  اعمال می‌شود که با کلیدواژه‌ی رفرنس داخل متن سؤال، `original_reference` و سطح اطمینان
  تناقض نداشته باشد؛ در غیر این صورت رد می‌شود و سؤال «نیازمند بازبینی علمی» می‌ماند.
- **پاکسازی متن** صورت سؤال، گزینه‌ها و پاسخنامه: حذف `*`، `#### فریم:`، `〔F..〕`،
  `{#...}`، `!!! info/note/warning`، کدبلاک‌ها، HTML comment، `QUALITY_GATE_ISSUES`،
  بلوک «ثبت مفاهیم»، نوفه‌ی pipeline و فاصله‌های تکراری. اصطلاحات پزشکی انگلیسی
  (`NST`, `BPP`, `DCIS`, `IUD`, `hCG`, ...) حفظ می‌شوند.
- **استخراج گزینه‌ها** که اغلب به‌صورت inline داخل `raw_question` با نشانگرهای
  «الف) ب) ج) د)» آمده‌اند و در صورت نبود، استفاده از فیلدهای `option_a..d`.
- **نرمال‌سازی پاسخ** به یکی از حروف `الف/ب/ج/د`. اگر ممکن نبود، `answer` خالی،
  مقدار اصلی در `answer_raw` و `review_needed=true`.
- **ساخت پاسخنامه** با اولویت `answer_excerpt` → `classification_reason` →
  `classification_evidence_quote` → `citation_line` → `reason`/`evidence_quote`.
- **پلنر فصل**: هیچ رکوردی با `chapter` خالی وارد خروجی نمی‌شود؛ در صورت نامشخص بودن،
  `chapter=NEEDS_REVIEW` و `chapter_title=نیازمند بازبینی علمی` می‌شود.
- تولید `docs/summary.json` و گزارش کیفیت در `exports/data_quality_report.json` و
  `exports/needs_review.json` (debug؛ در UI استفاده نمی‌شوند).

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
