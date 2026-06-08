#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_static_site.py
=====================
ابزار build برای سایت static بانک سؤالات بورد زنان و زایمان (gynqb).

این اسکریپت سه منبع داده را با ترتیب اولویت ادغام می‌کند، متن سؤال/گزینه/پاسخنامه
را پاکسازی می‌کند، طبقه‌بندی رفرنس/فصل را اصلاح می‌کند و خروجی static قابل انتشار
روی GitHub Pages تولید می‌کند.

ترتیب اولویت منابع:
    اولویت ۱: gyn1403_remaining21_resolutions.jsonl            (اصلاح دستی، high)
    اولویت ۲: gyn1403_unresolved_reference_chapter_output.jsonl (اصلاح رفرنس/فصل با sanity-check)
    اولویت ۳: gynecology_1403_final.jsonl                       (فیلدهای پایه، ۶۵۷ سؤال)

به‌علاوه چند override سخت (HARD_OVERRIDES) برای سؤال‌هایی که طبقه‌بندی/پاسخ آن‌ها
به‌صورت دستی تأیید شده است، پیش از نوشتن خروجی اعمال می‌شوند.

خروجی‌ها:
    docs/questions.json     داده‌ی نرمال‌شده‌ی عمومیِ همه‌ی سؤال‌ها (بدون فیلدهای داخلی)
    docs/summary.json       خلاصه‌ی رفرنس‌ها و فصل‌ها برای ساخت dropdown ها
    exports/data_quality_report.json   گزارش کیفیت داده (debug، در UI استفاده نمی‌شود)
    exports/needs_review.json          فهرست سؤال‌های ناقص (debug، در UI استفاده نمی‌شود)

نکته‌ی مهم: هیچ برچسب «بازبینی/اطمینان/وضعیت» و هیچ شمارنده‌ی عمومی در خروجیِ
عمومی (questions.json / summary.json) و UI نمایش داده نمی‌شود.
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

# مارکر داخلیِ «بدون فصل»؛ هرگز به‌صورت متن عمومی نمایش داده نمی‌شود.
REVIEW_CHAPTER = "NEEDS_REVIEW"
# برچسب خنثیِ عمومی برای سؤالی که فصل عددی ندارد ولی موضوع آن قابل استنباط نیست.
NEUTRAL_TOPIC = "سایر موضوعات"

# کلیدواژه‌هایی که نشان می‌دهند classification_topic یک slug پایپ‌لاین است نه موضوع واقعی.
JUNK_TOPIC_KEYS = (
    "frame", "test-master", "tehran-board", "exam-questions",
    "master-frame", "procedure-frame", "board-exam",
)

_RE_PERSIAN = re.compile(r"[؀-ۿ]")


# ---------------------------------------------------------------------------
# override های سختِ تأییدشده (پیش از نوشتن questions.json اعمال می‌شوند)
# ---------------------------------------------------------------------------
HARD_OVERRIDES = {
    "Q1403-0249": {
        "book_en": "UpToDate / Guideline",
        "book_fa": "آپتودیت",
        "chapter": "cervical cytology",
        "chapter_title": "Clinical management of unsatisfactory cervical cytology",
        "chapter_label": "موضوع: cervical cytology",
        "is_topic": True,
        "answer": "ب",
        "options": OrderedDict([
            ("الف", "تکرار پاپ اسمیر سال بعد"),
            ("ب", "انجام پاپ اسمیر دو ماه بعد"),
            ("ج", "نیاز به اقدامی نیست"),
            ("د", "انجام پاپ اسمیر ۶ ماه بعد"),
        ]),
        "explanation": (
            "در سیتولوژی نامطلوب یا unsatisfactory، نمونه برای تفسیر قابل اعتماد کافی "
            "نیست و باید در فاصله کوتاه تکرار شود. در این سؤال، نتیجه HPV نیز نامشخص "
            "گزارش شده است؛ بنابراین اقدام مناسب، تکرار پاپ اسمیر در فاصله کوتاه، یعنی "
            "حدود دو ماه بعد است. تکرار سال بعد باعث تأخیر نامناسب در ارزیابی می‌شود، عدم "
            "اقدام صحیح نیست، و فاصله شش‌ماهه نیز نسبت به توصیه پاسخنامه طولانی‌تر است."
        ),
        "reference_text": "آپتودیت - cervical cytology - Clinical management of unsatisfactory cervical cytology",
    },
    "Q1403-0173": {
        "book_en": "Berek & Novak Gynecology",
        "book_fa": "نواک",
        "chapter": "5",
        "chapter_title": "آناتومی و جنین‌شناسی",
        "chapter_label": "فصل ۵ - آناتومی و جنین‌شناسی",
        "is_topic": False,
        "answer": "ج",
        "options": OrderedDict([
            ("الف", "عضله پرینه‌ای عرضی عمقی"),
            ("ب", "عضله پووبوکسیژئوس"),
            ("ج", "عضله پووبورکتالیس"),
            ("د", "عضله ایلیوکوسیژئوس"),
        ]),
        "explanation": (
            "پاسخ صحیح عضله پووبورکتالیس است. این عضله بخشی از مجموعه عضلات کف لگن است و "
            "با تشکیل قلاب رکتال در پشت رکتوم، زاویه آنورکتال را حفظ می‌کند. حفظ این زاویه "
            "یکی از مکانیسم‌های مهم continence مدفوعی است. بنابراین حتی اگر بخش قدامی "
            "اسفنکتر آنال خارجی آسیب دیده یا وجود نداشته باشد، سالم بودن و عملکرد مناسب "
            "عضله پووبورکتالیس می‌تواند از بی‌اختیاری مدفوع جلوگیری کند. اسفنکتر داخلی مقعد "
            "تون مداوم دارد، اما کنترل ارادی و حفظ زاویه آنورکتال عمدتاً با همکاری "
            "پووبورکتالیس و اسفنکترها انجام می‌شود."
        ),
        "reference_text": "نواک - فصل ۵ - آناتومی و جنین‌شناسی",
    },
}


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


