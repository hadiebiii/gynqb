#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_static_site.py
=====================
تبدیل فایل منبع `gynecology_1403_final.jsonl` به داده‌ی static قابل مصرف
برای سایت بانک سؤالات بورد زنان و زایمان.

خروجی‌ها:
    docs/questions.json   داده‌ی نرمال‌شده‌ی همه‌ی سؤال‌ها
    docs/summary.json     خلاصه‌ی آماری (تعداد کل، تعداد هر رفرنس، تعداد فصل‌ها، تعداد review)

این اسکریپت هیچ backend ای ندارد؛ فقط یک ابزار build قبل از انتشار است.
"""

import json
import re
import os
from collections import Counter, OrderedDict

# ---------------------------------------------------------------------------
# مسیرها
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "gynecology_1403_final.jsonl")
DOCS = os.path.join(ROOT, "docs")
OUT_QUESTIONS = os.path.join(DOCS, "questions.json")
OUT_SUMMARY = os.path.join(DOCS, "summary.json")

# ---------------------------------------------------------------------------
# مپ رفرنس‌های انگلیسی به فارسی
# ---------------------------------------------------------------------------
BOOK_FA = {
    "Williams Obstetrics": "ویلیامز",
    "Berek & Novak Gynecology": "نواک",
    "Speroff CGEI": "اسپیروف",
    "Te Linde's Operative Gynecology": "تلیندز",
    "UpToDate / Guideline": "آپتودیت",
    "Medical Ethics / Other": "سایر",
    "Unknown": "سایر",
}

# ترتیب نمایش رفرنس‌ها در UI (چهار رفرنس اصلی اول، سپس گروه‌های تکمیلی)
BOOK_ORDER = ["ویلیامز", "نواک", "اسپیروف", "تلیندز", "آپتودیت", "سایر"]
PRIMARY_BOOKS = ["ویلیامز", "نواک", "اسپیروف", "تلیندز"]

# ---------------------------------------------------------------------------
# ابزارهای کمکی
# ---------------------------------------------------------------------------
OPTION_LABELS = ["الف", "ب", "ج", "د"]


def s(value):
    """تبدیل امن به رشته‌ی trim شده."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def first_nonempty(*values):
    for v in values:
        t = s(v)
        if t:
            return t
    return ""


def book_to_fa(book_en):
    book_en = s(book_en)
    return BOOK_FA.get(book_en, "سایر")


# ---------------------------------------------------------------------------
# پارس کردن گزینه‌ها از متن سؤال خام
# گزینه‌ها معمولاً به‌صورت inline داخل raw_question با نشانگرهای
# «الف) ب) ج) د)» آمده‌اند، در حالی که فیلدهای option_a..d ناقص‌اند.
# ---------------------------------------------------------------------------
_MARKER_RE = re.compile(r"(الف|ب|ج|د)\s*[\)\.\-–:]")


def parse_options_from_raw(raw):
    """متن خام را به (stem, options) تجزیه می‌کند.

    فقط نخستین رخداد هر نشانگر به ترتیب الف→ب→ج→د پذیرفته می‌شود تا
    حروف داخل متن به‌اشتباه به‌عنوان گزینه برداشت نشوند.
    """
    raw = s(raw)
    if not raw:
        return "", {}

    matches = list(_MARKER_RE.finditer(raw))
    want = ["الف", "ب", "ج", "د"]
    idx = 0
    picked = []  # (label, marker_start, marker_end)
    for m in matches:
        if idx < len(want) and m.group(1) == want[idx]:
            picked.append((want[idx], m.start(), m.end()))
            idx += 1

    if len(picked) < 2:
        return raw, {}

    stem = raw[: picked[0][1]].strip()
    opts = {}
    for i, (lab, _start, end) in enumerate(picked):
        nxt = picked[i + 1][1] if i + 1 < len(picked) else len(raw)
        opts[lab] = raw[end:nxt].strip()
    return stem, opts


def build_options(rec):
    """گزینه‌ها و متن سؤال را با ترکیب پارس متن خام و فیلدهای ساختاری می‌سازد."""
    raw = first_nonempty(rec.get("raw_question"), rec.get("stem"))
    parsed_stem, parsed_opts = parse_options_from_raw(raw)

    field_opts = {
        "الف": s(rec.get("option_a")),
        "ب": s(rec.get("option_b")),
        "ج": s(rec.get("option_c")),
        "د": s(rec.get("option_d")),
    }

    # ترجیح: گزینه‌ی پارس‌شده، در غیر این صورت فیلد ساختاری
    options = OrderedDict()
    for lab in OPTION_LABELS:
        options[lab] = first_nonempty(parsed_opts.get(lab), field_opts.get(lab))

    have_parsed = len([1 for lab in OPTION_LABELS if parsed_opts.get(lab)]) >= 2
    if have_parsed and parsed_stem:
        stem = parsed_stem
    else:
        # متن سؤال خام شامل گزینه‌ها است؛ stem فیلدِ تمیزتری است
        stem = first_nonempty(rec.get("stem"), parsed_stem, raw)

    return stem, options


