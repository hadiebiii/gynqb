#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_static_site.py
=====================
ابزار build برای سایت static بانک سؤالات بورد زنان و زایمان (gynqb).

این اسکریپت سه منبع داده را با ترتیب اولویت ادغام می‌کند، متن سؤال/گزینه/پاسخنامه
را پاکسازی می‌کند و خروجی static قابل انتشار روی GitHub Pages تولید می‌کند.

ترتیب اولویت منابع:
    اولویت ۱: gyn1403_remaining21_resolutions.jsonl     (اصلاح دستی، high)
    اولویت ۲: gyn1403_unresolved_reference_chapter_output.jsonl (اصلاح رفرنس/فصل با sanity-check)
    اولویت ۳: gynecology_1403_final.jsonl               (فیلدهای پایه، ۶۵۷ سؤال)

خروجی‌ها:
    docs/questions.json                  داده‌ی نرمال‌شده‌ی همه‌ی سؤال‌ها
    docs/summary.json                    خلاصه‌ی آماری (رفرنس‌ها، فصل‌ها، review)
    exports/data_quality_report.json     گزارش کیفیت داده (debug، در UI استفاده نمی‌شود)
    exports/needs_review.json            فهرست سؤال‌های نیازمند بازبینی (debug)

این پروژه backend ندارد؛ همه‌ی اصلاحات در همین مرحله‌ی build انجام می‌شوند تا با
یک دستور (`python3 scripts/export_static_site.py`) خروجی نهایی بازسازی شود.
"""

import json
import re
import os
from collections import Counter, OrderedDict

# ---------------------------------------------------------------------------
# مسیرها
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT = os.path.dirname(ROOT)
DOCS = os.path.join(ROOT, "docs")
EXPORTS = os.path.join(ROOT, "exports")
OUT_QUESTIONS = os.path.join(DOCS, "questions.json")
OUT_SUMMARY = os.path.join(DOCS, "summary.json")
OUT_QUALITY = os.path.join(EXPORTS, "data_quality_report.json")
OUT_NEEDS_REVIEW = os.path.join(EXPORTS, "needs_review.json")

SRC_MAIN = "gynecology_1403_final.jsonl"
SRC_21 = "gyn1403_remaining21_resolutions.jsonl"
SRC_198_CANDIDATES = [
    "gyn1403_unresolved_reference_chapter_output(1).jsonl",
    "gyn1403_unresolved_reference_chapter_output.jsonl",
]


def find_file(name):
    """فایل را در ریشه‌ی پروژه یا کنار آن (دایرکتوری والد) پیدا می‌کند."""
    for base in (ROOT, PARENT):
        path = os.path.join(base, name)
        if os.path.exists(path):
            return path
    return None


def find_first(names):
    for name in names:
        path = find_file(name)
        if path:
            return path
    return None


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

# کلیدواژه‌های پرانتز رفرنس داخل متن سؤال برای sanity-check اصلاح‌های رفرنس
REF_HINTS = {
    "ویلیامز": "Williams Obstetrics",
    "williams": "Williams Obstetrics",
    "نواک": "Berek & Novak Gynecology",
    "برک": "Berek & Novak Gynecology",
    "novak": "Berek & Novak Gynecology",
    "berek": "Berek & Novak Gynecology",
    "اسپیروف": "Speroff CGEI",
    "speroff": "Speroff CGEI",
    "تلیندز": "Te Linde's Operative Gynecology",
    "تلیند": "Te Linde's Operative Gynecology",
    "te linde": "Te Linde's Operative Gynecology",
    "telinde": "Te Linde's Operative Gynecology",
    "آپتودیت": "UpToDate / Guideline",
    "اپتودیت": "UpToDate / Guideline",
    "uptodate": "UpToDate / Guideline",
}

BOOK_ORDER = ["ویلیامز", "نواک", "اسپیروف", "تلیندز", "آپتودیت", "سایر"]
PRIMARY_BOOKS = ["ویلیامز", "نواک", "اسپیروف", "تلیندز"]

OPTION_LABELS = ["الف", "ب", "ج", "د"]
REVIEW_CHAPTER = "NEEDS_REVIEW"
REVIEW_CHAPTER_TITLE = "نیازمند بازبینی علمی"


# ---------------------------------------------------------------------------
# ابزارهای کمکی پایه
# ---------------------------------------------------------------------------
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
    return BOOK_FA.get(s(book_en), "سایر")


# ---------------------------------------------------------------------------
# توابع پاکسازی متن
# اصطلاحات پزشکی انگلیسی (NST, BPP, AGC, DCIS, IUD, hCG, ...) حفظ می‌شوند چون
# الگوهای حذف فقط ساختارهای markdown/pipeline را هدف می‌گیرند، نه واژگان.
# ---------------------------------------------------------------------------
_RE_CODEBLOCK = re.compile(r"```[a-zA-Z]*.*?```", re.DOTALL)
_RE_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# هر «فریم» تصویری (با یا بدون #/کولن، چه ابتدای خط چه میان متن) تا انتهای خط حذف می‌شود
_RE_FRAME_HEAD = re.compile(r"#{0,6}\s*فریم\s*[:：]?[^\n]*")
# heading های markdown چه در ابتدای خط چه بعد از فاصله (پس از join شدن خطوط)
_RE_HEADING = re.compile(r"(?:(?<=\s)|^)#{1,6}\s+")
# خط جداکننده‌ی افقی markdown (---)
_RE_HRULE = re.compile(r"(?:(?<=\s)|^)-{3,}(?=\s|$)")
_RE_FRAME_TAG = re.compile(r"〔\s*F\d+\s*〕")
_RE_ANCHOR = re.compile(r"\{#[^}]*\}")
_RE_ADMONITION = re.compile(r"!!!\s*\w+(?:\s+\"[^\"]*\"?)?", re.IGNORECASE)
_RE_CONCEPT_BLOCK = re.compile(
    r"#{0,6}\s*ثبت\s+مفاهیم.*?(?:\n\s*\n|$)", re.DOTALL
)
_RE_QUALITY_GATE = re.compile(r"QUALITY_GATE_ISSUES.*", re.IGNORECASE)
_RE_PIPELINE_NOISE = re.compile(
    r".*(?:Gemini|Vertex|API error|pipeline|traceback|Exception).*", re.IGNORECASE
)
_RE_MULTISPACE = re.compile(r"[ \t]{2,}")
_RE_MULTINEWLINE = re.compile(r"\n{3,}")
# کاراکترهای کنترلی/مخفی (zero-width و علامت‌های جهت)؛ نیم‌فاصله (‌) حفظ می‌شود
_RE_HIDDEN = re.compile(r"[​‎‏‪-‮﻿]")


def _strip_common(text):
    """پاکسازی مشترک: حذف ساختارهای markdown/pipeline و نرمال‌سازی فاصله‌ها."""
    if not text:
        return ""
    t = text
    t = _RE_CODEBLOCK.sub(" ", t)
    t = _RE_HTML_COMMENT.sub(" ", t)
    t = _RE_CONCEPT_BLOCK.sub(" ", t)
    t = _RE_FRAME_HEAD.sub(" ", t)
    t = _RE_ADMONITION.sub(" ", t)
    t = _RE_FRAME_TAG.sub(" ", t)
    t = _RE_ANCHOR.sub(" ", t)
    t = _RE_QUALITY_GATE.sub(" ", t)
    t = _RE_HEADING.sub(" ", t)
    t = _RE_HRULE.sub(" ", t)
    t = _RE_HIDDEN.sub("", t)
    # ستاره‌های markdown (bold/bullet) — حذف، اما بدون آسیب به متن
    t = t.replace("**", " ").replace("*", " ")
    # خطوط نوفه‌ی pipeline را خط‌به‌خط حذف کن
    lines = [ln for ln in t.split("\n") if not _RE_PIPELINE_NOISE.match(ln)]
    t = "\n".join(lines)
    t = _RE_MULTISPACE.sub(" ", t)
    t = _RE_MULTINEWLINE.sub("\n\n", t)
    # trim هر خط
    t = "\n".join(ln.strip() for ln in t.split("\n"))
    return t.strip()


def clean_question_text(text):
    """پاکسازی صورت سؤال: تک‌خطی، بدون artifact."""
    t = _strip_common(text)
    t = t.replace("\n", " ")
    t = _RE_MULTISPACE.sub(" ", t)
    return t.strip()


def clean_option_text(text):
    """پاکسازی متن یک گزینه."""
    t = _strip_common(text)
    t = t.replace("\n", " ")
    # حذف نشانگر باقی‌مانده‌ی ابتدای گزینه مثل «الف)» یا «ب-»
    t = re.sub(r"^\s*(?:الف|ب|ج|د)\s*[\)\.\-–:]\s*", "", t)
    t = _RE_MULTISPACE.sub(" ", t)
    return t.strip()


def clean_explanation_text(text):
    """پاکسازی پاسخنامه با حفظ ساختار پاراگراف‌ها."""
    t = _strip_common(text)
    t = _RE_MULTINEWLINE.sub("\n\n", t)
    return t.strip()


# ---------------------------------------------------------------------------
# استخراج گزینه‌ها از متن خام
# ---------------------------------------------------------------------------
_MARKER_RE = re.compile(r"(الف|ب|ج|د)\s*[\)\.\-–:]")


def parse_options_from_raw(raw):
    """متن خام را به (stem, options) تجزیه می‌کند.

    فقط نخستین رخداد هر نشانگر به ترتیب الف→ب→ج→د پذیرفته می‌شود تا حروف
    داخل متن به‌اشتباه گزینه برداشت نشوند.
    """
    raw = s(raw)
    if not raw:
        return "", {}

    want = ["الف", "ب", "ج", "د"]
    idx = 0
    picked = []  # (label, marker_start, marker_end)
    for m in _MARKER_RE.finditer(raw):
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
    """گزینه‌ها و متن سؤال را با ترکیب پارس متن خام و فیلدهای ساختاری می‌سازد.

    خروجی: (stem, options, missing_options) که missing_options فهرست برچسب‌های
    خالی است (برای علامت‌گذاری review_needed).
    """
    raw = first_nonempty(rec.get("raw_question"), rec.get("stem"))
    parsed_stem, parsed_opts = parse_options_from_raw(raw)

    field_opts = {
        "الف": s(rec.get("option_a")),
        "ب": s(rec.get("option_b")),
        "ج": s(rec.get("option_c")),
        "د": s(rec.get("option_d")),
    }

    options = OrderedDict()
    for lab in OPTION_LABELS:
        merged = first_nonempty(field_opts.get(lab), parsed_opts.get(lab))
        options[lab] = clean_option_text(merged)

    have_parsed = len([1 for lab in OPTION_LABELS if parsed_opts.get(lab)]) >= 2
    if have_parsed and parsed_stem:
        stem_src = parsed_stem
    else:
        stem_src = first_nonempty(rec.get("stem"), parsed_stem, raw)

    stem = clean_question_text(stem_src)
    missing = [lab for lab in OPTION_LABELS if not options[lab]]
    return stem, options, missing


# ---------------------------------------------------------------------------
# نرمال‌سازی پاسخ صحیح
# ---------------------------------------------------------------------------
_ANSWER_MAP = {
    "ا": "الف", "أ": "الف", "آ": "الف", "الف": "الف",
    "ب": "ب", "ج": "ج", "د": "د",
    "a": "الف", "b": "ب", "c": "ج", "d": "د",
    "option_a": "الف", "option_b": "ب", "option_c": "ج", "option_d": "د",
    "1": "الف", "2": "ب", "3": "ج", "4": "د",
    "۱": "الف", "۲": "ب", "۳": "ج", "۴": "د",
}


def normalize_answer(raw_answer):
    """تبدیل پاسخ به یکی از حروف الف/ب/ج/د؛ در صورت ناموفق رشته‌ی خالی."""
    raw = s(raw_answer)
    if not raw:
        return ""

    low = raw.lower()
    if low in _ANSWER_MAP:
        return _ANSWER_MAP[low]

    cleaned = re.sub(r"^(گزینه|پاسخ|جواب)\s*", "", raw).strip()
    if cleaned.lower() in _ANSWER_MAP:
        return _ANSWER_MAP[cleaned.lower()]

    token = re.split(r"[\s\.\)،,:-]+", cleaned)[0].lower() if cleaned else ""
    if token in _ANSWER_MAP:
        return _ANSWER_MAP[token]

    m = re.search(r"option[_\s-]?([abcd])", low)
    if m:
        return _ANSWER_MAP[m.group(1)]
    return ""


def recover_answer_from_text(*texts):
    """تلاش برای یافتن «گزینه X» در ابتدای متن پاسخنامه/citation (انکر شده)."""
    pat = re.compile(r"^\s*(?:پاسخ\s*[:：]?\s*)?گزینه\s*(الف|ا|ب|ج|د)\b")
    for t in texts:
        t = s(t)
        m = pat.match(t)
        if m:
            return _ANSWER_MAP.get(m.group(1), "")
    return ""


# ---------------------------------------------------------------------------
# اطمینان (confidence) و وضعیت (status)
# ---------------------------------------------------------------------------
_CONF_MAP = {
    "high": "high", "زیاد": "high", "بالا": "high",
    "medium": "medium", "متوسط": "medium",
    "low": "low", "کم": "low", "پایین": "low",
}


def normalize_confidence(raw):
    return _CONF_MAP.get(s(raw).lower(), "unknown")


# ---------------------------------------------------------------------------
# تشخیص نوع آزمون و منطقه
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
# بارگذاری منابع اصلاحی
# ---------------------------------------------------------------------------
def load_jsonl(path):
    out = []
    if not path:
        return out
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print("  هشدار: خط %d در %s نامعتبر بود (%s)" % (i, os.path.basename(path), exc))
    return out


def detect_ref_hint(*texts):
    """رفرنسِ اشاره‌شده در پرانتز/متن سؤال را برمی‌گرداند (یا None)."""
    blob = " ".join(s(t) for t in texts).lower()
    for key, book in REF_HINTS.items():
        if key in blob:
            return book
    return None


# ---------------------------------------------------------------------------
# ادغام منابع روی رکورد پایه
# ---------------------------------------------------------------------------
def apply_21(base, corr):
    """اولویت ۱: اصلاح دستی high. فیلدهای غیرخالی روی رکورد پایه اعمال می‌شوند."""
    mapping = {
        "stem": "stem",
        "option_a": "option_a",
        "option_b": "option_b",
        "option_c": "option_c",
        "option_d": "option_d",
        "source_book": "source_book_final",
        "chapter": "chapter_final",
        "chapter_title": "chapter_title_final",
        "confidence": "classification_confidence",
        "status": "classification_status",
        "evidence_quote": "classification_evidence_quote",
        "reason": "classification_reason",
    }
    for src_key, dst_key in mapping.items():
        val = s(corr.get(src_key))
        if val:
            base[dst_key] = val
    # رکورد اصلاح‌شده‌ی دستی، حل‌شده تلقی می‌شود
    if s(corr.get("status")).lower() == "resolved":
        base["review_needed_final"] = False
    base["_merge_source"] = "remaining21"


def apply_198(base, corr, debug):
    """اولویت ۲: اصلاح رفرنس/فصل با sanity-check.

    اصلاح فقط زمانی اعمال می‌شود که با متن سؤال، original_reference و سطح
    اطمینان تناقض نداشته باشد. در غیر این صورت رکورد review_needed باقی می‌ماند
    و علت در گزارش debug ثبت می‌شود.
    """
    corr_ref = s(corr.get("reference"))
    corr_book_fa = book_to_fa(corr_ref) if corr_ref in BOOK_FA else None
    conf = normalize_confidence(corr.get("confidence"))
    base_ref = s(base.get("source_book_final"))
    base_unknown = base_ref in ("", "Unknown")

    reason = None

    # ۱) تناقض با کلیدواژه‌ی رفرنس داخل متن سؤال
    hint = detect_ref_hint(corr.get("question_short"), base.get("raw_question"), base.get("stem"))
    if corr_ref and hint and hint != corr_ref:
        reason = "ref_hint_conflict:%s≠%s" % (hint, corr_ref)

    # ۲) تناقض با original_reference (وقتی یک کتاب واقعیِ متفاوت است)
    orig = s(corr.get("original_reference"))
    if reason is None and corr_ref and orig and orig in BOOK_FA and orig != "Unknown" and orig != corr_ref:
        reason = "original_reference_conflict:%s≠%s" % (orig, corr_ref)

    # ۳) اطمینان پایین فقط وقتی base خالی است اعمال شود
    if reason is None and conf == "low" and not base_unknown:
        reason = "low_confidence_kept_in_debug"

    if reason is not None:
        debug.append(OrderedDict([
            ("id", base.get("question_id")),
            ("action", "skipped"),
            ("reason", reason),
            ("base_ref", base_ref),
            ("corr_ref", corr_ref),
        ]))
        # وقتی اصلاح رد شد و base هم نامطمئن است، نیازمند بازبینی نگه‌دار
        if base_unknown:
            base["review_needed_final"] = True
        return

    # اعمال اصلاح
    if corr_ref:
        base["source_book_final"] = corr_ref
    ch = s(corr.get("chapter"))
    if ch:
        base["chapter_final"] = ch
    cht = s(corr.get("chapter_title"))
    if cht:
        base["chapter_title_final"] = cht
    if conf != "unknown":
        base["classification_confidence"] = corr.get("confidence")
    method = s(corr.get("method"))
    if method and not s(base.get("classification_reason")):
        base["classification_reason"] = method
    base["_merge_source"] = "unresolved198"
    debug.append(OrderedDict([
        ("id", base.get("question_id")),
        ("action", "applied"),
        ("corr_ref", corr_ref),
        ("chapter", ch),
    ]))


# ---------------------------------------------------------------------------
# نرمال‌سازی یک رکورد به اسکیمای خروجی
# ---------------------------------------------------------------------------
def normalize_record(rec, fallback_index):
    qid = first_nonempty(rec.get("question_id"), rec.get("id"), "Q1403-%04d" % fallback_index)

    book_en = first_nonempty(rec.get("source_book_final"), rec.get("source_book"), "Unknown")
    book_fa = book_to_fa(book_en)

    stem, options, missing_opts = build_options(rec)
    if not stem:
        stem = "متن سؤال در دیتابیس موجود نیست."

    # ---- پاسخ ----
    raw_answer = s(rec.get("answer"))
    answer = normalize_answer(raw_answer)
    if not answer:
        answer = recover_answer_from_text(
            rec.get("citation_line"), rec.get("answer_excerpt"),
            rec.get("classification_evidence_quote"),
        )

    # ---- پاسخنامه ----
    explanation_src = first_nonempty(
        rec.get("answer_excerpt"),
        rec.get("classification_reason"),
        rec.get("classification_evidence_quote"),
        rec.get("citation_line"),
        rec.get("reason"),
        rec.get("evidence_quote"),
    )
    explanation = clean_explanation_text(explanation_src)
    if len(explanation) < 15:
        # تلاش با منابع جایگزین
        explanation = clean_explanation_text(first_nonempty(
            rec.get("citation_line"),
            rec.get("classification_evidence_quote"),
            rec.get("evidence_quote"),
        ))

    explanation_missing = False
    if len(explanation) < 8:
        explanation = "پاسخنامه این سؤال نیازمند بازبینی علمی است."
        explanation_missing = True

    # ---- وضعیت و نیاز به بازبینی ----
    status = s(rec.get("classification_status")).lower()
    if status not in ("resolved", "review"):
        status = "review" if rec.get("review_needed_final") else "resolved"

    review_needed = bool(rec.get("review_needed_final")) or status == "review"
    if missing_opts:
        review_needed = True
    if not answer:
        review_needed = True
    if explanation_missing:
        review_needed = True

    # ---- فصل (پلنر) ----
    chapter = first_nonempty(rec.get("chapter_final"), rec.get("chapter"))
    chapter_title = first_nonempty(rec.get("chapter_title_final"))
    if not chapter:
        chapter = REVIEW_CHAPTER
        chapter_title = REVIEW_CHAPTER_TITLE
        review_needed = True
    if not chapter_title:
        chapter_title = "بدون عنوان"

    is_topic = book_fa == "آپتودیت"
    if is_topic:
        chapter_label = "موضوع: %s" % chapter_title
    elif chapter == REVIEW_CHAPTER:
        chapter_label = REVIEW_CHAPTER_TITLE
    else:
        chapter_label = "فصل %s - %s" % (chapter, chapter_title)

    chapter_key = "%s::%s::%s" % (book_fa, chapter, chapter_title)

    reference_text = "%s - فصل %s - %s" % (book_fa, chapter, chapter_title)
    if is_topic:
        reference_text = "%s - موضوع: %s" % (book_fa, chapter_title)
    elif chapter == REVIEW_CHAPTER:
        reference_text = "%s - نیازمند بازبینی علمی" % book_fa

    return OrderedDict([
        ("question_id", qid),
        ("book_en", book_en),
        ("book_fa", book_fa),
        ("chapter", chapter),
        ("chapter_title", chapter_title),
        ("chapter_label", chapter_label),
        ("chapter_key", chapter_key),
        ("is_topic", is_topic),
        ("exam_type", detect_exam_type(rec)),
        ("exam_region", detect_region(rec)),
        ("year", "۱۴۰۳"),
        ("stem", stem),
        ("options", options),
        ("answer", answer),
        ("answer_raw", raw_answer),
        ("explanation", explanation),
        ("reference_text", reference_text),
        ("confidence", normalize_confidence(rec.get("classification_confidence"))),
        ("status", status),
        ("review_needed", review_needed),
        ("source_question_id", qid),
        # فیلدهای کمکیِ کیفیت (در UI استفاده نمی‌شوند ولی برای گزارش مفیدند)
        ("_missing_options", missing_opts),
        ("_explanation_missing", explanation_missing),
    ])


# ---------------------------------------------------------------------------
# ساخت خلاصه‌ی آماری
# ---------------------------------------------------------------------------
def build_summary(questions):
    by_book = Counter(q["book_fa"] for q in questions)
    review_count = sum(1 for q in questions if q["review_needed"])
    resolved_count = sum(1 for q in questions if q["status"] == "resolved")
    has_answer = sum(1 for q in questions if q["answer"])

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
                ("chapter_label", q["chapter_label"]),
                ("is_topic", q["is_topic"]),
                ("count", 0),
                ("review_count", 0),
            ])
        chapters_by_book[b][key]["count"] += 1
        if q["review_needed"]:
            chapters_by_book[b][key]["review_count"] += 1
        chapter_seen[key] = True

    def chap_sort_key(c):
        m = re.search(r"\d+", str(c["chapter"]))
        if c["chapter"] == REVIEW_CHAPTER:
            return (2, 0, "")
        return (0, int(m.group()), "") if m else (1, 0, str(c["chapter"]))

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

    return OrderedDict([
        ("total", len(questions)),
        ("total_books", len(books)),
        ("total_chapters", len(chapter_seen)),
        ("review_count", review_count),
        ("resolved_count", resolved_count),
        ("with_answer", has_answer),
        ("by_book", OrderedDict((b["book_fa"], b["count"]) for b in books)),
        ("primary_books", PRIMARY_BOOKS),
        ("book_order", [b["book_fa"] for b in books]),
        ("books", books),
    ])


# ---------------------------------------------------------------------------
# گزارش کیفیت داده
# ---------------------------------------------------------------------------
ARTIFACT_PATS = ["#### فریم", "!!! info", "!!! note", "!!! warning", "{#", "〔F", "```"]


def build_quality_report(questions, total_loaded, merge_stats):
    def has_artifact(q):
        blob = " ".join([q["stem"], q["explanation"]] + list(q["options"].values()))
        return any(p in blob for p in ARTIFACT_PATS)

    by_book = Counter(q["book_fa"] for q in questions)
    by_chapter = Counter(q["chapter_label"] for q in questions)

    return OrderedDict([
        ("total", total_loaded),
        ("exported", len(questions)),
        ("by_book", OrderedDict(sorted(by_book.items()))),
        ("by_chapter", OrderedDict(sorted(by_chapter.items()))),
        ("missing_options", [q["question_id"] for q in questions if q["_missing_options"]]),
        ("missing_answer", [q["question_id"] for q in questions if not q["answer"]]),
        ("missing_explanation", [q["question_id"] for q in questions if q["_explanation_missing"]]),
        ("review_needed", [q["question_id"] for q in questions if q["review_needed"]]),
        ("raw_markdown_artifacts", [q["question_id"] for q in questions if has_artifact(q)]),
        ("unknown_reference", [q["question_id"] for q in questions if q["book_en"] == "Unknown"]),
        ("merge_stats", merge_stats),
        ("fetch_ready", True),
    ])


# ---------------------------------------------------------------------------
# اجرای اصلی
# ---------------------------------------------------------------------------
def main():
    src_main = find_file(SRC_MAIN)
    if not src_main:
        raise SystemExit("فایل منبع اصلی یافت نشد: %s" % SRC_MAIN)

    os.makedirs(DOCS, exist_ok=True)
    os.makedirs(EXPORTS, exist_ok=True)

    # --- بارگذاری پایه ---
    base_records = OrderedDict()
    order = []
    with open(src_main, encoding="utf-8") as fh:
        for i, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                print("هشدار: خط %d در فایل اصلی نامعتبر بود (%s)" % (i, exc))
                continue
            qid = first_nonempty(rec.get("question_id"), rec.get("id"), "Q1403-%04d" % i)
            base_records[qid] = rec
            order.append(qid)

    total_loaded = len(base_records)

    # --- اولویت ۱: فایل ۲۱ سؤال ---
    path21 = find_file(SRC_21)
    rows21 = load_jsonl(path21)
    applied21 = 0
    for corr in rows21:
        qid = s(corr.get("question_id"))
        if qid in base_records:
            apply_21(base_records[qid], corr)
            applied21 += 1
    print("منبع اصلاحی ۲۱: %s (%d رکورد، %d اعمال‌شده)" % (
        os.path.basename(path21) if path21 else "یافت نشد", len(rows21), applied21))

    # --- اولویت ۲: فایل ۱۹۸ سؤال (با sanity-check) ---
    path198 = find_first(SRC_198_CANDIDATES)
    rows198 = load_jsonl(path198)
    debug198 = []
    for corr in rows198:
        qid = s(corr.get("id")) or s(corr.get("question_id"))
        if qid in base_records:
            apply_198(base_records[qid], corr, debug198)
    applied198 = sum(1 for d in debug198 if d["action"] == "applied")
    skipped198 = sum(1 for d in debug198 if d["action"] == "skipped")
    print("منبع اصلاحی ۱۹۸: %s (%d رکورد، %d اعمال‌شده، %d رد‌شده با sanity-check)" % (
        os.path.basename(path198) if path198 else "یافت نشد",
        len(rows198), applied198, skipped198))

    # --- نرمال‌سازی ---
    questions = [normalize_record(base_records[qid], i) for i, qid in enumerate(order, start=1)]

    # --- شماره‌گذاری سراسری و درون‌فصلی ---
    chapter_counters = {}
    for n, q in enumerate(questions, start=1):
        q["global_number"] = n
        key = q["chapter_key"]
        chapter_counters[key] = chapter_counters.get(key, 0) + 1
        q["question_number"] = chapter_counters[key]

    summary = build_summary(questions)

    merge_stats = OrderedDict([
        ("applied_remaining21", applied21),
        ("applied_unresolved198", applied198),
        ("skipped_unresolved198", skipped198),
    ])
    quality = build_quality_report(questions, total_loaded, merge_stats)
    needs_review = [
        OrderedDict([
            ("question_id", q["question_id"]),
            ("book_fa", q["book_fa"]),
            ("chapter_label", q["chapter_label"]),
            ("missing_options", q["_missing_options"]),
            ("missing_answer", not q["answer"]),
            ("missing_explanation", q["_explanation_missing"]),
        ])
        for q in questions if q["review_needed"]
    ]

    # --- حذف فیلدهای کمکی از خروجی عمومی ---
    public_questions = []
    for q in questions:
        pub = OrderedDict((k, v) for k, v in q.items() if not k.startswith("_"))
        public_questions.append(pub)

    with open(OUT_QUESTIONS, "w", encoding="utf-8") as fh:
        json.dump(public_questions, fh, ensure_ascii=False, indent=1)
    with open(OUT_SUMMARY, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    with open(OUT_QUALITY, "w", encoding="utf-8") as fh:
        json.dump(quality, fh, ensure_ascii=False, indent=2)
    with open(OUT_NEEDS_REVIEW, "w", encoding="utf-8") as fh:
        json.dump(needs_review, fh, ensure_ascii=False, indent=2)

    # --- گزارش ترمینال ---
    print("")
    print("✓ نوشته شد: %s (%d سؤال)" % (OUT_QUESTIONS, len(public_questions)))
    print("✓ نوشته شد: %s" % OUT_SUMMARY)
    print("✓ نوشته شد: %s (debug)" % OUT_QUALITY)
    print("✓ نوشته شد: %s (debug)" % OUT_NEEDS_REVIEW)
    print("")
    print("خلاصه‌ی کیفیت:")
    print("  کل سؤال‌ها:            %d" % summary["total"])
    print("  دارای پاسخ ساختاریافته: %d" % summary["with_answer"])
    print("  نیازمند بازبینی:       %d" % summary["review_count"])
    print("  گزینه‌ی ناقص:          %d" % len(quality["missing_options"]))
    print("  پاسخنامه‌ی ناقص:       %d" % len(quality["missing_explanation"]))
    print("  رفرنس نامشخص:         %d" % len(quality["unknown_reference"]))
    print("  artifact باقی‌مانده:   %d" % len(quality["raw_markdown_artifacts"]))
    print("  تعداد فصل‌ها:          %d" % summary["total_chapters"])
    print("  به تفکیک رفرنس:")
    for book, cnt in summary["by_book"].items():
        print("    - %-8s %d" % (book + ":", cnt))


if __name__ == "__main__":
    main()
