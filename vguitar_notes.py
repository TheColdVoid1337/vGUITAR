#!/usr/bin/env python3
"""vGUITAR Note Trainer — an offline fretboard study and quiz app.

Python 3.9+, Tkinter only. No Internet, accounts, or third-party modules.
"""

from __future__ import annotations

import random
import tkinter as tk
from dataclasses import dataclass
from typing import Optional


# Pitch classes: C=0, C#=1, ..., B=11.
NOTE_EN = ("C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B")
NOTE_RU = ("До", "До♯", "Ре", "Ре♯", "Ми", "Фа", "Фа♯", "Соль", "Соль♯", "Ля", "Ля♯", "Си")
# Display order: thin string at the top, thick string at the bottom.
STRINGS = (
    ("1", "e", "Ми", 4),
    ("2", "B", "Си", 11),
    ("3", "G", "Соль", 7),
    ("4", "D", "Ре", 2),
    ("5", "A", "Ля", 9),
    ("6", "E", "Ми", 4),
)

BG = "#0b1220"
PANEL = "#141f30"
CELL_ACTIVE = "#163349"
CELL_ACTIVE_ALT = "#19394f"
CELL_INACTIVE = "#202834"
CELL_INACTIVE_ALT = "#1b2430"
BUTTON_BG = "#26384d"
BUTTON_HOVER = "#344c67"
BORDER = "#2c4157"
TEXT = "#eef6ff"
MUTED = "#9cb1c6"
FAINT = "#68798a"
ACCENT = "#55c4f6"
GREEN = "#57d5a0"
RED = "#fb8c87"
AMBER = "#f5c178"

CELL_W = 72
TOP = 48
ROW_H = 47
BOARD_H = TOP + ROW_H * 6 + 13
FONT = "Segoe UI"


@dataclass(frozen=True)
class Question:
    row: int
    fret: int

    @property
    def pitch(self) -> int:
        return (STRINGS[self.row][3] + self.fret) % 12


def name_at(row: int, fret: int) -> str:
    return NOTE_EN[(STRINGS[row][3] + fret) % 12]


def readable_note(pc: int) -> str:
    return f"{NOTE_EN[pc]} ({NOTE_RU[pc]})"


def blend_hex(foreground: str, background: str, opacity: float) -> str:
    """Simulate opacity: Tkinter Canvas doesn't support alpha for shapes."""
    fg = tuple(int(foreground[i:i+2], 16) for i in (1, 3, 5))
    bg = tuple(int(background[i:i+2], 16) for i in (1, 3, 5))
    mixed = [round(opacity * f + (1 - opacity) * b) for f, b in zip(fg, bg)]
    return "#" + "".join(f"{n:02x}" for n in mixed)