# ---------------------------------------------------------------------------
# نرمال‌سازی پاسخ صحیح
# ---------------------------------------------------------------------------
_ANSWER_MAP = {
    "ا": "الف",  # الفِ تک‌حرفی (الف عربی)
    "أ": "الف",
    "آ": "الف",
    "الف": "الف",
    "ب": "ب",
    "ج": "ج",
    "د": "د",
    "a": "الف",
    "b": "ب",
    "c": "ج",
    "d": "د",
    "option_a": "الف",
    "option_b": "ب",
    "option_c": "ج",
    "option_d": "د",
    "1": "الف",
    "2": "ب",
    "3": "ج",
    "4": "د",
}


def normalize_answer(raw_answer):
    """تلاش برای تبدیل پاسخ به یکی از حروف الف/ب/ج/د. در صورت ناموفق رشته‌ی خالی."""
    raw = s(raw_answer)
    if not raw:
        return ""

    low = raw.lower()

    # تطبیق مستقیم
    if low in _ANSWER_MAP:
        return _ANSWER_MAP[low]

    # حذف پیشوند «گزینه»
    cleaned = re.sub(r"^(گزینه|پاسخ|جواب)\s*", "", raw).strip()
    cleaned_low = cleaned.lower()
    if cleaned_low in _ANSWER_MAP:
        return _ANSWER_MAP[cleaned_low]

    # نخستین توکن
    token = re.split(r"[\s\.\)،,:-]+", cleaned)[0].lower() if cleaned else ""
    if token in _ANSWER_MAP:
        return _ANSWER_MAP[token]

    # جست‌وجوی الگوی option_x
    m = re.search(r"option[_\s-]?([abcd])", low)
    if m:
        return _ANSWER_MAP[m.group(1)]

    return ""


# ---------------------------------------------------------------------------
# اطمینان (confidence) و وضعیت (status)
# ---------------------------------------------------------------------------
_CONF_MAP = {
    "high": "high",
    "زیاد": "high",
    "بالا": "high",
    "medium": "medium",
    "متوسط": "medium",
    "low": "low",
    "کم": "low",
    "پایین": "low",
}


def normalize_confidence(raw):
    return _CONF_MAP.get(s(raw).lower(), "unknown")


def normalize_status(rec):
    st = s(rec.get("classification_status")).lower()
    if st in ("resolved", "review"):
        return st
    # fallback از روی review_needed_final
    return "review" if rec.get("review_needed_final") else "resolved"


# ---------------------------------------------------------------------------
# تشخیص نوع آزمون
# ---------------------------------------------------------------------------
def detect_exam_type(rec):
    blob = " ".join(
        s(rec.get(f))
        for f in ("section", "concept", "label", "chunk", "citation_line", "raw_question")
    ).lower()
    if "فلوشیپ" in blob or "fellow" in blob:
        return "فلوشیپ"
    if "ارتقا" in blob or "ارتقاء" in blob or "upgrade" in blob:
        return "ارتقا"
    if "بورد" in blob or "board" in blob:
        return "بورد"
    return "نامشخص"


def detect_region(rec):
    blob = " ".join(s(rec.get(f)) for f in ("section", "concept", "label", "citation_line"))
    if "تهران" in blob or "tehran" in blob.lower():
        return "تهران"
    return ""


# ---------------------------------------------------------------------------
# نرمال‌سازی یک رکورد
# ---------------------------------------------------------------------------
def normalize_record(rec, fallback_index):
    qid = first_nonempty(rec.get("question_id"), rec.get("id"), "Q1403-%04d" % fallback_index)

    book_en = first_nonempty(rec.get("source_book_final"), rec.get("source_book"), "Unknown")
    book_fa = book_to_fa(book_en)

    chapter = first_nonempty(rec.get("chapter_final"), rec.get("chapter"), "—")
    chapter_title = first_nonempty(rec.get("chapter_title_final"), "بدون عنوان")
    chapter_key = "%s::%s::%s" % (book_fa, chapter, chapter_title)

    stem, options = build_options(rec)
    if not stem:
        stem = "متن سؤال در دیتابیس موجود نیست."

    raw_answer = s(rec.get("answer"))
    answer = normalize_answer(raw_answer)

    explanation = first_nonempty(
        rec.get("answer_excerpt"),
        rec.get("classification_reason"),
        rec.get("classification_evidence_quote"),
        rec.get("citation_line"),
        "پاسخنامه‌ای برای این سؤال در دیتابیس ثبت نشده است.",
    )

    citation = first_nonempty(rec.get("citation_line"), rec.get("answer_excerpt"))

    status = normalize_status(rec)
    review_needed = bool(rec.get("review_needed_final")) or status == "review"

    return OrderedDict([
        ("question_id", qid),
        ("book_en", book_en),
        ("book_fa", book_fa),
        ("chapter", chapter),
        ("chapter_title", chapter_title),
        ("chapter_key", chapter_key),
        ("exam_type", detect_exam_type(rec)),
        ("exam_region", detect_region(rec)),
        ("year", "۱۴۰۳"),
        ("stem", stem),
        ("options", options),
        ("answer", answer),
        ("answer_raw", raw_answer),
        ("explanation", explanation),
        ("citation", citation),
        ("confidence", normalize_confidence(rec.get("classification_confidence"))),
        ("status", status),
        ("review_needed", review_needed),
    ])


