"""
formatFile.py
-------------
Công cụ chuyển đổi dữ liệu thô (TXT / JSON / Markdown Marugoto)
sang JSON chuẩn để app Vocabulary Trainer load được.

Hỗ trợ:
- parse_txt_to_json        : TXT dạng Lesson/Word/Meaning
- normalize_vocab         : chuẩn hóa JSON Nhật thô
- parse_marugoto_md       : parse 2 file MD grammar + kanji

Cấu trúc MD thực tế (quan trọng):
  Grammar:
    ### **Bài 1: ...**
    *   **Tên mẫu:** `pattern` (romaji) -> nghĩa.
        *   ví dụ tiếng Nhật
        *   *(Romaji)* -> nghĩa ví dụ
  Kanji:
    ## 1. Chủ đề
    *   **一** (いち - ichi): Một
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_dir(folder: str | Path) -> Path:
    """Tạo thư mục nếu chưa có, trả về Path."""
    p = Path(folder)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_json(data: list, output_folder: str | Path, output_name: str) -> Path:
    """Ghi list dict ra file JSON utf-8, indent=2."""
    out = _ensure_dir(output_folder) / output_name
    out.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Đã xuất file: {out}  ({len(data)} mục)")
    return out


# ---------------------------------------------------------------------------
# 1. TXT → JSON (Lesson / Word / Meaning)
# ---------------------------------------------------------------------------

def parse_txt_to_json(txt_file, output_folder, output_name):
    """
    TXT format:
        Lesson: 1
        Word: あ
        Meaning: À
    """
    vocab = []
    item: dict = {}

    with open(txt_file, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            if line.startswith("Lesson:"):
                item["lesson"] = line.split(":", 1)[1].strip()
            elif line.startswith("Word:"):
                item["hiragana"] = line.split(":", 1)[1].strip()
            elif line.startswith("Meaning:"):
                item["meaning"] = line.split(":", 1)[1].strip()
                if item.get("lesson") and item.get("hiragana"):
                    vocab.append(item)
                item = {}

    _write_json(vocab, output_folder, output_name)
    return vocab


# ---------------------------------------------------------------------------
# 2. Normalize JSON Nhật thô
# ---------------------------------------------------------------------------

def normalize_vocab(input_file, output_folder, output_name):
    """
    Chuẩn hóa JSON Nhật về format thống nhất:
        kanji, hiragana, meaning, lesson
    """
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Một số file bọc trong key data / items / vocabulary
    if isinstance(data, dict):
        data = (
            data.get("data")
            or data.get("items")
            or data.get("vocabulary")
            or [data]
        )

    normalized = []
    for item in data:
        if not isinstance(item, dict):
            continue

        hiragana = str(item.get("hiragana") or item.get("reading") or "").strip()
        kanji = str(item.get("kanji") or item.get("word") or "").strip()

        # Format cũ: "hiragana": "たべます／食べます"
        if "／" in hiragana:
            parts = [x.strip() for x in hiragana.split("／", 1)]
            hiragana = parts[0]
            if not kanji:
                kanji = parts[1]

        if not kanji:
            kanji = None

        normalized.append({
            "kanji": kanji,
            "hiragana": hiragana,
            "meaning": str(
                item.get("meaning") or item.get("translation") or ""
            ).strip(),
            "lesson": str(
                item.get("lesson") or item.get("unit") or ""
            ).strip(),
        })

    _write_json(normalized, output_folder, output_name)
    return normalized


# ---------------------------------------------------------------------------
# 3. Parse Marugoto Markdown (Grammar + Kanji)
# ---------------------------------------------------------------------------

def parse_marugoto_md(md_file, output_folder, output_name, kind="grammar"):
    """
    Parse 2 file Markdown Marugoto A1.

    kind='grammar' → mỗi bullet ngữ pháp thành 1 item
    kind='kanji'   → mỗi chữ kanji thành 1 item
    """
    text = Path(md_file).read_text(encoding="utf-8")

    if kind == "kanji":
        return _parse_kanji_md(text, output_folder, output_name)
    return _parse_grammar_md(text, output_folder, output_name)


def _parse_kanji_md(text: str, output_folder, output_name):
    """
    Parse kanji MD.

    Dòng mẫu thực tế:
        *   **一** (いち - ichi): Một
        *   **四** (よん / し - yon / shi): Bốn
        *   **百** (ひゃく - hyaku): Trăm *(Vd: 三百 - さんびゃく - 300)*

    Regex bắt:
        **kanji** (reading): meaning
    """
    topic = ""
    result = []

    # Bắt cả dòng bắt đầu bằng * hoặc - rồi tới **kanji**
    kanji_re = re.compile(
        r"""
        ^[\*\-]\s+                  # * hoặc - đầu dòng
        \*\*(.+?)\*\*               # **kanji**
        \s*                         # khoảng trắng
        \((.+?)\)                   # (reading)
        \s*:\s*                     # :
        (.+)                        # meaning (phần còn lại)
        """,
        re.VERBOSE,
    )

    for raw in text.splitlines():
        line = raw.strip()

        # ## 1. Chủ đề  →  topic
        if line.startswith("## "):
            # Bỏ số thứ tự đầu (nếu có): "1. Chữ số & Tiền tệ" → "Chữ số & Tiền tệ"
            topic = re.sub(r"^##\s*\d+\.\s*", "", line).strip()
            # Bỏ markdown bold còn sót
            topic = topic.replace("**", "").strip()
            continue

        m = kanji_re.match(line)
        if not m:
            continue

        kanji, reading, meaning = m.groups()

        # # Làm sạch meaning (bỏ chú thích *Vd: ...* nếu muốn giữ nguyên thì thôi)
        # meaning = meaning.strip()
        # # Bỏ hết markdown italic còn sót ở cuối
        # meaning = re.sub(r"\s*\*\(.*$", "", meaning).strip() or meaning

        result.append({
            "kanji": kanji.strip(),
            "hiragana": reading.strip(),
            "meaning": meaning,
            "lesson": topic or "Kanji",
            "type": "Kanji",
        })

    _write_json(result, output_folder, output_name)
    return result


def _parse_grammar_md(text: str, output_folder, output_name):
    """
    Parse grammar MD.

    Cấu trúc thực tế:
        ## **Topic 1: ...**
        ### **Bài 1: Chào hỏi & Tự giới thiệu**
        *   **Mẫu câu giới thiệu tên:** `N1 は N2 です` (N1 wa N2 desu) -> N1 là N2.
            *   わたしは マイです。
            *   *(Watashi wa Mai desu.)* -> Tôi là Mai.
        *   **Chào hỏi cơ bản:**
            *   おはようございます *(Ohayou gozaimasu)* -> Chào buổi sáng.

    Mỗi bullet cấp 1 (*   **...**) = 1 mục ngữ pháp.
    Các bullet cấp 2 (indent) = example / romaji.
    """
    topic = ""
    lesson = ""
    result = []
    current: dict | None = None

    # Bullet cấp 1: bắt đầu bằng * hoặc - rồi **title**
    # Có thể có hoặc không có pattern/romaji/meaning trên cùng dòng
    top_bullet_re = re.compile(
        r"""
        ^[\*\-]\s+                  # * hoặc -
        \*\*(.+?)\*\*               # **tiêu đề mẫu**
        \s*:?\s*                    # : tùy chọn
        (.*)                        # phần còn lại của dòng (pattern / nghĩa)
        """,
        re.VERBOSE,
    )

    # Bullet cấp 2 (indent ≥ 2 space hoặc tab)
    sub_bullet_re = re.compile(r"^\s{2,}[\*\-]\s+(.*)")

    for raw in text.splitlines():
        # Giữ nguyên indent để phân biệt cấp
        stripped = raw.strip()
        if not stripped:
            continue

        # ----- Heading -----
        if stripped.startswith("## "):
            topic = stripped[3:].replace("**", "").strip()
            lesson = ""  # reset khi sang topic mới
            current = None
            continue

        if stripped.startswith("### "):
            lesson = stripped[4:].replace("**", "").strip()
            current = None
            continue

        # ----- Bullet cấp 1 (mẫu ngữ pháp mới) -----
        # Chỉ nhận dòng bắt đầu bằng * hoặc - (không indent)
        if re.match(r"^[\*\-]\s+", raw) and not raw.startswith(" "):
            m = top_bullet_re.match(stripped)
            if not m:
                current = None
                continue

            title, rest = m.groups()
            title = title.strip()
            rest = rest.strip()

            # Tách pattern / romaji / nghĩa từ phần rest nếu có
            # Ví dụ: `N1 は N2 です` (N1 wa N2 desu) -> N1 là N2.
            pattern = ""
            romaji = ""
            meaning = ""

            # Pattern trong backtick
            bt = re.search(r"`([^`]+)`", rest)
            if bt:
                pattern = bt.group(1).strip()
                rest_after = rest[bt.end():].strip()
            else:
                rest_after = rest

            # Romaji trong ngoặc đơn ngay sau pattern
            rom = re.search(r"^\(([^)]+)\)", rest_after)
            if rom:
                romaji = rom.group(1).strip()
                rest_after = rest_after[rom.end():].strip()

            # Nghĩa sau mũi tên -> hoặc —
            mean = re.search(r"(?:->|→|—|-)\s*(.+)$", rest_after)
            if mean:
                meaning = mean.group(1).strip()
            elif rest_after and not pattern:
                # Không có pattern riêng → cả rest là nghĩa / mô tả
                meaning = rest_after

            # Nếu không tách được pattern thì dùng title làm pattern
            if not pattern:
                pattern = title

            current = {
                "lesson": lesson or topic or "Grammar",
                "pattern": pattern,
                "title": title,          # tiêu đề gốc (Mẫu câu giới thiệu tên...)
                "meaning": meaning,
                "example": "",
                "romaji": romaji,
                "type": "Grammar",
            }
            result.append(current)
            continue

        # ----- Bullet cấp 2 (example / romaji) -----
        sub = sub_bullet_re.match(raw)
        if sub and current is not None:
            value = sub.group(1).strip()

            # Dạng: *(Watashi wa Mai desu.)* -> Tôi là Mai.
            # hoặc: *(Watashi wa Mai desu.)*
            rom_m = re.match(
                r"\*\((.+?)\)\*\s*(?:->|→)?\s*(.*)",
                value,
            )
            if rom_m:
                r, m = rom_m.groups()
                if not current["romaji"]:
                    current["romaji"] = r.strip()
                if m.strip():
                    # Nghĩa của ví dụ → gắn vào example nếu đã có
                    if current["example"]:
                        current["example"] += " | " + m.strip()
                    else:
                        current["meaning"] = current["meaning"] or m.strip()
                continue

            # Dạng có romaji inline: おはようございます *(Ohayou gozaimasu)* -> ...
            inline = re.match(
                r"^(.+?)\s*\*\((.+?)\)\*\s*(?:->|→)?\s*(.*)$",
                value,
            )
            if inline:
                jp, r, m = inline.groups()
                example_text = jp.strip()
                if m.strip():
                    example_text += " → " + m.strip()
                if current["example"]:
                    current["example"] += " | " + example_text
                else:
                    current["example"] = example_text
                if not current["romaji"]:
                    current["romaji"] = r.strip()
                continue

            # Ví dụ tiếng Nhật thuần hoặc có -> nghĩa
            if "->" in value or "→" in value:
                # Tách phần trước mũi tên làm example
                parts = re.split(r"\s*(?:->|→)\s*", value, maxsplit=1)
                jp = parts[0].strip()
                mean = parts[1].strip() if len(parts) > 1 else ""
                text = jp + ((" → " + mean) if mean else "")
            else:
                text = value

            if current["example"]:
                current["example"] += " | " + text
            else:
                current["example"] = text
            continue

    _write_json(result, output_folder, output_name)
    return result


# ---------------------------------------------------------------------------
# Main – chạy chuyển đổi
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent

    # Thư mục xuất (có thể đổi thành "data" nếu muốn app auto-load)
    OUT_DIR = BASE_DIR / "data"
    RAWOUT_DIR = BASE_DIR / "raw_vocab"

    DOCS_DIR = BASE_DIR / "docs"

    # ---------- Grammar ----------
    grammar_md = DOCS_DIR / "marugoto_a1_grammar_summary.md"
    if not grammar_md.exists():
        # Fallback: file nằm cùng thư mục script
        grammar_md = BASE_DIR / "marugoto_a1_grammar_summary.md"

    if grammar_md.exists():
        parse_marugoto_md(
            grammar_md,
            OUT_DIR,
            "jp_a1_marugoto_grammar.json",
            kind="grammar",
        )
    else:
        print(f"[!] Không tìm thấy: {grammar_md}")

    # ---------- Kanji ----------
    kanji_md = DOCS_DIR / "marugoto_a1_kanji_summary.md"
    if not kanji_md.exists():
        kanji_md = BASE_DIR / "marugoto_a1_kanji_summary.md"

    if kanji_md.exists():
        parse_marugoto_md(
            kanji_md,
            OUT_DIR,
            "jp_a1_kanji.json",
            kind="kanji",
        )
    else:
        print(f"[!] Không tìm thấy: {kanji_md}")

    parse_txt_to_json(
        BASE_DIR / "raw_vocab" / "a1-rikai_raw.txt",
        RAWOUT_DIR,
        "jp_a1_rikai_raw.json",
    )
    normalize_vocab(
        BASE_DIR / "raw_vocab" / "a1-katsudou_raw.json",
        OUT_DIR,
        "jp_a1_katsudou.json",
    )
    normalize_vocab(
            BASE_DIR / "raw_vocab" / "a1-rikai_raw.json",
            OUT_DIR,
            "jp_a1_rikai.json",
        )