def has_persian(text):
    return bool(_RE_PERSIAN.search(s(text)))


def usable_topic(text):
    """آیا classification_topic یک موضوع واقعیِ قابل‌نمایش است؟ (موضوع فارسی، نه slug)."""
    t = s(text)
    if len(t) < 3:
        return ""
    low = t.lower()
    if any(k in low for k in JUNK_TOPIC_KEYS):
        return ""
    if not has_persian(t):
        return ""
    return t


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
_RE_QUALITY_GATE = re.compile(r"QUALITY_GATE_ISSUES.*", re.IGNORECASE | re.DOTALL)
_RE_PIPELINE_NOISE = re.compile(
    r".*(?:Gemini|Vertex|API error|pipeline|traceback|Exception).*", re.IGNORECASE
)
_RE_MULTISPACE = re.compile(r"[ \t]{2,}")
_RE_MULTINEWLINE = re.compile(r"\n{3,}")
# کاراکترهای کنترلی/مخفی (zero-width و علامت‌های جهت)؛ نیم‌فاصله (‌) حفظ می‌شود
_RE_HIDDEN = re.compile(r"[​‎‏‪-‮﻿]")

# نقطه‌ای که از آن‌جا به بعد، محتوای پاسخنامه به بخش/فریم سؤال دیگری نشت کرده است.
_RE_EXPLANATION_CUT = re.compile(r"(####|〔\s*F|\{#|##\s|QUALITY_GATE|!!!\s)")


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
    t = re.sub(r"^\s*[\-–•]\s*", "", t)
    t = re.sub(r"^\s*(?:الف|ب|ج|د)\s*[\)\.\-–:]\s*", "", t)
    t = _RE_MULTISPACE.sub(" ", t)
    # حذف خط تیره‌ی انتهاییِ بی‌معنی
    t = t.rstrip(" -–•").strip()
    return t.strip()


def clean_explanation_text(text):
    """پاکسازی پاسخنامه با حفظ ساختار پاراگراف‌ها.

    اگر محتوای بخش/فریمِ سؤال دیگری به انتهای پاسخنامه نشت کرده باشد، از همان نقطه
    بریده می‌شود تا متنِ نامرتبط نمایش داده نشود.
    """
    raw = s(text)
    if not raw:
        return ""
    # قطع محتوای نشت‌کرده‌ی بخش/فریم بعدی
    cut = _RE_EXPLANATION_CUT.search(raw)
    if cut and cut.start() > 30:
        raw = raw[: cut.start()]
    t = _strip_common(raw)
    t = _RE_MULTINEWLINE.sub("\n\n", t)
    # حذف خط تیره‌های ابتدای bullet در هر خط
    t = "\n".join(re.sub(r"^\s*[\-–•]\s*", "", ln) for ln in t.split("\n"))
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
    خالی است (برای علامت‌گذاری داخلیِ کیفیت).
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