class NoteTrainer:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("vGUITAR — Note Trainer")
        self.root.configure(bg=BG)
        self.root.minsize(850, 650)
        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        self.root.geometry(f"{min(1190, screen_w - 40)}x{min(855, screen_h - 65)}")

        self.active_strings = 2            # Thick E, then A, then D, ...
        self.active_frets = 7              # Frets 1..N, plus open string 0
        self.question_count = 10
        self.mode = "name"                # name / find
        self.phase = "study"              # study / quiz / result
        self.questions: list[Question] = []
        self.index = 0
        self.correct = 0
        self.mistakes: list[str] = []
        self.checked = False
        self.guess_fret: Optional[int] = None
        self.feedback = ""
        self.feedback_is_correct = False
        self.study_message = "Сначала повтори ноты на подсвеченных струнах, затем начни тест."

        self._create_layout()
        self._update_all()
        self.root.bind("<Return>", self._enter_key)
        self.root.bind("<Escape>", lambda event: self.show_map())
        self.root.bind_all("<MouseWheel>", self._mousewheel)
        self.root.bind_all("<Button-4>", lambda event: self.page_scroll(-1))
        self.root.bind_all("<Button-5>", lambda event: self.page_scroll(1))

    def _label(self, parent: tk.Widget, text: str, size: int = 11,
               color: str = TEXT, bold: bool = False, **kwargs) -> tk.Label:
        return tk.Label(parent, text=text, fg=color, bg=kwargs.pop("bg", PANEL),
                        font=(FONT, size, "bold" if bold else "normal"), **kwargs)

    def _button(self, parent: tk.Widget, text: str, command,
                primary: bool = False, width: Optional[int] = None) -> tk.Button:
        opts = dict(bg=ACCENT if primary else BUTTON_BG,
                    fg="#072139" if primary else TEXT,
                    activebackground="#8cddff" if primary else BUTTON_HOVER,
                    activeforeground="#072139" if primary else TEXT,
                    relief="flat", bd=0, padx=16, pady=10,
                    cursor="hand2", font=(FONT, 10, "bold"))
        if width is not None:
            opts["width"] = width
        return tk.Button(parent, text=text, command=command, **opts)

    def _create_layout(self) -> None:
        # Vertical scrolling keeps the test usable on smaller laptop screens.
        scroller = tk.Canvas(self.root, bg=BG, bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=scroller.yview)
        scroller.configure(yscrollcommand=scrollbar.set)
        scroller.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.page = scroller
        self.outer = tk.Frame(scroller, bg=BG)
        window_id = scroller.create_window((0, 0), anchor="nw", window=self.outer)
        self.outer.bind("<Configure>", lambda e: scroller.configure(scrollregion=scroller.bbox("all")))
        scroller.bind("<Configure>", lambda e: scroller.itemconfigure(window_id, width=e.width))

        header = tk.Frame(self.outer, bg=BG)
        header.pack(fill="x", padx=22, pady=(16, 12))
        self._label(header, "vGUITAR", 13, ACCENT, True, bg=BG).pack(anchor="w")
        self._label(header, "Тренажёр нот на грифе", 23, TEXT, True, bg=BG).pack(anchor="w")
        self._label(header, "Сначала изучение карты, затем проверка без подсказок. Без интернета и дополнительных библиотек.",
                    10, MUTED, bg=BG).pack(anchor="w", pady=(3, 0))

        settings = tk.Frame(self.outer, bg=PANEL, padx=16, pady=12,
                            highlightbackground=BORDER, highlightthickness=1)
        settings.pack(fill="x", padx=22, pady=(0, 12))
        line1 = tk.Frame(settings, bg=PANEL)
        line1.pack(fill="x")
        self.strings_value = self._counter(line1, "Активных струн", "strings", 1, 6)
        self.frets_value = self._counter(line1, "Активных ладов", "frets", 1, 24)
        self.questions_value = self._counter(line1, "Вопросов в тесте", "questions", 5, 100, step=5)
        line2 = tk.Frame(settings, bg=PANEL)
        line2.pack(fill="x", pady=(12, 0))
        self._label(line2, "Тип проверки", 10, MUTED).pack(side="left", padx=(0, 12))
        self.mode_buttons: dict[str, tk.Button] = {}
        for m, text in (("name", "Назови ноту"), ("find", "Найди ноту на струне")):
            btn = self._button(line2, text, lambda mode=m: self.change_mode(mode))
            btn.pack(side="left", padx=(0, 7))
            self.mode_buttons[m] = btn
        self._label(line2, "Активируем струны от толстой 6-й к тонкой 1-й.",
                    9, MUTED).pack(side="right")

        board_card = tk.Frame(self.outer, bg=PANEL, padx=16, pady=12,
                              highlightbackground=BORDER, highlightthickness=1)
        board_card.pack(fill="x", padx=22, pady=(0, 12))
        header_row = tk.Frame(board_card, bg=PANEL)
        header_row.pack(fill="x")
        self.board_heading = self._label(header_row, "КАРТА ДЛЯ ПОВТОРЕНИЯ", 11, TEXT, True)
        self.board_heading.pack(side="left")
        self.board_hint = self._label(header_row, "Полупрозрачные струны выключены", 10, MUTED)
        self.board_hint.pack(side="right")

        chart_row = tk.Frame(board_card, bg=PANEL)
        chart_row.pack(fill="x", pady=(10, 0))
        self.string_labels = tk.Canvas(chart_row, width=82, height=BOARD_H,
                                       bg=PANEL, highlightthickness=0)
        self.string_labels.pack(side="left")
        board_area = tk.Frame(chart_row, bg=PANEL)
        board_area.pack(side="left", fill="x", expand=True)
        self.board = tk.Canvas(board_area, height=BOARD_H, bg=PANEL,
                               highlightthickness=0, cursor="arrow")
        self.board.pack(fill="x")
        hbar = tk.Scrollbar(board_area, orient="horizontal", command=self.board.xview)
        hbar.pack(fill="x")
        self.board.configure(xscrollcommand=hbar.set)
        self.board.bind("<Button-1>", self._click_board)
        self._label(board_card, "0 = открытая струна · Каждая клетка = один полутон · Струны всегда показаны сверху вниз: 1 → 6",
                    9, MUTED).pack(anchor="w", pady=(8, 0))

        quiz_card = tk.Frame(self.outer, bg=PANEL, padx=16, pady=12,
                             highlightbackground=BORDER, highlightthickness=1)
        quiz_card.pack(fill="x", padx=22, pady=(0, 12))
        self.quiz_heading = self._label(quiz_card, "Подготовка", 13, TEXT, True)
        self.quiz_heading.pack(anchor="w")
        self.quiz_body = tk.Frame(quiz_card, bg=PANEL)
        self.quiz_body.pack(fill="x", pady=(8, 0))
        self.action_row = tk.Frame(quiz_card, bg=PANEL)
        self.action_row.pack(fill="x", pady=(10, 0))

        footer = tk.Frame(self.outer, bg=BG)
        footer.pack(fill="x", padx=22, pady=(0, 15))
        self._label(footer, "Стандартный строй E–A–D–G–B–E  •  ♯ = диез  •  Esc = показать карту  •  Enter = следующий вопрос",
                    9, MUTED, bg=BG).pack(anchor="w")

    def page_scroll(self, units: int) -> None:
        self.page.yview_scroll(units, "units")

    def _mousewheel(self, event: tk.Event) -> None:
        # Windows uses multiples of 120; macOS often sends smaller values.
        units = -1 if event.delta > 0 else 1
        if event.delta:
            self.page_scroll(units)

    def _counter(self, parent: tk.Widget, label: str, kind: str,
                 minimum: int, maximum: int, step: int = 1) -> tk.Label:
        box = tk.Frame(parent, bg=PANEL)
        box.pack(side="left", padx=(0, 35))
        self._label(box, label, 10, MUTED).pack(anchor="w", pady=(0, 5))
        row = tk.Frame(box, bg=PANEL)
        row.pack(anchor="w")
        self._button(row, "−", lambda: self.change_setting(kind, -step)).pack(side="left")
        value = self._label(row, "", 15, TEXT, True, width=4)
        value.pack(side="left", padx=8)
        self._button(row, "+", lambda: self.change_setting(kind, step)).pack(side="left")
        return value

    def _active(self, row: int) -> bool:
        return row >= 6 - self.active_strings

    def change_setting(self, kind: str, delta: int) -> None:
        if kind == "strings":
            self.active_strings = max(1, min(6, self.active_strings + delta))
        elif kind == "frets":
            self.active_frets = max(1, min(24, self.active_frets + delta))
        else:
            self.question_count = max(5, min(100, self.question_count + delta))
        self.show_map("Диапазон изменён. Повтори ноты в новой области и начни тест.")

    def change_mode(self, mode: str) -> None:
        self.mode = mode
        self.show_map("Режим изменён. Повтори карту перед новой проверкой.")

    def show_map(self, message: Optional[str] = None) -> None:
        self.phase = "study"
        self.checked = False
        self.guess_fret = None
        self.study_message = message or "Повтори ноты в цветной области. Когда будешь готов — начни проверку."
        self._update_all()

    def _make_questions(self) -> list[Question]:
        pool = [Question(row, fret)
                for row in range(6 - self.active_strings, 6)
                for fret in range(self.active_frets + 1)]
        if self.mode == "find":
            # With >12 frets the same pitch class reappears on a string;
            # a find-question asks for the pitch, not one arbitrary octave.
            unique: dict[tuple[int, int], Question] = {}
            for q in pool:
                unique.setdefault((q.row, q.pitch), q)
            pool = list(unique.values())
        questions: list[Question] = []
        while len(questions) < self.question_count:
            batch = pool[:]
            random.shuffle(batch)
            questions.extend(batch)
        return questions[:self.question_count]

    def start_quiz(self) -> None:
        self.questions = self._make_questions()
        self.index = 0
        self.correct = 0
        self.mistakes = []
        self.checked = False
        self.guess_fret = None
        self.feedback = ""
        self.phase = "quiz"
        self._update_all()

    def _current(self) -> Question:
        return self.questions[self.index]

    def _feedback(self, correct: bool, actual_pc: Optional[int] = None) -> None:
        q = self._current()
        self.checked = True
        self.feedback_is_correct = correct
        if correct:
            self.correct += 1
            self.feedback = f"Верно! {readable_note(q.pitch)}."
        else:
            n = STRINGS[q.row][0]
            if self.mode == "name":
                self.feedback = f"Правильный ответ: {readable_note(q.pitch)}."
                self.mistakes.append(f"{n}-я струна, лад {q.fret}: {readable_note(q.pitch)}")
            else:
                valid = [f for f in range(self.active_frets + 1)
                         if (STRINGS[q.row][3] + f) % 12 == q.pitch]
                frets = ", ".join(map(str, valid))
                self.feedback = (f"Ты выбрал {readable_note(actual_pc)}. "
                                 f"Нужная нота: {readable_note(q.pitch)} (лад: {frets}).")
                self.mistakes.append(f"{n}-я струна: найти {readable_note(q.pitch)} (лады {frets})")
        self._update_all()

    def answer_name(self, pitch_class: int) -> None:
        if self.phase != "quiz" or self.checked or self.mode != "name":
            return
        self._feedback(pitch_class == self._current().pitch)

    def _click_board(self, event: tk.Event) -> None:
        if self.phase != "quiz" or self.checked or self.mode != "find":
            return
        x = self.board.canvasx(event.x)
        fret = int(x // CELL_W)
        row = int((event.y - TOP) // ROW_H)
        if not (0 <= fret <= self.active_frets and 0 <= row < 6 and self._active(row)):
            return
        q = self._current()
        if row != q.row:
            return  # Target string is fixed; grey and other rows do not answer.
        self.guess_fret = fret
        pc = (STRINGS[row][3] + fret) % 12
        self._feedback(pc == q.pitch, actual_pc=pc)

    def next_question(self) -> None:
        if self.phase != "quiz" or not self.checked:
            return
        self.index += 1
        self.checked = False
        self.guess_fret = None
        self.feedback = ""
        if self.index >= len(self.questions):
            self.phase = "result"
        self._update_all()

    def _enter_key(self, event: tk.Event) -> None:
        if self.phase == "quiz" and self.checked:
            self.next_question()

    def _update_all(self) -> None:
        self.strings_value.config(text=str(self.active_strings))
        self.frets_value.config(text=str(self.active_frets))
        self.questions_value.config(text=str(self.question_count))
        for mode, btn in self.mode_buttons.items():
            selected = (mode == self.mode)
            btn.config(bg=ACCENT if selected else BUTTON_BG,
                       fg="#072139" if selected else TEXT)
        self._draw_board()
        self._update_quiz_ui()

    def _draw_board(self) -> None:
        self.board.delete("all")
        self.string_labels.delete("all")
        width = (self.active_frets + 1) * CELL_W
        self.board.configure(scrollregion=(0, 0, width, BOARD_H))
        self.board_heading.config(text="КАРТА ДЛЯ ПОВТОРЕНИЯ" if self.phase == "study"
                                  else "ГРИФ БЕЗ ПОДСКАЗОК")
        self.board_hint.config(text=f"{self.active_strings} из 6 струн · 0–{self.active_frets} лад")
        for fret in range(self.active_frets + 1):
            x0 = fret * CELL_W
            self.board.create_text(x0 + CELL_W / 2, 25, text=str(fret),
                                   fill=MUTED, font=(FONT, 10, "bold"))
        for row, (num, letter, ru, base_pc) in enumerate(STRINGS):
            active = self._active(row)
            y0 = TOP + row * ROW_H
            ymid = y0 + ROW_H / 2
            label_color = TEXT if active else FAINT
            self.string_labels.create_text(4, ymid - 8, text=f"{num}-я  {letter}",
                                           anchor="w", fill=label_color,
                                           font=(FONT, 11, "bold"))
            self.string_labels.create_text(4, ymid + 11, text=ru,
                                           anchor="w", fill=MUTED if active else FAINT,
                                           font=(FONT, 9))
            for fret in range(self.active_frets + 1):
                x0 = fret * CELL_W
                color = (CELL_ACTIVE if fret % 2 == 0 else CELL_ACTIVE_ALT) if active else (
                    CELL_INACTIVE if fret % 2 == 0 else CELL_INACTIVE_ALT)
                self.board.create_rectangle(x0, y0, x0 + CELL_W, y0 + ROW_H,
                                            fill=color, outline=BORDER if active else "#27313e",
                                            width=1)
                if fret == 0:
                    self.board.create_rectangle(x0 + CELL_W - 3, y0,
                                                x0 + CELL_W, y0 + ROW_H,
                                                fill=TEXT if active else FAINT, outline="")
                self.board.create_line(x0 + 7, ymid, x0 + CELL_W - 7, ymid,
                                       fill=blend_hex("#b4d5e4", color, .45 if active else .13),
                                       width=max(1, 4 - row // 2))
                pc = (base_pc + fret) % 12
                is_target = self.phase == "quiz" and self.mode == "name" and not self.checked and (
                    row == self._current().row and fret == self._current().fret)
                show_note = active and self.phase == "study"
                if active and self.phase == "quiz" and self.checked:
                    q = self._current()
                    if self.mode == "name" and (row, fret) == (q.row, q.fret):
                        show_note = True
                    if self.mode == "find" and row == q.row and pc == q.pitch:
                        show_note = True
                if show_note:
                    highlight = self.phase == "quiz" and self.checked
                    self.board.create_oval(x0 + 13, ymid - 19, x0 + CELL_W - 13, ymid + 19,
                                           fill="#236e70" if highlight else "#2b607f",
                                           outline=GREEN if highlight else "#4b9abd", width=1)
                    self.board.create_text(x0 + CELL_W / 2, ymid - 7, text=NOTE_EN[pc],
                                           fill=TEXT, font=(FONT, 12, "bold"))
                    self.board.create_text(x0 + CELL_W / 2, ymid + 10, text=NOTE_RU[pc],
                                           fill="#c8e3ef", font=(FONT, 8))
                elif is_target:
                    self.board.create_oval(x0 + 14, ymid - 18, x0 + CELL_W - 14, ymid + 18,
                                           fill="#245879", outline=ACCENT, width=2)
                    self.board.create_text(x0 + CELL_W / 2, ymid, text="?",
                                           fill=TEXT, font=(FONT, 17, "bold"))
                if active and self.phase == "quiz" and self.mode == "find":
                    q = self._current()
                    if row == q.row and not self.checked:
                        self.board.create_rectangle(x0 + 3, y0 + 3, x0 + CELL_W - 3,
                                                    y0 + ROW_H - 3, outline="#4188ad", width=2)
                    if self.checked and row == q.row and fret == self.guess_fret:
                        self.board.create_rectangle(x0 + 2, y0 + 2, x0 + CELL_W - 2,
                                                    y0 + ROW_H - 2,
                                                    outline=GREEN if self.feedback_is_correct else RED,
                                                    width=3)
        if self.phase == "quiz":
            q = self._current()
            x0 = q.fret * CELL_W
            if self.mode == "name":
                self.board.xview_moveto(max(0, x0 - 2 * CELL_W) / max(width, 1))
            # In 'find' mode don't reveal the target fret by auto-scrolling.

    def _clear(self, parent: tk.Widget) -> None:
        for child in parent.winfo_children():
            child.destroy()

    def _update_quiz_ui(self) -> None:
        self._clear(self.quiz_body)
        self._clear(self.action_row)
        if self.phase == "study":
            self.quiz_heading.config(text="Сначала изучи карту")
            self._label(self.quiz_body, self.study_message, 11, TEXT,
                        wraplength=950, justify="left").pack(anchor="w")
            self._label(self.quiz_body,
                        "Подписаны только активные струны и лады. Нажми «Начать тест», чтобы убрать все названия нот.",
                        10, MUTED, wraplength=950, justify="left").pack(anchor="w", pady=(5, 0))
            self._button(self.action_row, "Начать тест  →", self.start_quiz, primary=True).pack(side="left")
        elif self.phase == "quiz":
            q = self._current()
            string_name = f"{STRINGS[q.row][0]}-я струна ({STRINGS[q.row][1]})"
            self.quiz_heading.config(text=f"Вопрос {self.index + 1} / {len(self.questions)}    ·    Правильно: {self.correct}")
            if self.mode == "name":
                question = f"Какая нота на {string_name}, {q.fret}-й лад?" if q.fret else (
                    f"Какая нота на {string_name}, открытая струна?")
                self._label(self.quiz_body, question, 13, TEXT, True).pack(anchor="w", pady=(0, 10))
                answers = tk.Frame(self.quiz_body, bg=PANEL)
                answers.pack(fill="x")
                for pc in range(12):
                    btn = self._button(answers, f"{NOTE_EN[pc]}  {NOTE_RU[pc]}",
                                       lambda n=pc: self.answer_name(n))
                    btn.grid(row=pc // 6, column=pc % 6, sticky="ew", padx=3, pady=3)
                    answers.columnconfigure(pc % 6, weight=1)
                    if self.checked:
                        if pc == q.pitch:
                            btn.configure(bg="#27765e", fg=TEXT, activebackground="#27765e")
                        else:
                            btn.configure(state="disabled", disabledforeground=FAINT)
            else:
                self._label(self.quiz_body, f"Найди {readable_note(q.pitch)} на {string_name}.",
                            13, TEXT, True).pack(anchor="w")
                self._label(self.quiz_body, "Щёлкни по нужному ладу этой струны на схеме выше. Можно выбрать открытую струну (0).",
                            10, MUTED).pack(anchor="w", pady=(6, 0))
            if self.checked:
                self._label(self.action_row, ("✓ " if self.feedback_is_correct else "✕ ") + self.feedback,
                            10, GREEN if self.feedback_is_correct else AMBER,
                            wraplength=820, justify="left").pack(side="left", fill="x", expand=True)
                label = "Показать итог  →" if self.index + 1 == len(self.questions) else "Следующий вопрос  →"
                self._button(self.action_row, label, self.next_question, primary=True).pack(side="right", padx=(12, 0))
            else:
                self._button(self.action_row, "Показать учебную карту", self.show_map).pack(side="left")
        else:
            total = len(self.questions)
            self.quiz_heading.config(text=f"Тест завершён  ·  {self.correct} / {total}")
            if self.mistakes:
                self._label(self.quiz_body, "Стоит повторить:", 11, AMBER, True).pack(anchor="w")
                for mistake in self.mistakes[:8]:
                    self._label(self.quiz_body, "• " + mistake, 10, TEXT).pack(anchor="w", pady=2)
                if len(self.mistakes) > 8:
                    self._label(self.quiz_body, f"…и ещё {len(self.mistakes) - 8} ошибок.",
                                10, MUTED).pack(anchor="w")
            else:
                self._label(self.quiz_body, "Все ответы правильные. Попробуй больше ладов или струн!",
                            12, GREEN, True).pack(anchor="w")
            self._button(self.action_row, "Повторить карту", self.show_map).pack(side="left", padx=(0, 8))
            self._button(self.action_row, "Новый тест  →", self.start_quiz, primary=True).pack(side="left")


def main() -> None:
    root = tk.Tk()
    NoteTrainer(root)
    root.mainloop()


if __name__ == "__main__":
    main()