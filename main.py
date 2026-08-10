from __future__ import annotations

import random
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from vocabulary import Vocabulary, load_multiple_files
from audio import SpeechManager


APP_TITLE = "Japanese & English Vocabulary Trainer"
WINDOW_WIDTH = 1180
WINDOW_HEIGHT = 820

BG = "#0b1020"
PANEL = "#111827"
CARD = "#172033"
CARD_2 = "#1d2942"
BORDER = "#2b3a5e"

TEXT = "#f8fafc"
MUTED = "#a9b7d6"
PRIMARY = "#4055d6"
PRIMARY_HOVER = "#5267ec"
SUCCESS = "#16a36b"
SUCCESS_BG = "#123d32"
DANGER = "#dc4c4c"
DANGER_BG = "#451f28"
WARNING = "#e4a72c"
WHITE = "#ffffff"


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def app_exe_dir() -> Path:
    """Thư mục chứa file .exe (để user thả thêm JSON)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class VocabularyApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(1020, 700)
        self.configure(bg=BG)

        self.vocab: list[Vocabulary] = []
        self.filtered_vocab: list[Vocabulary] = []

        self.current_index = 0
        self.show_answer = False

        # Quiz
        self.quiz_score = 0
        self.quiz_answered = False
        self.quiz_correct_answer = ""
        self.quiz_choices: list[str] = []
        self.quiz_selected: str | None = None

        # Settings
        self.study_mode_var = tk.StringVar(value="Flashcard")
        self.study_type_var = tk.StringVar(value="Mixed")
        self.card_mode_var = tk.StringVar(value="Japanese → Vietnamese")
        self.source_var = tk.StringVar(value="All")
        self.lesson_var = tk.StringVar(value="All")

        self.counter_var = tk.StringVar(value="0 / 0")
        self.status_var = tk.StringVar(value="Đang khởi tạo...")
        self.score_var = tk.StringVar(value="Điểm: 0")
        self.speech_status_var = tk.StringVar(value="")

        self.speech = SpeechManager()

        self.setup_style()
        self.build_ui()
        self.bind_keyboard()
        self.center_window()

        self.after(100, self.auto_load_data)
        # ----- Icon riêng -----
        icon_path = app_base_dir() / "flashcard.ico"
        if icon_path.exists():
            try:
                # Windows: iconbitmap dùng .ico
                self.iconbitmap(default=str(icon_path))
            except Exception:
                pass
            try:
                # Fallback đa nền tảng (cần PNG cũng được nếu dùng iconphoto)
                from tkinter import PhotoImage
                # Nếu có app.png thì dùng:
                png_path = app_base_dir() / "flashcard.png"
                if png_path.exists():
                    self._icon_img = PhotoImage(file=str(png_path))
                    self.iconphoto(True, self._icon_img)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # STYLE
    # ------------------------------------------------------------------

    def setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)

        style.configure(
            "Title.TLabel",
            background=BG,
            foreground=TEXT,
            font=("Segoe UI", 23, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=BG,
            foreground=MUTED,
            font=("Segoe UI", 10),
        )

        style.configure(
            "Card.TLabelframe",
            background=CARD,
            foreground=TEXT,
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Card.TLabelframe.Label",
            background=CARD,
            foreground=TEXT,
            font=("Segoe UI", 10, "bold"),
        )

        style.configure(
            "Card.TLabel",
            background=CARD,
            foreground=TEXT,
            font=("Segoe UI", 11),
        )
        style.configure(
            "Muted.Card.TLabel",
            background=CARD,
            foreground=MUTED,
            font=("Segoe UI", 10),
        )

        style.configure(
            "App.TButton",
            background=PRIMARY,
            foreground=WHITE,
            padding=(13, 8),
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )
        style.map(
            "App.TButton",
            background=[("active", PRIMARY_HOVER)],
        )

        style.configure(
            "Success.TButton",
            background=SUCCESS,
            foreground=WHITE,
            padding=(13, 8),
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )
        style.map(
            "Success.TButton",
            background=[("active", "#1fbd82")],
        )

        style.configure(
            "Danger.TButton",
            background=DANGER,
            foreground=WHITE,
            padding=(13, 8),
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )

        style.configure(
            "Answer.TButton",
            background=CARD_2,
            foreground=TEXT,
            padding=(14, 12),
            font=("Segoe UI", 11, "bold"),
            borderwidth=1,
        )

        style.configure(
            "Correct.Answer.TButton",
            background=SUCCESS_BG,
            foreground="#78f0c2",
            padding=(14, 12),
            font=("Segoe UI", 11, "bold"),
            borderwidth=1,
        )

        style.configure(
            "Wrong.Answer.TButton",
            background=DANGER_BG,
            foreground="#ff8f9b",
            padding=(14, 12),
            font=("Segoe UI", 11, "bold"),
            borderwidth=1,
        )

        style.configure(
            "App.TCombobox",
            fieldbackground="#0f1630",
            background="#0f1630",
            foreground=TEXT,
            arrowcolor=TEXT,
            padding=7,
        )

        style.map(
            "App.TCombobox",
            fieldbackground=[("readonly", "#0f1630")],
            foreground=[("readonly", TEXT)],
        )

        style.configure(
            "Horizontal.TProgressbar",
            troughcolor="#0e1528",
            background=PRIMARY,
            borderwidth=0,
            thickness=8,
        )

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def build_ui(self):
        root = ttk.Frame(self, style="App.TFrame", padding=18)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root, style="App.TFrame")
        header.pack(fill="x")

        ttk.Label(
            header,
            text="日本語 & English Vocabulary Trainer",
            style="Title.TLabel",
        ).pack(side="left")

        ttk.Button(
            header,
            text="📂 Load JSON",
            style="Success.TButton",
            command=self.load_files,
        ).pack(side="right")

        ttk.Label(
            root,
            text=(
                "Flashcard đơn giản · Quiz có phản hồi đúng/sai ngay trên đáp án "
                "· Phát âm online/offline"
            ),
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 12))

        self.build_settings(root)

        self.progress = ttk.Progressbar(
            root,
            style="Horizontal.TProgressbar",
            maximum=100,
            value=0,
        )
        self.progress.pack(fill="x", pady=(12, 8))

        self.study_card = tk.Frame(
            root,
            bg=CARD,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.study_card.pack(fill="both", expand=True, pady=(0, 12))

        footer = ttk.Frame(root, style="App.TFrame")
        footer.pack(fill="x")

        ttk.Label(
            footer,
            textvariable=self.status_var,
            style="Subtitle.TLabel",
        ).pack(side="left")

        ttk.Label(
            footer,
            textvariable=self.speech_status_var,
            style="Subtitle.TLabel",
        ).pack(side="left", padx=18)

        ttk.Label(
            footer,
            textvariable=self.counter_var,
            style="Subtitle.TLabel",
        ).pack(side="right")

        self.build_navigation(root)

    def build_settings(self, parent):
        settings = ttk.LabelFrame(
            parent,
            text="Thiết lập",
            style="Card.TLabelframe",
            padding=10,
        )
        settings.pack(fill="x")

        for col in range(11):
            settings.columnconfigure(col, weight=0)
        settings.columnconfigure(10, weight=1)

        # --- Loại ---
        ttk.Label(settings, text="Loại:", style="Card.TLabel").grid(row=0, column=0, padx=5)
        self.study_type_combo = ttk.Combobox(
            settings,
            textvariable=self.study_type_var,
            values=["Mixed", "Kanji", "Hiragana", "English", "Grammar"],
            state="readonly",
            width=12,
            style="App.TCombobox",
        )
        self.study_type_combo.grid(row=0, column=1, padx=5)
        self.study_type_combo.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        # --- Nguồn (Source / Category) ---
        ttk.Label(settings, text="Nguồn:", style="Card.TLabel").grid(row=0, column=2, padx=(12, 5))
        self.source_combo = ttk.Combobox(
            settings,
            textvariable=self.source_var,
            state="readonly",
            width=18,
            style="App.TCombobox",
        )
        self.source_combo.grid(row=0, column=3, padx=5)
        self.source_combo.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        # --- Lesson/Topic ---
        ttk.Label(settings, text="Lesson:", style="Card.TLabel").grid(row=0, column=4, padx=(12, 5))
        self.lesson_combo = ttk.Combobox(
            settings,
            textvariable=self.lesson_var,
            state="readonly",
            width=22,
            style="App.TCombobox",
        )
        self.lesson_combo.grid(row=0, column=5, padx=5)
        self.lesson_combo.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        # --- Mode ---
        ttk.Label(settings, text="Mode:", style="Card.TLabel").grid(row=0, column=6, padx=(12, 5))
        mode_combo = ttk.Combobox(
            settings,
            textvariable=self.study_mode_var,
            values=["Flashcard", "Quiz"],
            state="readonly",
            width=10,
            style="App.TCombobox",
        )
        mode_combo.grid(row=0, column=7, padx=5)
        mode_combo.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        # --- Chiều ---
        ttk.Label(settings, text="Chiều:", style="Card.TLabel").grid(row=0, column=8, padx=(12, 5))
        self.card_mode_combo = ttk.Combobox(
            settings,
            textvariable=self.card_mode_var,
            state="readonly",
            width=24,
            style="App.TCombobox",
        )
        self.card_mode_combo.grid(row=0, column=9, padx=5)
        self.card_mode_combo.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        ttk.Button(
            settings,
            text="🎲 Random",
            style="App.TButton",
            command=self.random_card,
        ).grid(row=0, column=10, padx=8)

        self.update_card_modes()

    def build_navigation(self, parent):
        nav = ttk.Frame(parent, style="App.TFrame")
        nav.pack(fill="x")

        ttk.Button(
            nav,
            text="← Trước",
            style="App.TButton",
            command=self.previous_card,
        ).pack(side="left", padx=3)

        ttk.Button(
            nav,
            text="Space · Hiện/ẩn đáp án",
            style="App.TButton",
            command=self.flip_card,
        ).pack(side="left", padx=3)

        ttk.Button(
            nav,
            text="🔊 Nghe  [A]",
            style="Success.TButton",
            command=self.speak_current,
        ).pack(side="left", padx=3)

        ttk.Button(
            nav,
            text="Tiếp →",
            style="App.TButton",
            command=self.next_card,
        ).pack(side="left", padx=3)

        ttk.Button(
            nav,
            text="↻ Reset Quiz",
            style="App.TButton",
            command=self.reset_quiz,
        ).pack(side="right", padx=3)

    # ------------------------------------------------------------------
    # LOAD
    # ------------------------------------------------------------------

    def auto_load_data(self):
        """
        Tự động load các file JSON trong thư mục data/ nếu tồn tại.
        Hỗ trợ cả vocab, grammar, kanji và English Langeek.
        """
        # Ưu tiên data đóng gói trong exe, sau đó data cạnh exe
        candidates_dirs = [
            app_base_dir() / "data",
            app_exe_dir() / "data",
        ]

        file_names = [
            "en_vocab_a1.json",
            "en_vocab_a2.json",
            "en_vocab_b1.json",
            "en_vocab_b2.json",
            "en_vocab_c1.json",
            "en_vocab_c2.json",
            "jp_a1_kanji.json",
            "jp_a1_katsudou.json",
            "jp_a1_rikai.json",
            "jp_a1_marugoto_grammar.json"
        ]

        existing = []
        for data_dir in candidates_dirs:
            for name in file_names:
                p = data_dir / name
                if p.exists():
                    existing.append(str(p))

        # bỏ trùng
        existing = list(dict.fromkeys(existing))

        if existing:
            try:
                self.vocab = load_multiple_files(existing)
                self.refresh()
                self.status_var.set(f"Đã load {len(self.vocab):,} mục từ vựng")
            except Exception as exc:
                messagebox.showerror("Load dữ liệu", f"Không thể load dữ liệu:\n\n{exc}")
        else:
            self.refresh()
            self.status_var.set("Chưa có JSON. Hãy bấm Load JSON.")

    def load_files(self):
        paths = filedialog.askopenfilenames(
            title="Chọn JSON",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )

        if not paths:
            return

        try:
            self.vocab = load_multiple_files(paths)
            self.lesson_var.set("All")
            self.current_index = 0
            self.quiz_score = 0
            self.refresh()

            self.status_var.set(
                f"Đã load {len(self.vocab):,} mục từ vựng"
            )
        except Exception as exc:
            messagebox.showerror(
                "Load JSON",
                f"Không thể load JSON:\n\n{exc}",
            )

    # ------------------------------------------------------------------
    # FILTER / MODES
    # ------------------------------------------------------------------

    def update_card_modes(self):
        """
        Cập nhật danh sách chiều học (card mode) tùy theo study_type.
        English hỗ trợ thêm Definition (lấy từ definition_en trong JSON).
        """
        study_type = self.study_type_var.get()

        if study_type == "English":
            values = [
                "English → Definition",
                "Definition → English",
                "English → Example",
                "Example → English",
            ]
            if self.card_mode_var.get() not in values:
                self.card_mode_var.set(values[0])
        elif study_type in ("Kanji", "Hiragana"):
            values = [
                "Japanese → Vietnamese",
                "Vietnamese → Japanese",
            ]
            if self.card_mode_var.get() not in values:
                self.card_mode_var.set(values[0])
        else:  # Mixed
            values = [
                "Japanese → Vietnamese",
                "Vietnamese → Japanese",
                "English → Definition",
                "Definition → English",
                "English → Example",
                "Example → English",
            ]
            if self.card_mode_var.get() not in values:
                self.card_mode_var.set(values[0])

        self.card_mode_combo.configure(values=values)

    def refresh(self):
        self.update_card_modes()

        study_type = self.study_type_var.get()

        # 1) Lọc theo Loại (study_type)
        if study_type == "English":
            filtered = [v for v in self.vocab if v.language == "English"]
        elif study_type == "Kanji":
            filtered = [
                v for v in self.vocab
                if v.language == "Japanese" and (v.type == "Kanji" or v.has_kanji)
            ]
        elif study_type == "Hiragana":
            filtered = [
                v for v in self.vocab
                if v.language == "Japanese"
                and v.type != "Kanji"
                and v.type != "Grammar"
                and not v.has_kanji
            ]
        elif study_type == "Grammar":
            filtered = [v for v in self.vocab if v.type == "Grammar"]
        else:  # Mixed
            filtered = list(self.vocab)

        # 2) Cập nhật danh sách Nguồn từ dữ liệu đã lọc
        sources = sorted(
            {v.source for v in filtered if v.source},
            key=lambda s: s.lower(),
        )
        # Hiển thị tên gọn hơn (bỏ .json)
        source_labels = ["All"] + [Path(s).stem for s in sources]
        source_map = {Path(s).stem: s for s in sources}  # label → tên file gốc

        self.source_combo.configure(values=source_labels)

        selected_source_label = self.source_var.get()
        if selected_source_label != "All" and selected_source_label not in source_labels:
            selected_source_label = "All"
            self.source_var.set("All")

        # 3) Lọc theo Nguồn
        if selected_source_label != "All":
            real_source = source_map.get(selected_source_label, selected_source_label)
            filtered = [v for v in filtered if v.source == real_source]

        # 4) Cập nhật danh sách Lesson
        lessons = sorted(
            {v.lesson for v in filtered if v.lesson},
            key=self.lesson_sort_key,
        )
        self.lesson_combo.configure(values=["All"] + lessons)

        selected_lesson = self.lesson_var.get()
        if selected_lesson != "All" and selected_lesson not in lessons:
            selected_lesson = "All"
            self.lesson_var.set("All")

        # 5) Lọc theo Lesson
        if selected_lesson != "All":
            filtered = [v for v in filtered if v.lesson == selected_lesson]

        self.filtered_vocab = filtered
        self.current_index = 0
        self.show_answer = False
        self.quiz_answered = False
        self.quiz_selected = None
        self.quiz_choices = []
        self.quiz_score = 0
        self.score_var.set("Điểm: 0")

        self.render()

    @staticmethod
    def lesson_sort_key(value: str):
        try:
            return (0, int(value))
        except ValueError:
            return (1, value.lower())

    # ------------------------------------------------------------------
    # CARD DATA
    # ------------------------------------------------------------------

    def get_question_answer(self, vocab: Vocabulary):
        """
        Trả về (question, answer) tùy theo card_mode hiện tại.

        English:
            - English → Definition / Definition → English
            - English → Example / Example → English
        Japanese:
            - Japanese → Vietnamese / Vietnamese → Japanese
        """
        mode = self.card_mode_var.get()

        if vocab.language == "English":
            if mode == "Definition → English":
                return (vocab.meaning or "(Không có định nghĩa)", vocab.word)
            if mode == "Example → English":
                return (vocab.example or "(Không có ví dụ)", vocab.word)
            if mode == "English → Example":
                return (vocab.word, vocab.example or "(Không có ví dụ)")
            # mặc định: English → Definition
            return (vocab.word, vocab.meaning or "(Không có định nghĩa)")

        if mode == "Vietnamese → Japanese":
            return vocab.meaning or "(Không có nghĩa)", vocab.word

        return vocab.word, vocab.meaning or "(Không có nghĩa)"

    def speech_text(self, vocab: Vocabulary) -> str:
        if vocab.language == "Japanese":
            # Ưu tiên reading (kana). Nếu reading lẫn romaji thì chỉ lấy phần kana.
            raw = (vocab.reading or vocab.word or "").strip()
            # Bỏ romaji sau dấu -
            kana = re.split(r"\s*[-–—]\s*", raw, maxsplit=1)[0].strip()
            # Bỏ dấu ・ trong kunyomi (た・べる → たべる) để TTS đọc mượt hơn
            kana = kana.replace("・", "")
            return kana or vocab.word
        return vocab.word

    # ------------------------------------------------------------------
    # RENDER
    # ------------------------------------------------------------------

    def clear_study_card(self):
        for widget in self.study_card.winfo_children():
            widget.destroy()

    def render(self):
        self.clear_study_card()

        if not self.filtered_vocab:
            self.render_empty()
            return

        if self.study_mode_var.get() == "Quiz":
            self.render_quiz()
        else:
            self.render_flashcard()

        percent = (
            ((self.current_index + 1) / len(self.filtered_vocab)) * 100
            if self.filtered_vocab else 0
        )
        self.progress["value"] = percent

    def render_empty(self):
        tk.Label(
            self.study_card,
            text="📚",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 50),
        ).pack(pady=(80, 15))

        tk.Label(
            self.study_card,
            text="Chưa có dữ liệu phù hợp",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 20, "bold"),
        ).pack()

        tk.Label(
            self.study_card,
            text=(
                "Hãy Load JSON hoặc đổi Loại / Lesson / Mode."
            ),
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 11),
        ).pack(pady=8)

        self.counter_var.set("0 / 0")
        self.status_var.set("Chưa có dữ liệu")

    def render_flashcard(self):
        vocab = self.filtered_vocab[self.current_index]
        question, answer = self.get_question_answer(vocab)

        top = tk.Frame(self.study_card, bg=CARD)
        top.pack(fill="x", padx=28, pady=(24, 0))

        tk.Label(
            top,
            text=vocab.language,
            bg=CARD,
            fg="#91a7ff",
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        lesson_label = (
            f"Lesson {vocab.lesson}"
            if vocab.language == "Japanese"
            else f"Topic: {vocab.lesson}"
        )

        tk.Label(
            top,
            text=lesson_label,
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="right")

        tk.Label(
            self.study_card,
            text="QUESTION",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 10, "bold"),
        ).pack(pady=(34, 8))

        tk.Label(
            self.study_card,
            text=question,
            bg=CARD,
            fg=TEXT,
            wraplength=900,
            justify="center",
            font=("Segoe UI", 34, "bold"),
        ).pack(expand=True, padx=30)

        # Japanese reading / English phonetic luôn hiện dưới question.
        if vocab.language == "Japanese" and vocab.reading:
            tk.Label(
                self.study_card,
                text=f"ひらがな  {vocab.reading}",
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 14),
            ).pack(pady=(0, 5))

        if vocab.language == "English" and vocab.phonetic:
            tk.Label(
                self.study_card,
                text=vocab.phonetic,
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 14),
            ).pack(pady=(0, 5))

        if self.show_answer:
            separator = tk.Frame(
                self.study_card,
                bg=BORDER,
                height=1,
            )
            separator.pack(fill="x", padx=100, pady=12)

            tk.Label(
                self.study_card,
                text="ANSWER",
                bg=CARD,
                fg="#7ee8be",
                font=("Segoe UI", 10, "bold"),
            ).pack()

            tk.Label(
                self.study_card,
                text=answer,
                bg=CARD,
                fg=TEXT,
                wraplength=900,
                justify="center",
                font=("Segoe UI", 21, "bold"),
            ).pack(pady=7)

            if vocab.language == "Japanese" and vocab.word != vocab.reading:
                tk.Label(
                    self.study_card,
                    text=f"Kanji: {vocab.word}",
                    bg=CARD,
                    fg=MUTED,
                    font=("Segoe UI", 12),
                ).pack(pady=2)

            if vocab.language == "English" and vocab.example:
                tk.Label(
                    self.study_card,
                    text=f"Example: {vocab.example}",
                    bg=CARD,
                    fg=MUTED,
                    wraplength=820,
                    justify="center",
                    font=("Segoe UI", 11),
                ).pack(pady=7)

        tk.Label(
            self.study_card,
            text="Space = hiện/ẩn đáp án   •   A = nghe   •   ← → = chuyển thẻ",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(pady=(10, 20))

        self.counter_var.set(
            f"{self.current_index + 1} / {len(self.filtered_vocab)}"
        )
        self.status_var.set(
            "Flashcard · Space: hiện/ẩn · A: nghe · ← →: chuyển"
        )

    # ------------------------------------------------------------------
    # QUIZ
    # ------------------------------------------------------------------

    def render_quiz(self):
        vocab = self.filtered_vocab[self.current_index]
        question, answer = self.get_question_answer(vocab)

        self.quiz_correct_answer = answer

        top = tk.Frame(self.study_card, bg=CARD)
        top.pack(fill="x", padx=28, pady=(22, 0))

        tk.Label(
            top,
            text="QUIZ",
            bg=CARD,
            fg="#91a7ff",
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        tk.Label(
            top,
            text=f"Điểm: {self.quiz_score}",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 11, "bold"),
        ).pack(side="right")

        tk.Label(
            self.study_card,
            text=question,
            bg=CARD,
            fg=TEXT,
            wraplength=880,
            justify="center",
            font=("Segoe UI", 29, "bold"),
        ).pack(pady=(34, 20))

        if vocab.language == "Japanese" and vocab.reading:
            tk.Label(
                self.study_card,
                text=f"ひらがな  {vocab.reading}",
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 13),
            ).pack(pady=(0, 12))

        if vocab.language == "English" and vocab.phonetic:
            tk.Label(
                self.study_card,
                text=vocab.phonetic,
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 13),
            ).pack(pady=(0, 12))

        if not self.quiz_choices:
            self.quiz_choices = self.generate_choices(answer)

        choices_frame = tk.Frame(self.study_card, bg=CARD)
        choices_frame.pack(fill="x", padx=100)

        for i, choice in enumerate(self.quiz_choices):
            style = "Answer.TButton"

            if self.quiz_answered:
                if choice == self.quiz_correct_answer:
                    style = "Correct.Answer.TButton"
                elif choice == self.quiz_selected:
                    style = "Wrong.Answer.TButton"

            prefix = f"{i + 1}. "
            button = ttk.Button(
                choices_frame,
                text=prefix + choice,
                style=style,
                command=lambda c=choice: self.answer_quiz(c),
            )
            button.pack(fill="x", pady=5)

        if self.quiz_answered:
            correct = self.quiz_selected == self.quiz_correct_answer

            feedback = (
                "✓ Chính xác!"
                if correct
                else f"✗ Chưa đúng — Đáp án đúng: {self.quiz_correct_answer}"
            )

            feedback_color = "#69e0ae" if correct else "#ff7d8b"

            tk.Label(
                self.study_card,
                text=feedback,
                bg=CARD,
                fg=feedback_color,
                font=("Segoe UI", 13, "bold"),
            ).pack(pady=(12, 4))

            if vocab.language == "English" and vocab.example:
                tk.Label(
                    self.study_card,
                    text=f"Example: {vocab.example}",
                    bg=CARD,
                    fg=MUTED,
                    wraplength=820,
                    justify="center",
                    font=("Segoe UI", 10),
                ).pack(pady=3)

            ttk.Button(
                self.study_card,
                text="Câu tiếp theo →  [Enter]",
                style="App.TButton",
                command=self.next_card,
            ).pack(pady=10)

        tk.Label(
            self.study_card,
            text="1–4 = chọn đáp án   •   A = nghe   •   Enter = câu tiếp theo",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(pady=(5, 18))

        self.counter_var.set(
            f"{self.current_index + 1} / {len(self.filtered_vocab)}"
        )
        self.status_var.set(
            "Quiz · chọn đáp án. Đáp án đúng/sai sẽ hiện ngay trên nút."
        )

    def generate_choices(self, correct_answer: str) -> list[str]:
        answers = []

        for v in self.filtered_vocab:
            _, answer = self.get_question_answer(v)
            if answer and answer.strip():
                answers.append(answer.strip())

        unique = list(dict.fromkeys(answers))
        wrong = [
            x for x in unique
            if x != correct_answer and x.strip()
        ]

        random.shuffle(wrong)

        choices = [correct_answer] + wrong[:3]
        random.shuffle(choices)

        return choices

    def answer_quiz(self, selected: str):
        if self.quiz_answered:
            return

        self.quiz_answered = True
        self.quiz_selected = selected

        if selected == self.quiz_correct_answer:
            self.quiz_score += 1

        self.score_var.set(f"Điểm: {self.quiz_score}")
        self.render()

    # ------------------------------------------------------------------
    # NAVIGATION
    # ------------------------------------------------------------------

    def flip_card(self):
        if self.study_mode_var.get() != "Flashcard":
            return
        if not self.filtered_vocab:
            return

        self.show_answer = not self.show_answer
        self.render()

    def next_card(self):
        if not self.filtered_vocab:
            return

        if self.study_mode_var.get() == "Quiz" and not self.quiz_answered:
            return

        self.current_index = (
            self.current_index + 1
        ) % len(self.filtered_vocab)

        self.show_answer = False
        self.quiz_answered = False
        self.quiz_selected = None
        self.quiz_choices = []

        self.render()

    def previous_card(self):
        if not self.filtered_vocab:
            return

        self.current_index = (
            self.current_index - 1
        ) % len(self.filtered_vocab)

        self.show_answer = False
        self.quiz_answered = False
        self.quiz_selected = None
        self.quiz_choices = []

        self.render()

    def random_card(self):
        if not self.filtered_vocab:
            return

        self.current_index = random.randrange(
            len(self.filtered_vocab)
        )
        self.show_answer = False
        self.quiz_answered = False
        self.quiz_selected = None
        self.quiz_choices = []

        self.render()

    def reset_quiz(self):
        self.current_index = 0
        self.quiz_score = 0
        self.quiz_answered = False
        self.quiz_selected = None
        self.quiz_choices = []
        self.show_answer = False
        self.score_var.set("Điểm: 0")
        self.render()

    # ------------------------------------------------------------------
    # SPEECH
    # ------------------------------------------------------------------

    def speak_current(self):
        if not self.filtered_vocab:
            return

        vocab = self.filtered_vocab[self.current_index]
        text = self.speech_text(vocab)

        # Online first because README yêu cầu gTTS.
        self.speech_status_var.set("🔊 Đang phát...")

        self.speech.speak(
            text,
            vocab.language,
            mode="online",
            on_done=lambda: self.after(
                0,
                lambda: self.speech_status_var.set("✓ Đã phát"),
            ),
            on_error=lambda error: self.after(
                0,
                lambda: self.speech_status_var.set(
                    "Online lỗi — hãy dùng Offline"
                ),
            ),
        )

    def speak_current_offline(self):
        if not self.filtered_vocab:
            return

        vocab = self.filtered_vocab[self.current_index]
        text = self.speech_text(vocab)

        self.speech_status_var.set("🔊 Offline...")

        self.speech.speak(
            text,
            vocab.language,
            mode="offline",
            on_done=lambda: self.after(
                0,
                lambda: self.speech_status_var.set("✓ Offline xong"),
            ),
            on_error=lambda error: self.after(
                0,
                lambda: self.speech_status_var.set(
                    "Offline lỗi: " + error[:80]
                ),
            ),
        )

    # ------------------------------------------------------------------
    # KEYBOARD
    # ------------------------------------------------------------------

    def bind_keyboard(self):
        self.bind("<space>", lambda _: self.flip_card())
        self.bind("<Right>", lambda _: self.next_card())
        self.bind("<Left>", lambda _: self.previous_card())
        self.bind("<Return>", lambda _: self.next_card())
        self.bind("<Key-a>", lambda _: self.speak_current())
        self.bind("<Key-A>", lambda _: self.speak_current())

        for i in range(4):
            self.bind(
                f"<Key-{i + 1}>",
                lambda _, idx=i: self.answer_by_number(idx),
            )

    def answer_by_number(self, index: int):
        if self.study_mode_var.get() != "Quiz":
            return
        if self.quiz_answered:
            return
        if index >= len(self.quiz_choices):
            return

        self.answer_quiz(self.quiz_choices[index])

    # ------------------------------------------------------------------
    # CENTER
    # ------------------------------------------------------------------

    def center_window(self):
        self.update_idletasks()

        width = self.winfo_width()
        height = self.winfo_height()

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)

        self.geometry(
            f"{width}x{height}+{x}+{y}"
        )


if __name__ == "__main__":
    app = VocabularyApp()
    app.mainloop()
