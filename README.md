# Japanese & English Vocabulary Trainer

Ứng dụng học từ vựng **tiếng Nhật** và **tiếng Anh** bằng Flashcard & Quiz, hỗ trợ phát âm online/offline.

---

## Tính năng chính

| Tính năng | Mô tả |
|-----------|--------|
| **Flashcard** | Học từ, hiện/ẩn đáp án bằng `Space` |
| **Quiz** | Trắc nghiệm 4 đáp án, báo đúng/sai ngay trên nút |
| **Lọc dữ liệu** | Theo Loại · Nguồn (file JSON) · Lesson/Topic |
| **Chiều học** | Japanese ↔ Vietnamese · English ↔ Definition/Example |
| **Phát âm** | Online (`edge-tts` → `gTTS`) · Offline (`pyttsx3`) |
| **Đa nguồn** | Marugoto A1 (vocab, grammar, kanji) · Langeek English |

---

## Yêu cầu hệ thống

- Python **3.9+**
- Windows / macOS / Linux
  *(Windows SAPI offline chỉ hoạt động trên Windows)*

---

## Cài đặt

### 1. Tạo môi trường ảo

```bash
python -m venv .venv
```

### 2. Kích hoạt môi trường ảo

```bash
# Windows (cmd)
.venv\Scripts\activate.bat

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

### 3. Cài thư viện

```bash
pip install -r requirements.txt
```

Nội dung `requirements.txt`:

```txt
gTTS>=2.5.4
edge-tts>=6.1.9
pyttsx3>=2.98
pygame>=2.5.0
playsound==1.3.0
...
```

---

## Chạy ứng dụng

### Windows (khuyến nghị)

```bat
run.bat
```

Nội dung `run.bat`:

```bat
@echo off
call .venv\Scripts\activate.bat
python main.py
pause
```

### Thủ công

```bash
# Đã activate .venv
python main.py
```

---

## Cấu trúc thư mục

```
Flash_card_tool/
├── main.py                 # UI chính (Tkinter)
├── vocabulary.py           # Load & chuẩn hóa dữ liệu
├── audio.py                # TTS online/offline + cache
├── formatFile.py           # Chuyển MD/TXT → JSON
├── requirements.txt
├── run.bat
├── data/                   # JSON đã format (app tự load)
│   ├── a1-katsudou_formatted.json
│   ├── a1-rikai_formatted.json
│   ├── a1-marugoto_grammar_formatted.json
│   ├── a1-kanji_formatted.json
│   └── langeek_....json
├── docs/                   # Markdown nguồn Marugoto
│   ├── marugoto_a1_grammar_summary.md
│   └── marugoto_a1_kanji_summary.md
└── audio_cache/            # Cache file .mp3 (tự tạo)
```

---

## Chuẩn bị dữ liệu

### A. Từ Markdown Marugoto (Grammar + Kanji)

1. Đặt 2 file vào `docs/`:
   - `marugoto_a1_grammar_summary.md`
   - `marugoto_a1_kanji_summary.md`
2. Chạy:

```bash
python formatFile.py
```

3. Kết quả trong `data/`:
   - `a1-marugoto_grammar_formatted.json`
   - `a1-kanji_formatted.json`

### B. Load JSON có sẵn

- Đặt file `.json` vào thư mục `data/` → app tự load khi mở.
- Hoặc bấm **📂 Load JSON** trong app để chọn file thủ công.

Định dạng được hỗ trợ:

| Loại | Nhận diện |
|------|-----------|
| Japanese vocab | `kanji` / `hiragana` / `meaning` / `lesson` |
| English Langeek | `topic_title` + `entries[]` |
| Grammar | tên file chứa `grammar` |
| Kanji | tên file chứa `kanji` |

---

## Hướng dẫn sử dụng

### Thanh thiết lập

- **Loại**: Mixed · Kanji · Hiragana · English · Grammar
- **Nguồn**: theo tên file JSON (Katsudou, Rikai, Grammar, Kanji, Langeek…)
- **Lesson**: bài học / topic trong nguồn đã chọn
- **Mode**: Flashcard hoặc Quiz
- **Chiều**: hướng hỏi–đáp

### Phím tắt

| Phím | Chức năng |
|------|-----------|
| `Space` | Hiện / ẩn đáp án (Flashcard) |
| `←` `→` | Thẻ trước / thẻ sau |
| `Enter` | Câu tiếp theo (Quiz, sau khi đã trả lời) |
| `A` | Nghe phát âm |
| `1` – `4` | Chọn đáp án trong Quiz |

### Phát âm

1. Ưu tiên **edge-tts** (giọng Neural).
2. Nếu lỗi → **gTTS**.
3. Vẫn lỗi hoặc chọn Offline → **pyttsx3** (máy).
4. File `.mp3` được cache trong `audio_cache/` → lần sau không gọi lại TTS.
5. Phát bằng **pygame** trong nền → **không mở cửa sổ player**.

---

## Xuất lại requirements

Khi đã cài thêm thư viện trong `.venv`:

```bash
pip freeze > requirements.txt
```

---

## Xử lý lỗi thường gặp

| Lỗi | Cách xử lý |
|-----|------------|
| `No module named 'edge_tts'` | `pip install edge-tts` |
| `No module named 'pygame'` | `pip install pygame` |
| Mở cửa sổ .mp3 khi nghe | Cài `pygame`, đảm bảo không fallback sang OS player |
| Kanji đọc sai (có romaji) | Chạy lại `formatFile.py` (đã clean reading) |
| Không load được JSON | Kiểm tra file nằm trong `data/` và đúng format |

---

## License

Dự án cá nhân – tự do sử dụng và chỉnh sửa.