# الگوهای پر‌اطمینانِ اعلام پاسخ در متن پاسخنامه/citation/excerpt.
# فقط اعلام‌های صریح پذیرفته می‌شوند تا حروفِ داخل توضیح به‌اشتباه پاسخ برداشت نشوند.
_ANSWER_DECL_PATS = [
    # «پاسخ صحیح: گزینه ج»، «پاسخ: گزینه ب»، «جواب گزینه د»
    re.compile(r"(?:پاسخ\s*صحیح|پاسخ|جواب)\s*[:：]?\s*گزینه\s*(الف|ا|ب|ج|د)\b"),
    # «گزینه صحیح: ب»، «گزینه صحیح ج»
    re.compile(r"گزینه\s*صحیح\s*[:：]?\s*(الف|ا|ب|ج|د)\b"),
    # «کم گزینه ب» / «… گزینه ب» در ابتدای excerpt پاسخنامه
    re.compile(r"^\s*(?:کم\s+)?گزینه\s*(الف|ا|ب|ج|د)\b"),
    # «option_c» / «option c»
    re.compile(r"option[_\s-]?([abcd])\b", re.IGNORECASE),
]
_LATIN_ANS = {"a": "الف", "b": "ب", "c": "ج", "d": "د"}


def recover_answer(rec):
    """تلاش برای استخراج پاسخ از متن‌های موجود وقتی فیلد answer خالی است.

    منابع به‌ترتیب اعتماد بررسی می‌شوند و فقط اعلام‌های صریح پذیرفته می‌شوند.
    """
    sources = [
        s(rec.get("citation_line")),
        s(rec.get("answer_excerpt")),
        s(rec.get("classification_evidence_quote")),
    ]
    for text in sources:
        if not text:
            continue
        for pat in _ANSWER_DECL_PATS:
            m = pat.search(text)
            if m:
                g = m.group(1).lower()
                if g in _LATIN_ANS:
                    return _LATIN_ANS[g]
                return _ANSWER_MAP.get(m.group(1), "")
    return ""


# ---------------------------------------------------------------------------
# اطمینان (confidence) و وضعیت (status) — فقط برای پردازش داخلی
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
    # کل این بانک از آزمون بورد/ارتقای ۱۴۰۳ است؛ پیش‌فرضِ نامشخص «بورد» در نظر گرفته
    # می‌شود تا برچسب نامشخص در UI نمایش داده نشود.
    return "بورد"


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
    if s(corr.get("status")).lower() == "resolved":
        base["review_needed_final"] = False
    base["_merge_source"] = "remaining21"


