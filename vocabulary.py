"""
vocabulary.py
-------------
Module quản lý dữ liệu từ vựng (Japanese / English / Grammar / Kanji).

Chức năng chính:
- Định nghĩa dataclass Vocabulary
- Load JSON theo nhiều format (Marugoto, Langeek, Grammar, Kanji)
- Tự nhận diện loại file dựa trên tên hoặc cấu trúc JSON
- Fallback lesson từ tên file khi JSON thiếu field lesson
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable


@dataclass
class Vocabulary:
    """
    Một mục từ vựng thống nhất cho cả tiếng Nhật và tiếng Anh.

    Attributes:
        language: "Japanese" | "English"
        word: Từ chính (kanji hoặc từ tiếng Anh)
        reading: Cách đọc (hiragana / romaji). Có thể None.
        meaning: Nghĩa (tiếng Việt hoặc definition tiếng Anh)
        lesson: Số bài / topic
        example: Câu ví dụ
        example_meaning: Nghĩa của câu ví dụ (nếu có)
        phonetic: Phiên âm IPA (chủ yếu English)
        note: Ghi chú thêm
        topic_url: URL topic (Langeek)
        source: Tên file JSON gốc
        category: Nhóm / chủ đề phụ
        type: "Grammar" | "Kanji" | None
    """
    language: str
    word: str
    reading: str | None = None
    meaning: str = ""
    lesson: str | None = None
    example: str | None = None
    example_meaning: str | None = None
    phonetic: str | None = None
    note: str | None = None
    topic_url: str | None = None
    source: str | None = None
    category: str = ""
    type: str | None = None  # "Grammar" | "Kanji" | None

    @property
    def has_kanji(self) -> bool:
        """
        True nếu là từ tiếng Nhật có kanji
        (word khác reading và cả hai đều không rỗng).
        """
        return (
            self.language == "Japanese"
            and bool((self.word or "").strip())
            and bool((self.reading or "").strip())
            and (self.word or "").strip() != (self.reading or "").strip()
        )


def _text(value: Any) -> str:
    """Chuyển giá trị bất kỳ thành chuỗi đã strip. None → ''."""
    if value is None:
        return ""
    return str(value).strip()


def _load_json(path: str | Path) -> Any:
    """Đọc file JSON với encoding utf-8."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _looks_like_langeek(data: Any) -> bool:
    """
    Kiểm tra xem JSON có đúng format Langeek không
    (list các topic, mỗi topic có topic_title + entries).
    """
    return (
        isinstance(data, list)
        and bool(data)
        and isinstance(data[0], dict)
        and "entries" in data[0]
        and "topic_title" in data[0]
    )


def _fallback_lesson_from_filename(path: Path) -> str:
    """
    Khi JSON không có field lesson, dùng tên file (stem)
    làm lesson để vẫn lọc được theo nguồn dữ liệu.
    Ví dụ: a1-katsudou_formatted → "a1 katsudou"
    """
    return path.stem.replace("_formatted", "").replace("_", " ")


def load_japanese_json(path: str | Path) -> list[Vocabulary]:
    """
    Load JSON tiếng Nhật chuẩn (Marugoto / Rikai / Katsudou).

    Format mong đợi mỗi item:
        {
            "kanji": "...",
            "hiragana": "...",
            "meaning": "...",
            "lesson": "..."
        }
    """
    path = Path(path)
    data = _load_json(path)
    if not isinstance(data, list):
        raise ValueError(f"JSON Nhật không phải là một mảng: {path}")

    fallback_lesson = _fallback_lesson_from_filename(path)
    result: list[Vocabulary] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        reading = _text(item.get("hiragana") or item.get("reading"))
        kanji = _text(item.get("kanji") or item.get("word"))

        # Hỗ trợ format cũ kiểu: "hiragana": "たべます／食べます"
        if not kanji and "／" in reading:
            parts = [p.strip() for p in reading.split("／", 1)]
            reading = parts[0]
            kanji = parts[1] if len(parts) > 1 else ""

        word = kanji or reading
        if not word:
            continue

        lesson = _text(item.get("lesson") or item.get("unit")) or fallback_lesson

        result.append(
            Vocabulary(
                language="Japanese",
                word=word,
                reading=reading or None,
                meaning=_text(item.get("meaning") or item.get("translation")),
                lesson=lesson,
                source=path.name,
                type=_text(item.get("type")) or None,
                category=_text(item.get("category")),
            )
        )

    return result


def load_english_langeek_json(path: str | Path) -> list[Vocabulary]:
    """
    Load JSON tiếng Anh format Langeek (nested topics).

    Mỗi topic có:
        topic_title, topic_url, entries[]
    Mỗi entry có:
        word, phonetic, example, note, definition_en
    """
    path = Path(path)
    data = _load_json(path)

    if not _looks_like_langeek(data):
        raise ValueError(
            "File English không đúng format Langeek: cần topic_title + entries."
        )

    result: list[Vocabulary] = []

    for topic in data:
        topic_title = _text(topic.get("topic_title"))
        topic_url = _text(topic.get("topic_url"))

        for entry in topic.get("entries", []):
            if not isinstance(entry, dict):
                continue

            word = _text(entry.get("word"))
            if not word:
                continue

            result.append(
                Vocabulary(
                    language="English",
                    word=word,
                    phonetic=_text(entry.get("phonetic")) or None,
                    example=_text(entry.get("example")) or None,
                    note=_text(entry.get("note")) or None,
                    # definition_en là nghĩa chính
                    meaning=_text(entry.get("definition_en") or entry.get("definition")),
                    lesson=topic_title or _fallback_lesson_from_filename(path),
                    source=path.name,
                    topic_url=topic_url or None,
                )
            )

    return result