# ---------------------------------------------------------------------------
# ساخت خلاصه‌ی آماری
# ---------------------------------------------------------------------------
def build_summary(questions):
    by_book = Counter(q["book_fa"] for q in questions)
    review_count = sum(1 for q in questions if q["review_needed"])
    resolved_count = sum(1 for q in questions if q["status"] == "resolved")
    has_answer = sum(1 for q in questions if q["answer"])

    # فصل‌ها به تفکیک رفرنس
    chapters_by_book = OrderedDict()
    chapter_seen = {}
    for q in questions:
        b = q["book_fa"]
        chapters_by_book.setdefault(b, {})
        key = q["chapter_key"]
        if key not in chapters_by_book[b]:
            chapters_by_book[b][key] = OrderedDict([
                ("chapter_key", key),
                ("chapter", q["chapter"]),
                ("chapter_title", q["chapter_title"]),
                ("count", 0),
                ("review_count", 0),
            ])
        chapters_by_book[b][key]["count"] += 1
        if q["review_needed"]:
            chapters_by_book[b][key]["review_count"] += 1
        chapter_seen[key] = True

    # مرتب‌سازی فصل‌ها بر اساس شماره‌ی فصل (عددی در صورت امکان)
    def chap_sort_key(c):
        m = re.search(r"\d+", str(c["chapter"]))
        return (0, int(m.group())) if m else (1, str(c["chapter"]))

    books = []
    for book_fa in BOOK_ORDER:
        if by_book.get(book_fa, 0) == 0:
            continue
        chap_list = sorted(chapters_by_book.get(book_fa, {}).values(), key=chap_sort_key)
        books.append(OrderedDict([
            ("book_fa", book_fa),
            ("count", by_book[book_fa]),
            ("chapter_count", len(chap_list)),
            ("is_primary", book_fa in PRIMARY_BOOKS),
            ("chapters", chap_list),
        ]))

    total_chapters = len(chapter_seen)

    return OrderedDict([
        ("total", len(questions)),
        ("total_books", len([b for b in books])),
        ("total_chapters", total_chapters),
        ("review_count", review_count),
        ("resolved_count", resolved_count),
        ("with_answer", has_answer),
        ("by_book", OrderedDict((b["book_fa"], b["count"]) for b in books)),
        ("primary_books", PRIMARY_BOOKS),
        ("book_order", [b["book_fa"] for b in books]),
        ("books", books),
    ])


# ---------------------------------------------------------------------------
# اجرای اصلی
# ---------------------------------------------------------------------------
def main():
    if not os.path.exists(SRC):
        raise SystemExit("فایل منبع یافت نشد: %s" % SRC)

    os.makedirs(DOCS, exist_ok=True)

    questions = []
    with open(SRC, encoding="utf-8") as fh:
        for i, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                print("هشدار: خط %d نامعتبر بود و رد شد (%s)" % (i, exc))
                continue
            questions.append(normalize_record(rec, i))

    # شماره‌گذاری سراسری و درون‌فصلی برای ناوبری
    chapter_counters = {}
    for n, q in enumerate(questions, start=1):
        q["global_number"] = n
        key = q["chapter_key"]
        chapter_counters[key] = chapter_counters.get(key, 0) + 1
        q["question_number"] = chapter_counters[key]

    summary = build_summary(questions)

    with open(OUT_QUESTIONS, "w", encoding="utf-8") as fh:
        json.dump(questions, fh, ensure_ascii=False, indent=1)

    with open(OUT_SUMMARY, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    # گزارش کوتاه
    print("✓ نوشته شد: %s (%d سؤال)" % (OUT_QUESTIONS, len(questions)))
    print("✓ نوشته شد: %s" % OUT_SUMMARY)
    print("  تعداد کل سؤال‌ها: %d" % summary["total"])
    print("  تعداد فصل‌ها: %d" % summary["total_chapters"])
    print("  نیازمند بازبینی: %d" % summary["review_count"])
    print("  دارای پاسخ ساختاریافته: %d" % summary["with_answer"])
    print("  به تفکیک رفرنس:")
    for book, cnt in summary["by_book"].items():
        print("    - %s: %d" % (book, cnt))


if __name__ == "__main__":
    main()