def apply_198(base, corr, debug):
    """اولویت ۲: اصلاح رفرنس/فصل با sanity-check.

    اصلاح فقط زمانی اعمال می‌شود که با متن سؤال، original_reference و سطح
    اطمینان تناقض نداشته باشد. در غیر این صورت رکورد دست‌نخورده می‌ماند و علت در
    گزارش debug ثبت می‌شود.
    """
    corr_ref = s(corr.get("reference"))
    conf = normalize_confidence(corr.get("confidence"))
    base_ref = s(base.get("source_book_final"))
    base_unknown = base_ref in ("", "Unknown")

    reason = None

    # ۱) تناقض با کلیدواژه‌ی رفرنس داخل متن سؤال (مثلاً متن می‌گوید «اسپیروف» ولی اصلاح «نواک»)
    hint = detect_ref_hint(corr.get("question_short"), base.get("raw_question"), base.get("stem"))
    if corr_ref and hint and hint != corr_ref:
        reason = "ref_hint_conflict:%s≠%s" % (hint, corr_ref)

    # ۲) تناقض با original_reference (وقتی یک کتاب واقعیِ متفاوت است)
    orig = s(corr.get("original_reference"))
    if reason is None and corr_ref and orig and orig in BOOK_FA and orig != "Unknown" and orig != corr_ref:
        reason = "original_reference_conflict:%s≠%s" % (orig, corr_ref)

    # ۳) اطمینان پایین فقط وقتی base معتبر است، اصلاح را رد کن
    if reason is None and conf == "low" and not base_unknown:
        reason = "low_confidence_kept_base"

    if reason is not None:
        debug.append(OrderedDict([
            ("id", base.get("question_id")),
            ("action", "skipped"),
            ("reason", reason),
            ("base_ref", base_ref),
            ("corr_ref", corr_ref),
        ]))
        return

    # اعمال اصلاح رفرنس
    if corr_ref:
        base["source_book_final"] = corr_ref
    # فصل/عنوان فصل فقط وقتی base فصل عددی معتبر ندارد یا base نامطمئن بوده اعمال می‌شود،
    # تا عنوان‌های نامرتبطِ احتمالی روی فصل‌های درستِ موجود ننشینند.
    base_chapter = s(base.get("chapter_final") or base.get("chapter"))
    base_has_numeric = bool(re.search(r"\d", base_chapter)) and base_chapter != REVIEW_CHAPTER
    ch = s(corr.get("chapter"))
    cht = s(corr.get("chapter_title"))
    if ch and (base_unknown or not base_has_numeric):
        base["chapter_final"] = ch
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
        answer = recover_answer(rec)

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
        explanation = clean_explanation_text(first_nonempty(
            rec.get("citation_line"),
            rec.get("classification_evidence_quote"),
            rec.get("evidence_quote"),
        ))

    explanation_missing = len(explanation) < 8
    if explanation_missing:
        # هیچ متن جایگزینِ «بازبینی» نمایش داده نمی‌شود؛ UI بخش خالی را پنهان می‌کند.
        explanation = ""

    # ---- فصل / موضوع ----
    chapter = first_nonempty(rec.get("chapter_final"), rec.get("chapter"))
    chapter_title = first_nonempty(rec.get("chapter_title_final"))
    # عنوان فصلِ junk (حاوی «نامشخص» یا مارکر بازبینی) دور ریخته می‌شود تا موضوع
    # امن‌تری از classification_topic یا برچسب خنثی جایگزین شود.
    if "نامشخص" in chapter_title or REVIEW_CHAPTER in chapter_title:
        chapter_title = ""
    topic = usable_topic(rec.get("classification_topic"))

    chapter_is_numeric = bool(re.search(r"\d", chapter)) and chapter != REVIEW_CHAPTER

    if not chapter or chapter == REVIEW_CHAPTER:
        # فصل واقعی ندارد → نمای موضوعی (بدون هیچ برچسب بازبینی)
        is_topic = True
        chapter = ""
        chapter_title = chapter_title or topic or NEUTRAL_TOPIC
        chapter_label = "موضوع: %s" % chapter_title
        reference_text = "%s - %s" % (book_fa, chapter_title)
    elif not chapter_is_numeric:
        # فصلِ متنی (موضوعات آپتودیت، اخلاق و …) → نمای موضوعی
        is_topic = True
        title = chapter_title or chapter
        chapter_label = "موضوع: %s" % title
        if chapter and chapter != title:
            reference_text = "%s - %s - %s" % (book_fa, chapter, title)
        else:
            reference_text = "%s - %s" % (book_fa, title)
        chapter_title = title
    else:
        # فصل عددی
        is_topic = False
        chapter_title = chapter_title or topic or NEUTRAL_TOPIC
        chapter_label = "فصل %s - %s" % (chapter, chapter_title)
        reference_text = "%s - فصل %s - %s" % (book_fa, chapter, chapter_title)

    chapter_key = "%s::%s::%s" % (book_fa, chapter, chapter_title)

    # ---- وضعیت داخلی (نمایش داده نمی‌شود) ----
    status = s(rec.get("classification_status")).lower()
    if status not in ("resolved", "review"):
        status = "review" if rec.get("review_needed_final") else "resolved"
    review_needed = bool(rec.get("review_needed_final")) or status == "review"
    if missing_opts or not answer or explanation_missing:
        review_needed = True

    # شماره‌ی سؤال از بخش بعد از خط تیره استخراج می‌شود (Q1403-0249 → ۲۴۹)
    mnum = re.search(r"-(\d+)\s*$", qid) or re.search(r"(\d+)\s*$", qid)
    try:
        source_number = int(mnum.group(1)) if mnum else fallback_index
    except (AttributeError, ValueError):
        source_number = fallback_index

    out = OrderedDict([
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
        ("question_number", source_number),
        ("stem", stem),
        ("options", options),
        ("answer", answer),
        ("answer_raw", raw_answer),
        ("explanation", explanation),
        ("reference_text", reference_text),
        ("source_question_id", qid),
        # فیلدهای داخلیِ کیفیت (با پیشوند _، از خروجی عمومی حذف می‌شوند)
        ("_confidence", normalize_confidence(rec.get("classification_confidence"))),
        ("_status", status),
        ("_review_needed", review_needed),
        ("_missing_options", missing_opts),
        ("_explanation_missing", explanation_missing),
    ])

    # ---- اعمال override سخت ----
    ov = HARD_OVERRIDES.get(qid)
    if ov:
        for k, v in ov.items():
            out[k] = v
        out["chapter_key"] = "%s::%s::%s" % (
            out["book_fa"], out["chapter"], out["chapter_title"])
        out["_review_needed"] = False
        out["_status"] = "resolved"
        out["_explanation_missing"] = False
        out["_missing_options"] = []

    return out