def load_grammar_json(path: str | Path) -> list[Vocabulary]:
    """
    Load JSON ngữ pháp (xuất từ marugoto_a1_grammar_summary.md).

    Mỗi item thường có:
        pattern, meaning, example, romaji, lesson, type="Grammar"
    """
    path = Path(path)
    data = _load_json(path)
    if not isinstance(data, list):
        raise ValueError(f"JSON Grammar không phải mảng: {path}")

    fallback_lesson = _fallback_lesson_from_filename(path)
    result: list[Vocabulary] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        pattern = _text(item.get("pattern") or item.get("word"))
        if not pattern:
            continue

        example = _text(item.get("example"))
        # Nếu không có meaning riêng thì dùng example làm nghĩa
        meaning = _text(item.get("meaning")) or example
        romaji = _text(item.get("romaji") or item.get("reading"))

        result.append(
            Vocabulary(
                language="Japanese",
                word=pattern,
                reading=romaji or None,
                meaning=meaning,
                example=example or None,
                lesson=_text(item.get("lesson")) or fallback_lesson,
                source=path.name,
                type="Grammar",
                category="Grammar",
            )
        )

    return result


def load_kanji_json(path: str | Path) -> list[Vocabulary]:
    """
    Load JSON kanji (xuất từ marugoto_a1_kanji_summary.md).

    Mỗi item thường có:
        kanji, hiragana/reading, meaning, lesson, type="Kanji"
    """
    path = Path(path)
    data = _load_json(path)
    if not isinstance(data, list):
        raise ValueError(f"JSON Kanji không phải mảng: {path}")

    fallback_lesson = _fallback_lesson_from_filename(path)
    result: list[Vocabulary] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        kanji = _text(item.get("kanji") or item.get("word") or item.get("pattern"))
        reading = _text(
            item.get("hiragana") or item.get("reading") or item.get("romaji")
        )
        meaning = _text(item.get("meaning"))

        if not kanji and not reading:
            continue

        word = kanji or reading

        result.append(
            Vocabulary(
                language="Japanese",
                word=word,
                reading=reading or None,
                meaning=meaning,
                lesson=_text(item.get("lesson")) or fallback_lesson,
                source=path.name,
                type="Kanji",
                category="Kanji",
            )
        )

    return result


def load_vocab(path: str | Path) -> list[Vocabulary]:
    """
    Hàm load thống nhất.

    Thứ tự nhận diện:
    1. Tên file chứa "grammar" → load_grammar_json
    2. Tên file chứa "kanji"   → load_kanji_json
    3. Cấu trúc Langeek        → load_english_langeek_json
    4. Còn lại                 → load_japanese_json
    """
    path = Path(path)
    name = path.name.lower()

    # Ưu tiên nhận diện theo tên file (ổn định hơn)
    if "grammar" in name:
        return load_grammar_json(path)
    if "kanji" in name:
        return load_kanji_json(path)

    data = _load_json(path)

    if _looks_like_langeek(data):
        return load_english_langeek_json(path)

    # Fallback: Japanese vocab thường
    return load_japanese_json(path)


def load_multiple_files(paths: Iterable[str | Path]) -> list[Vocabulary]:
    """Load nhiều file JSON và gộp thành một list Vocabulary."""
    result: list[Vocabulary] = []
    for path in paths:
        result.extend(load_vocab(path))
    return result


# ---------------------------------------------------------------------------
# Optional conversion helpers (dùng khi cần chuẩn hóa dữ liệu thô)
# ---------------------------------------------------------------------------

def normalize_japanese_json(
    input_file: str | Path,
    output_file: str | Path,
) -> None:
    """
    Chuẩn hóa JSON Nhật về format thống nhất:
        kanji / hiragana / meaning / lesson
    """
    data = _load_json(input_file)
    normalized = []

    for item in data:
        if not isinstance(item, dict):
            continue

        reading = _text(item.get("hiragana"))
        kanji = _text(item.get("kanji")) or None

        # Hỗ trợ format cũ: "hiragana": "たべます／食べます"
        if not kanji and "／" in reading:
            parts = [p.strip() for p in reading.split("／", 1)]
            reading = parts[0]
            kanji = parts[1] or None

        normalized.append(
            {
                "kanji": kanji,
                "hiragana": reading,
                "meaning": _text(item.get("meaning")),
                "lesson": item.get("lesson"),
            }
        )

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)


def convert_langeek_english_to_simple_json(
    input_file: str | Path,
    output_file: str | Path,
) -> None:
    """
    Chuyển JSON Langeek nested thành JSON phẳng dễ đọc.

    Lưu ý: File nguồn hiện tại không có bản dịch tiếng Việt,
    vì vậy không tự bịa meaning tiếng Việt.
    """
    vocab = load_english_langeek_json(input_file)
    normalized = [
        {
            "word": item.word,
            "phonetic": item.phonetic,
            "example": item.example,
            "note": item.note,
            "definition_en": item.meaning,
            "topic": item.lesson,
            "topic_url": item.topic_url,
        }
        for item in vocab
    ]

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)