# ---------------------------------------------------------------------------
# ساخت خلاصه‌ی آماری (فقط برای ساخت dropdown ها؛ بدون شمارنده‌ی بازبینی)
# ---------------------------------------------------------------------------
def build_summary(questions):
    by_book = Counter(q["book_fa"] for q in questions)

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
            ])
        chapters_by_book[b][key]["count"] += 1
        chapter_seen[key] = True

    def chap_sort_key(c):
        m = re.search(r"\d+", str(c["chapter"]))
        if not c["chapter"]:
            return (1, 0, str(c["chapter_title"]))
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
        ("by_book", OrderedDict((b["book_fa"], b["count"]) for b in books)),
        ("book_order", [b["book_fa"] for b in books]),
        ("primary_books", PRIMARY_BOOKS),
        ("books", books),
    ])


# ---------------------------------------------------------------------------
# گزارش کیفیت داده (debug — در UI استفاده نمی‌شود)
# ---------------------------------------------------------------------------
ARTIFACT_PATS = ["#### فریم", "!!! info", "!!! note", "!!! warning", "{#", "〔F", "```",
                 "نیازمند بازبینی علمی", "QUALITY_GATE"]


def build_quality_report(questions, total_loaded, merge_stats):
    def has_artifact(q):
        blob = " ".join([q["stem"], q["explanation"]] + list(q["options"].values()))
        return any(p in blob for p in ARTIFACT_PATS)

    by_book = Counter(q["book_fa"] for q in questions)
    by_chapter = Counter(q["chapter_label"] for q in questions)

    return OrderedDict([
        ("total", total_loaded),
        ("exported", len(questions)),
        ("with_answer", sum(1 for q in questions if q["answer"])),
        ("by_book", OrderedDict(sorted(by_book.items()))),
        ("by_chapter", OrderedDict(sorted(by_chapter.items()))),
        ("missing_options", [q["question_id"] for q in questions if q["_missing_options"]]),
        ("missing_answer", [q["question_id"] for q in questions if not q["answer"]]),
        ("missing_explanation", [q["question_id"] for q in questions if q["_explanation_missing"]]),
        ("internal_review_needed", [q["question_id"] for q in questions if q["_review_needed"]]),
        ("raw_markdown_artifacts", [q["question_id"] for q in questions if has_artifact(q)]),
        ("unknown_reference", [q["question_id"] for q in questions if q["book_en"] == "Unknown"]),
        ("merge_stats", merge_stats),
    ])


# ---------------------------------------------------------------------------
# اجرای اصلی
# ---------------------------------------------------------------------------
# کلیدهای مجاز در خروجی عمومی (questions.json). فیلدهای داخلی (_*) و برچسب‌های
# وضعیت/اطمینان/بازبینی هرگز منتشر نمی‌شوند.
PUBLIC_KEYS = [
    "question_id", "book_en", "book_fa", "chapter", "chapter_title",
    "chapter_label", "chapter_key", "is_topic", "exam_type", "exam_region",
    "year", "question_number", "stem", "options", "answer", "answer_raw",
    "explanation", "reference_text", "source_question_id",
]


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

    # --- شماره‌گذاری سراسری ---
    for n, q in enumerate(questions, start=1):
        q["global_number"] = n

    summary = build_summary(questions)

    merge_stats = OrderedDict([
        ("applied_remaining21", applied21),
        ("applied_unresolved198", applied198),
        ("skipped_unresolved198", skipped198),
        ("hard_overrides", list(HARD_OVERRIDES.keys())),
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
        for q in questions if q["_review_needed"]
    ]

    # --- خروجی عمومی: فقط کلیدهای مجاز ---
    public_questions = []
    for q in questions:
        pub = OrderedDict((k, q[k]) for k in PUBLIC_KEYS if k in q)
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
    print("  کل سؤال‌ها:             %d" % summary["total"])
    print("  دارای پاسخ:            %d" % quality["with_answer"])
    print("  گزینه‌ی ناقص:           %d" % len(quality["missing_options"]))
    print("  پاسخنامه‌ی خالی:        %d" % len(quality["missing_explanation"]))
    print("  رفرنس نامشخص:          %d" % len(quality["unknown_reference"]))
    print("  artifact باقی‌مانده:    %d" % len(quality["raw_markdown_artifacts"]))
    print("  به تفکیک رفرنس:")
    for book, cnt in summary["by_book"].items():
        print("    - %-8s %d" % (book + ":", cnt))


if __name__ == "__main__":
    main()
