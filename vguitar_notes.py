#!/usr/bin/env python3
"""vGUITAR Note Trainer — an offline fretboard study and quiz app.

Python 3.9+, Tkinter only. No Internet, accounts, or third-party modules.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import math
import time
from datetime import datetime, timezone
from uuid import uuid4
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from typing import Optional

from vguitar_audio import AudioPlayer
from vguitar_storage import (
    ensure_dirs, preferences_path, read_preferences, save_preferences,
    save_run, list_runs, run_statistics, export_runs_for_llm,
)


# Pitch classes: C=0, C#=1, ..., B=11.
NOTE_EN = ("C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B")
NOTE_RU = ("До", "До♯", "Ре", "Ре♯", "Ми", "Фа", "Фа♯", "Соль", "Соль♯", "Ля", "Ля♯", "Си")
NOTE_EN_FLAT = ("C", "D♭", "D", "E♭", "E", "F", "G♭", "G", "A♭", "A", "B♭", "B")
NOTE_RU_FLAT = ("До", "Ре♭", "Ре", "Ми♭", "Ми", "Фа", "Соль♭", "Соль", "Ля♭", "Ля", "Си♭", "Си")
# Display order: thin string at the top, thick string at the bottom.
# Tuning data is MIDI note numbers (thin 1st -> thick 6th), not pitch classes.
# This preserves the correct pitch/octave for audible string playback.
STANDARD_MIDI = (64, 59, 55, 50, 45, 40)
TUNINGS = {
    "Standard (E A D G B E)": STANDARD_MIDI,
    "E♭ Standard (E♭ A♭ D♭ G♭ B♭ E♭)": (63, 58, 54, 49, 44, 39),
    "D Standard (D G C F A D)": (62, 57, 53, 48, 43, 38),
    "C Standard (C F B♭ E♭ G C)": (60, 55, 51, 46, 41, 36),
    "Drop D (D A D G B E)": (64, 59, 55, 50, 45, 38),
    "Drop C (C G C F A D)": (62, 57, 53, 48, 43, 36),
    "Open G (D G D G B D)": (62, 59, 55, 50, 43, 38),
    "Open D (D A D F♯ A D)": (62, 57, 54, 50, 45, 38),
}
CUSTOM_TUNING = "Свой строй"
STRINGS = (
    ("1", "e", "Ми", 4),
    ("2", "B", "Си", 11),
    ("3", "G", "Соль", 7),
    ("4", "D", "Ре", 2),
    ("5", "A", "Ля", 9),
    ("6", "E", "Ми", 4),
)


def pitch_at(tuning: tuple[int, ...], row: int, fret: int) -> int:
    if len(tuning) != 6 or not 0 <= row < 6 or not 0 <= fret <= 24:
        raise ValueError("Invalid string/fret/tuning")
    return tuning[row] + fret


def note_at(tuning: tuple[int, ...], row: int, fret: int) -> str:
    return NOTE_EN[pitch_at(tuning, row, fret) % 12]


def midi_label(midi: int) -> str:
    pc, octave = midi % 12, midi // 12 - 1
    sharp, flat = NOTE_EN[pc], NOTE_EN_FLAT[pc]
    return f"{sharp}{octave}" if sharp == flat else f"{sharp}{octave} / {flat}{octave}"


def settings_path() -> Path:
    return preferences_path()


def legacy_settings_path() -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home() / ".config"))) if os.name == "nt" else Path.home() / ".config"
    return base / "vGUITAR" / "note_trainer_settings.json"


def read_settings(path: Path) -> tuple[str, tuple[int, ...], int]:
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
        name = settings.get("preset", "Standard (E A D G B E)")
        midi = tuple(settings.get("tuning_midi", STANDARD_MIDI))
        volume = int(settings.get("volume", 65))
        if (name not in TUNINGS and name != CUSTOM_TUNING) or len(midi) != 6 or any(
                type(n) is not int or not 24 <= n <= 96 for n in midi):
            raise ValueError("Invalid tuning")
        if name in TUNINGS:
            midi = TUNINGS[name]
        return name, midi, max(0, min(100, volume))
    except (OSError, ValueError, TypeError, AttributeError):
        return next(iter(TUNINGS)), STANDARD_MIDI, 65


def write_settings(path: Path, name: str, midi: tuple[int, ...], volume: int) -> None:
    if (name not in TUNINGS and name != CUSTOM_TUNING) or len(midi) != 6 or any(
            type(n) is not int or not 24 <= n <= 96 for n in midi):
        raise ValueError("Invalid tuning")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({"schema_version": 1, "preset": name, "tuning_midi": list(midi),
                                "volume": int(max(0, min(100, volume)))}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    temp.replace(path)


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

CELL_W = 66
TOP = 24
ROW_H = 31
BOARD_H = TOP + ROW_H * 6 + 6
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


def readable_note(pc: int, prefer_flats: bool = False) -> str:
    return f"{(NOTE_EN_FLAT if prefer_flats else NOTE_EN)[pc]} ({(NOTE_RU_FLAT if prefer_flats else NOTE_RU)[pc]})"


def blend_hex(foreground: str, background: str, opacity: float) -> str:
    """Simulate opacity: Tkinter Canvas doesn't support alpha for shapes."""
    fg = tuple(int(foreground[i:i+2], 16) for i in (1, 3, 5))
    bg = tuple(int(background[i:i+2], 16) for i in (1, 3, 5))
    mixed = [round(opacity * f + (1 - opacity) * b) for f, b in zip(fg, bg)]
    return "#" + "".join(f"{n:02x}" for n in mixed)


class Tooltip:
    """Compact delayed hover help; never steals focus."""
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget, self.text = widget, text
        self.popup = None
        self.timer = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, event=None) -> None:
        self._hide()
        self.timer = self.widget.after(550, self._show)

    def _show(self) -> None:
        self.timer = None
        if not self.widget.winfo_exists():
            return
        self.popup = tk.Toplevel(self.widget)
        self.popup.wm_overrideredirect(True)
        self.popup.attributes("-topmost", True)
        label = tk.Label(self.popup, text=self.text, font=(FONT, 9), fg=TEXT, bg="#26384d",
                         justify="left", wraplength=300, padx=10, pady=7, relief="solid", bd=1)
        label.pack()
        self.popup.update_idletasks()
        x = min(self.widget.winfo_pointerx() + 14, self.widget.winfo_screenwidth() - self.popup.winfo_reqwidth() - 8)
        y = min(self.widget.winfo_pointery() + 18, self.widget.winfo_screenheight() - self.popup.winfo_reqheight() - 8)
        self.popup.wm_geometry(f"+{max(0,x)}+{max(0,y)}")

    def _hide(self, event=None) -> None:
        if self.timer is not None:
            try:
                self.widget.after_cancel(self.timer)
            except tk.TclError:
                pass
            self.timer = None
        if self.popup is not None:
            self.popup.destroy()
            self.popup = None


class NoteTrainer:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("vGUITAR — Note Trainer")
        self.root.configure(bg=BG)
        self.root.minsize(680, 575)
        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        self.root.geometry(f"{max(680, min(1070, screen_w - 70))}x{max(575, min(790, screen_h - 75))}")

        self.storage_warning = ""
        try:
            ensure_dirs()
        except OSError as exc:
            self.storage_warning = f"Локальные папки недоступны: {exc}"
        if not settings_path().exists() and legacy_settings_path().exists():
            # One-time migration from v0.2's OS configuration directory.
            prior_name, prior_midi, prior_volume = read_settings(legacy_settings_path())
            try:
                write_settings(settings_path(), prior_name, prior_midi, prior_volume)
            except OSError:
                pass
        self.preset_name, self.tuning, initial_volume = read_settings(settings_path())
        lesson = read_preferences().get("lesson", {})
        if not isinstance(lesson, dict):
            lesson = {}
        self.audio = AudioPlayer(initial_volume)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.active_strings = self._bounded(lesson.get("active_strings", 2), 1, 6, 2)
        self.active_frets = self._bounded(lesson.get("active_frets", 7), 1, 24, 7)
        self.question_count = self._bounded(lesson.get("question_count", 10), 5, 100, 10)
        self.study_seconds = self._bounded(lesson.get("study_seconds", 60), 10, 300, 60)
        self.mode = lesson.get("mode") if lesson.get("mode") in ("name", "find") else "name"
        self.answer_layout = lesson.get("answer_layout") if lesson.get("answer_layout") in ("rows", "circle") else "rows"
        self.phase = "ready"              # ready / study / quiz / result
        self.study_deadline: Optional[float] = None
        self.study_after_id: Optional[str] = None
        self.study_left = self.study_seconds
        self.question_started: Optional[float] = None
        self.run_started_at = ""
        self.run_id = ""
        self.responses: list[dict] = []
        self.current_run: Optional[dict] = None
        self.questions: list[Question] = []
        self.index = 0
        self.correct = 0
        self.mistakes: list[str] = []
        self.checked = False
        self.guess_fret: Optional[int] = None
        self.feedback = ""
        self.feedback_is_correct = False
        self.study_message = "Выбери область и запусти повторение."
        self._chosen_pc: Optional[int] = None
        self.cell_width = CELL_W
        self.answer_wheel_regions: dict[int, tuple[float, float, float]] = {}

        self._create_layout()
        self._update_all()
        self.root.bind("<Return>", self._enter_key)
        self.root.bind("<Escape>", lambda event: self.show_map())
        self.root.bind_all("<MouseWheel>", self._mousewheel)
        self.root.bind_all("<Button-4>", lambda event: self.page_scroll(-1))
        self.root.bind_all("<Button-5>", lambda event: self.page_scroll(1))
        self._save_preferences()

    @staticmethod
    def _bounded(value: object, minimum: int, maximum: int, fallback: int) -> int:
        try:
            return max(minimum, min(maximum, int(value)))
        except (ValueError, TypeError, OverflowError):
            return fallback

    def _save_preferences(self) -> None:
        try:
            save_preferences({
                "schema_version": 2,
                "preset": self.preset_name,
                "tuning_midi": list(self.tuning),
                "volume": self.audio.volume,
                "lesson": {
                    "active_strings": self.active_strings,
                    "active_frets": self.active_frets,
                    "question_count": self.question_count,
                    "study_seconds": self.study_seconds,
                    "mode": self.mode,
                    "answer_layout": self.answer_layout,
                },
            })
        except OSError as exc:
            self.storage_warning = f"Не удалось сохранить настройки: {exc}"

    def _cancel_study_timer(self) -> None:
        if self.study_after_id is not None:
            try:
                self.root.after_cancel(self.study_after_id)
            except tk.TclError:
                pass
            self.study_after_id = None
        self.study_deadline = None

    def _copy_text(self, data: str) -> None:
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(data)
            self.root.update()  # clipboard survives app exit on Windows
            self._set_status("Скопировано! Вставь Ctrl+V в чат.")
        except tk.TclError as exc:
            messagebox.showerror("Буфер обмена", str(exc), parent=self.root)

    def _set_status(self, text: str) -> None:
        self.status_label.config(text=text)

    def _label(self, parent: tk.Widget, text: str, size: int = 11,
               color: str = TEXT, bold: bool = False, **kwargs) -> tk.Label:
        return tk.Label(parent, text=text, fg=color, bg=kwargs.pop("bg", PANEL),
                        font=(FONT, size, "bold" if bold else "normal"), **kwargs)

    def _button(self, parent: tk.Widget, text: str, command,
                primary: bool = False, width: Optional[int] = None, compact: bool = False) -> tk.Button:
        opts = dict(bg=ACCENT if primary else BUTTON_BG,
                    fg="#072139" if primary else TEXT,
                    activebackground="#8cddff" if primary else BUTTON_HOVER,
                    activeforeground="#072139" if primary else TEXT,
                    relief="flat", bd=0, padx=8 if compact else 16, pady=3 if compact else 10,
                    cursor="hand2", font=(FONT, 9 if compact else 10, "bold"))
        if width is not None:
            opts["width"] = width
        return tk.Button(parent, text=text, command=command, **opts)

    def _create_layout(self) -> None:
        # A single screen: board and answer area share the available height.
        self.outer = tk.Frame(self.root, bg=BG)
        self.outer.pack(fill="both", expand=True)
        self.page = None  # Legacy vertical scrolling deliberately removed.

        menu = tk.Menu(self.root)
        settings_menu = tk.Menu(menu, tearoff=False)
        settings_menu.add_command(label="Строй и звук…", command=self.open_settings)
        menu.add_cascade(label="Настройки", menu=settings_menu)
        menu.add_command(label="История", command=self.open_history)
        menu.add_command(label="Справка", command=self.open_help)
        self.root.config(menu=menu)

        toolbar = tk.Frame(self.outer, bg=PANEL, padx=9, pady=6,
                           highlightbackground=BORDER, highlightthickness=1)
        toolbar.pack(fill="x", padx=10, pady=(7, 5))
        self.toolbar = toolbar
        self.brand = tk.Frame(toolbar, bg=PANEL)
        self._label(self.brand, "vGUITAR", 14, ACCENT, True).pack(side="left")
        self._label(self.brand, "  NOTES", 9, MUTED, True).pack(side="left")
        self.counter_strip = tk.Frame(toolbar, bg=PANEL)
        self.strings_value = self._counter(self.counter_strip, "Струны", "strings", 1, 6)
        self.frets_value = self._counter(self.counter_strip, "Лады", "frets", 1, 24)
        self.questions_value = self._counter(self.counter_strip, "Вопросы", "questions", 5, 100, step=5)
        self.study_value = self._counter(self.counter_strip, "Повтор", "study", 10, 300, step=10)
        self.mode_strip = tk.Frame(toolbar, bg=PANEL)
        self.mode_buttons: dict[str, tk.Button] = {}
        for mode, title in (("name", "Назвать"), ("find", "Найти")):
            btn = self._button(self.mode_strip, title, lambda m=mode: self.change_mode(m), compact=True)
            btn.pack(side="left", padx=(0, 3))
            self.mode_buttons[mode] = btn
            Tooltip(btn, "Назвать ноту на указанном ладу." if mode == "name" else
                    "Найти указанную ноту на нужной струне.")
        self.history_button = self._button(toolbar, "История", self.open_history, compact=True)
        Tooltip(self.history_button, "Результаты прошлых тестов и экспорт выбранных запусков.")
        self._toolbar_layout = None
        self._layout_toolbar(self.root.winfo_width())

        self.content_area = tk.Frame(self.outer, bg=BG)
        self.content_area.pack(fill="both", expand=True, padx=12, pady=(0, 5))
        self._responsive_orientation = None
        board_card = tk.Frame(self.content_area, bg=PANEL, padx=9, pady=5,
                              highlightbackground=BORDER, highlightthickness=1)
        self.board_card = board_card
        header_row = tk.Frame(board_card, bg=PANEL)
        header_row.pack(fill="x")
        self.board_heading = self._label(header_row, "ГРИФ", 10, TEXT, True)
        self.board_heading.pack(side="left")
        self.board_hint = self._label(header_row, "", 9, MUTED)
        self.board_hint.pack(side="right")
        chart_row = tk.Frame(board_card, bg=PANEL)
        chart_row.pack(fill="x", pady=(3, 0))
        self.string_labels = tk.Canvas(chart_row, width=72, height=BOARD_H,
                                       bg=PANEL, highlightthickness=0)
        self.string_labels.pack(side="left")
        board_area = tk.Frame(chart_row, bg=PANEL)
        board_area.pack(side="left", fill="x", expand=True)
        self.board = tk.Canvas(board_area, height=BOARD_H, bg=PANEL,
                               highlightthickness=0, cursor="arrow")
        self.board.pack(fill="x")
        hbar = tk.Scrollbar(board_area, orient="horizontal", command=self.board.xview,
                            width=12)
        hbar.pack(fill="x")
        self.board.configure(xscrollcommand=hbar.set)
        self.board.bind("<Button-1>", self._click_board)
        self.board.bind("<Configure>", self._board_resized)
        Tooltip(self.board, "0 — открытая струна. В повторении щёлкни по ноте, чтобы услышать её.")

        quiz_card = tk.Frame(self.content_area, bg=PANEL, padx=9, pady=5,
                             highlightbackground=BORDER, highlightthickness=1)
        self.quiz_card = quiz_card
        quiz_header = tk.Frame(quiz_card, bg=PANEL)
        quiz_header.pack(fill="x")
        self.quiz_heading = self._label(quiz_header, "Подготовка", 11, TEXT, True)
        self.quiz_heading.pack(side="left")
        layout_box = tk.Frame(quiz_header, bg=PANEL)
        layout_box.pack(side="right")
        self.answer_mode_buttons: dict[str, tk.Button] = {}
        for layout, title in (("rows", "Ряды"), ("circle", "Круг")):
            btn = self._button(layout_box, title, lambda name=layout: self.change_answer_layout(name), compact=True)
            btn.pack(side="left", padx=(4, 0))
            self.answer_mode_buttons[layout] = btn
            Tooltip(btn, "Расположение нот-ответов. Для режима «Назвать ноту».")
        self.answer_layout_frame = layout_box
        self.quiz_body = tk.Frame(quiz_card, bg=PANEL)
        self.quiz_body.pack(fill="both", expand=True, pady=(3, 0))
        self.action_row = tk.Frame(quiz_card, bg=PANEL)
        self.action_row.pack(fill="x", pady=(4, 0))

        footer = tk.Frame(self.outer, bg=BG)
        footer.pack(fill="x", padx=12, pady=(0, 3))
        self.footer_label = self._label(footer, "", 9, MUTED, bg=BG)
        self.footer_label.pack(side="left")
        self.status_label = self._label(footer, "", 9, ACCENT, bg=BG)
        self.status_label.pack(side="right")
        self._layout_content()
        self.root.bind("<Configure>", self._resize_main, add="+")

    def _resize_main(self, event) -> None:
        if event.widget is self.root:
            self._layout_toolbar(event.width)
            self._layout_content()

    def _layout_toolbar(self, width: int) -> None:
        # Fully single-row on wide windows; compact 2-3 rows on narrow ones.
        mode = "wide" if width >= 940 else "medium" if width >= 790 else "small"
        if mode == self._toolbar_layout:
            return
        self._toolbar_layout = mode
        for widget in (self.brand, self.counter_strip, self.mode_strip, self.history_button):
            widget.grid_forget()
        for row in range(3):
            self.toolbar.grid_rowconfigure(row, weight=0)
        for col in range(4):
            self.toolbar.grid_columnconfigure(col, weight=0)
        if mode == "wide":
            self.toolbar.grid_columnconfigure(3, weight=1)
            self.brand.grid(row=0, column=0, sticky="w", padx=(0, 15))
            self.counter_strip.grid(row=0, column=1, sticky="w", padx=(0, 12))
            self.mode_strip.grid(row=0, column=2, sticky="w")
            self.history_button.grid(row=0, column=3, sticky="e")
        elif mode == "medium":
            self.toolbar.grid_columnconfigure(1, weight=1)
            self.brand.grid(row=0, column=0, sticky="w")
            self.mode_strip.grid(row=0, column=1, sticky="e", padx=(10, 8))
            self.history_button.grid(row=0, column=2, sticky="e")
            self.counter_strip.grid(row=1, column=0, columnspan=3, sticky="w", pady=(3, 0))
        else:
            self.toolbar.grid_columnconfigure(1, weight=1)
            self.brand.grid(row=0, column=0, sticky="w")
            self.mode_strip.grid(row=0, column=1, sticky="e")
            self.history_button.grid(row=0, column=2, sticky="e", padx=(6, 0))
            self.counter_strip.grid(row=1, column=0, columnspan=3, sticky="w", pady=(3, 0))

    def _layout_content(self) -> None:
        width, height = self.root.winfo_width(), self.root.winfo_height()
        orientation = "side" if height < 710 or width >= 1250 else "stack"
        if orientation == self._responsive_orientation:
            return
        self._responsive_orientation = orientation
        area = self.content_area
        self.board_card.grid_forget()
        self.quiz_card.grid_forget()
        for index in (0, 1):
            area.grid_rowconfigure(index, weight=0, minsize=0)
            # Unset the former uniform group: it otherwise reserves an invisible
            # second column and leaves a huge blank area on the right.
            area.grid_columnconfigure(index, weight=0, minsize=0, uniform="")
        if orientation == "side":
            area.grid_columnconfigure(0, weight=1)
            area.grid_columnconfigure(1, weight=1)
            area.grid_rowconfigure(0, weight=1)
            self.board_card.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
            self.quiz_card.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        else:
            area.grid_columnconfigure(0, weight=1)
            area.grid_rowconfigure(1, weight=1)
            self.board_card.grid(row=0, column=0, sticky="ew", pady=(0, 5))
            self.quiz_card.grid(row=1, column=0, sticky="nsew")

    def _on_close(self) -> None:
        self._cancel_study_timer()
        self._save_preferences()
        self.audio.close()
        self.root.destroy()

    def open_settings(self) -> None:
        if getattr(self, "_settings_window", None) is not None and self._settings_window.winfo_exists():
            self._settings_window.lift()
            self._settings_window.focus_force()
            return
        window = tk.Toplevel(self.root, bg=BG)
        self._settings_window = window
        window.title("vGUITAR — Строй и звук")
        window.geometry("550x690")
        window.minsize(500, 640)
        window.transient(self.root)
        window.grab_set()
        frame = tk.Frame(window, bg=PANEL, padx=20, pady=18)
        frame.pack(fill="both", expand=True, padx=14, pady=14)
        self._label(frame, "НАСТРОЙКИ", 16, TEXT, True).pack(anchor="w")
        self._label(frame, "Строй влияет на карту, вопросы и высоту звука.", 10, MUTED).pack(anchor="w", pady=(4, 12))

        chosen_preset = tk.StringVar(value=self.preset_name)
        self._label(frame, "Готовый строй", 10, MUTED).pack(anchor="w")
        preset_combo = ttk.Combobox(frame, state="readonly", textvariable=chosen_preset,
                                   values=[*TUNINGS, CUSTOM_TUNING], width=48)
        preset_combo.pack(fill="x", pady=(4, 12))
        self._label(frame, "Открытые струны (сверху тонкая 1-я, снизу толстая 6-я)", 10, MUTED).pack(anchor="w")
        note_choices = [midi_label(n) for n in range(24, 97)]
        midi_values = [tk.StringVar(value=midi_label(n)) for n in self.tuning]
        string_boxes = []
        string_frame = tk.Frame(frame, bg=PANEL)
        string_frame.pack(fill="x", pady=(7, 10))
        for i in range(6):
            line = tk.Frame(string_frame, bg=PANEL)
            line.pack(fill="x", pady=2)
            self._label(line, f"{i+1}-я струна", 10, TEXT, width=13, anchor="w").pack(side="left")
            combo = ttk.Combobox(line, state="readonly", width=15, values=note_choices,
                                 textvariable=midi_values[i])
            combo.pack(side="left", padx=10)
            string_boxes.append(combo)

        updating = False
        def preset_changed(event=None):
            nonlocal updating
            if chosen_preset.get() in TUNINGS:
                updating = True
                for variable, midi in zip(midi_values, TUNINGS[chosen_preset.get()]):
                    variable.set(midi_label(midi))
                updating = False

        def note_changed(event=None):
            if not updating:
                chosen_preset.set(CUSTOM_TUNING)

        preset_combo.bind("<<ComboboxSelected>>", preset_changed)
        for combo in string_boxes:
            combo.bind("<<ComboboxSelected>>", note_changed)

        volume = tk.IntVar(value=self.audio.volume)
        volume_line = tk.Frame(frame, bg=PANEL)
        volume_line.pack(fill="x", pady=(12, 5))
        self._label(volume_line, "Громкость", 11, TEXT, True).pack(side="left")
        volume_label = self._label(volume_line, str(volume.get()) + "%", 11, ACCENT)
        volume_label.pack(side="right")
        def volume_changed(value):
            volume_label.config(text=f"{round(float(value))}%")
        tk.Scale(frame, from_=0, to=100, resolution=1, orient="horizontal",
                 variable=volume, command=volume_changed,
                 bg=PANEL, fg=TEXT, troughcolor=CELL_ACTIVE, highlightthickness=0,
                 activebackground=ACCENT, length=430).pack(fill="x")
        self._label(frame, "Выход: " + self.audio.host_api_name + " · " + self.audio.device_name,
                    9, MUTED, wraplength=485, justify="left").pack(anchor="w")
        if not self.audio.available:
            self._label(frame, "WASAPI недоступен: запусти RUN.bat для установки sounddevice.",
                        9, AMBER).pack(anchor="w")

        bottom = tk.Frame(frame, bg=PANEL)
        bottom.pack(side="bottom", fill="x", pady=(12, 0))
        def apply_settings():
            new_tuning = tuple(note_choices.index(v.get()) + 24 for v in midi_values)
            new_preset = chosen_preset.get()
            new_volume = volume.get()
            try:
                write_settings(settings_path(), new_preset, new_tuning, new_volume)
            except OSError as exc:
                # Keep UI functional even when user config folder is read-only.
                self.study_message = f"Настройки действуют в этом запуске, но не сохранены: {exc}"
            changed = new_tuning != self.tuning
            self.preset_name, self.tuning = new_preset, new_tuning
            self.audio.volume = new_volume
            self._save_preferences()
            if changed:
                self.show_map("Строй изменён. Изучи обновлённые ноты перед тестом.")
            else:
                self._update_all()
            window.destroy()

        self._button(bottom, "Сохранить", apply_settings, primary=True).pack(side="right")
        self._button(bottom, "Отмена", window.destroy).pack(side="right", padx=8)
        test_btn = self._button(bottom, "♫ Тест", lambda: self._preview_audio(
            note_choices.index(midi_values[5].get()) + 24, volume.get()), compact=True)
        test_btn.pack(side="left")
        Tooltip(test_btn, "Сыграть шестую струну через WASAPI; затем показать состояние вывода.")
        log_btn = self._button(bottom, "Лог звука", self._copy_audio_diagnostic, compact=True)
        log_btn.pack(side="left", padx=(5, 0))
        Tooltip(log_btn, "Скопировать состояние аудиосистемы для разбора проблем.")

    def _copy_audio_diagnostic(self) -> None:
        self._copy_text("vGUITAR_AUDIO_DIAGNOSTIC\n" + self.audio.diagnostic())

    def _preview_audio(self, midi_note: int, volume: int) -> None:
        previous = self.audio.volume
        self.audio.volume = volume
        started = self.audio.play(midi_note)
        self.audio.volume = previous
        if not started:
            messagebox.showwarning("Проверка звука", self.audio.diagnostic(), parent=self._settings_window)
            return
        # The worker may report a native device error after play() returns.
        def report() -> None:
            window = getattr(self, "_settings_window", None)
            if window is None or not window.winfo_exists():
                return
            status = self.audio.diagnostic()
            lead = ("Плеер сообщил об ошибке. Нажми «Лог звука» и пришли его в чат."
                    if self.audio.last_result == "error"
                    else "Если звук не слышен, проверь микшер Windows и устройство вывода, затем пришли «Лог звука».")
            messagebox.showinfo("Проверка звука", lead + "\n\n" + status, parent=window)
        self.root.after(2500, report)

    def page_scroll(self, units: int) -> None:
        return  # The main window deliberately has no vertical scrolling.

    def _mousewheel(self, event: tk.Event) -> None:
        return  # The board uses its own horizontal scrollbar.

    def _counter(self, parent: tk.Widget, label: str, kind: str,
                 minimum: int, maximum: int, step: int = 1) -> tk.Label:
        box = tk.Frame(parent, bg=PANEL)
        box.pack(side="left", padx=(0, 7))
        row = tk.Frame(box, bg=PANEL)
        row.pack(anchor="w")
        self._label(row, label, 9, MUTED).pack(side="left", padx=(0, 3))
        self._button(row, "−", lambda: self.change_setting(kind, -step), compact=True).pack(side="left")
        value = self._label(row, "", 10, TEXT, True, width=2)
        value.pack(side="left", padx=1)
        self._button(row, "+", lambda: self.change_setting(kind, step), compact=True).pack(side="left")
        Tooltip(box, {"strings": "Струны активируются от толстой шестой к тонкой первой.",
                      "frets": "Диапазон 0–N, включая открытую струну.",
                      "questions": "Число заданий в одном тесте.",
                      "study": "Сколько секунд показывать ноты до теста."}[kind])
        return value

    def change_answer_layout(self, layout: str) -> None:
        if layout not in ("rows", "circle"):
            raise ValueError("Unknown note answer layout")
        self.answer_layout = layout
        self._save_preferences()
        self._update_answer_layout_buttons()
        self._update_quiz_ui()

    def _update_answer_layout_buttons(self) -> None:
        for name, button in self.answer_mode_buttons.items():
            active = name == self.answer_layout
            button.config(bg=ACCENT if active else BUTTON_BG,
                          fg="#072139" if active else TEXT)

    def _active(self, row: int) -> bool:
        return row >= 6 - self.active_strings

    def change_setting(self, kind: str, delta: int) -> None:
        if kind == "strings":
            self.active_strings = max(1, min(6, self.active_strings + delta))
        elif kind == "frets":
            self.active_frets = max(1, min(24, self.active_frets + delta))
        elif kind == "questions":
            self.question_count = max(5, min(100, self.question_count + delta))
        elif kind == "study":
            self.study_seconds = max(10, min(300, self.study_seconds + delta))
        self._save_preferences()
        self.show_map("Параметры изменены")

    def change_mode(self, mode: str) -> None:
        self.mode = mode
        self.board.xview_moveto(0)
        self._save_preferences()
        self.show_map("Режим изменён")

    def show_map(self, message: Optional[str] = None) -> None:
        """Preparation starts hidden; the full map is visible only for a timed window."""
        self._cancel_study_timer()
        self.phase = "ready"
        self.checked = False
        self.guess_fret = None
        self.study_message = message or "Готов к повторению?"
        self._update_all()

    def start_study(self) -> None:
        self._cancel_study_timer()
        self.phase = "study"
        self.study_deadline = time.monotonic() + self.study_seconds
        self.study_left = self.study_seconds
        self._update_all()
        self._study_tick()

    def _study_tick(self) -> None:
        if self.phase != "study" or self.study_deadline is None:
            return
        self.study_left = max(0, int(self.study_deadline - time.monotonic() + .999))
        if self.study_left <= 0:
            self.start_quiz()
        else:
            self.quiz_heading.config(text=f"Повторение · {self.study_left} с")
            self.study_after_id = self.root.after(200, self._study_tick)

    def _prefer_flats(self) -> bool:
        return "♭" in self.preset_name

    def _note_name(self, pc: int) -> str:
        return (NOTE_EN_FLAT if self._prefer_flats() else NOTE_EN)[pc]

    def _note_ru(self, pc: int) -> str:
        return (NOTE_RU_FLAT if self._prefer_flats() else NOTE_RU)[pc]

    def _readable_note(self, pc: int) -> str:
        return readable_note(pc, self._prefer_flats())

    def _pitch(self, row: int, fret: int) -> int:
        return pitch_at(self.tuning, row, fret)

    def _pitch_class(self, row: int, fret: int) -> int:
        return self._pitch(row, fret) % 12

    def _make_questions(self) -> list[Question]:
        pool = [Question(row, fret)
                for row in range(6 - self.active_strings, 6)
                for fret in range(self.active_frets + 1)]
        if self.mode == "find":
            # With >12 frets the same pitch class reappears on a string;
            # a find-question asks for the pitch, not one arbitrary octave.
            unique: dict[tuple[int, int], Question] = {}
            for q in pool:
                unique.setdefault((q.row, self._pitch_class(q.row, q.fret)), q)
            pool = list(unique.values())
        questions: list[Question] = []
        while len(questions) < self.question_count:
            batch = pool[:]
            random.shuffle(batch)
            questions.extend(batch)
        return questions[:self.question_count]

    def start_quiz(self) -> None:
        self._cancel_study_timer()
        self.run_started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.run_id = uuid4().hex
        self.responses = []
        self.current_run = None
        self.questions = self._make_questions()
        self.index = 0
        self.correct = 0
        self.mistakes = []
        self.checked = False
        self.guess_fret = None
        self.feedback = ""
        self.phase = "quiz"
        self._update_all()
        self.question_started = time.monotonic()

    def _current(self) -> Question:
        return self.questions[self.index]

    def _feedback(self, correct: bool, actual_pc: Optional[int] = None) -> None:
        q = self._current()
        target_pc = self._pitch_class(q.row, q.fret)
        # Record response BEFORE sound synthesis/UI rendering delays.
        duration = round(max(0.0, time.monotonic() - self.question_started), 3) if self.question_started is not None else 0.0
        self.question_started = None
        self.checked = True
        self.feedback_is_correct = correct
        answer_pc = actual_pc if self.mode == "find" else getattr(self, "_chosen_pc", None)
        self.responses.append({
            "index": self.index + 1,
            "mode": self.mode,
            "string_number": int(STRINGS[q.row][0]),
            "fret": q.fret,
            "expected_note": self._note_name(target_pc),
            "expected_midi": self._pitch(q.row, q.fret),
            "answer_note": self._note_name(answer_pc) if answer_pc is not None else None,
            "answer_fret": self.guess_fret if self.mode == "find" else None,
            "correct": bool(correct),
            "response_seconds": duration,
        })
        if correct:
            self.correct += 1
            self.feedback = f"Верно · {self._readable_note(target_pc)} · {duration:.2f} с"
            self.audio.play(self._pitch(q.row, self.guess_fret if self.mode == "find" and self.guess_fret is not None else q.fret))
        else:
            n = STRINGS[q.row][0]
            if self.mode == "name":
                self.feedback = f"{self._readable_note(target_pc)} · {duration:.2f} с"
                self.mistakes.append(f"{n}-я струна, лад {q.fret}: {self._readable_note(target_pc)}")
            else:
                valid = [f for f in range(self.active_frets + 1)
                         if self._pitch_class(q.row, f) == target_pc]
                frets = ", ".join(map(str, valid))
                self.feedback = (f"{self._readable_note(actual_pc)} → {self._readable_note(target_pc)} "
                                 f"(лад: {frets}) · {duration:.2f} с")
                self.mistakes.append(f"{n}-я струна: найти {self._readable_note(target_pc)} (лады {frets})")
            wrong_fret = self.guess_fret if self.mode == "find" and self.guess_fret is not None else q.fret
            self.audio.play(self._pitch(q.row, wrong_fret), buzzing=True)
        self._update_all()

    def answer_name(self, pitch_class: int) -> None:
        if self.phase != "quiz" or self.checked or self.mode != "name":
            return
        self._chosen_pc = pitch_class
        self._feedback(pitch_class == self._pitch_class(self._current().row, self._current().fret))

    def _click_board(self, event: tk.Event) -> None:
        x = self.board.canvasx(event.x)
        fret = int(x // self.cell_width)
        row = int((event.y - TOP) // ROW_H)
        if not (0 <= fret <= self.active_frets and 0 <= row < 6 and self._active(row)):
            return
        if self.phase == "study" and self.study_deadline is not None and time.monotonic() < self.study_deadline:
            self.audio.play(self._pitch(row, fret))
            return
        if self.phase != "quiz" or self.checked or self.mode != "find":
            return
        q = self._current()
        if row != q.row:
            return  # Target string is fixed; grey and other rows do not answer.
        self.guess_fret = fret
        pc = self._pitch_class(row, fret)
        self._feedback(pc == self._pitch_class(q.row, q.fret), actual_pc=pc)

    def abort_quiz(self) -> None:
        if self.phase == "quiz" and messagebox.askyesno(
                "Прервать тест", "Текущий тест не будет сохранён. Прервать?", parent=self.root):
            self.show_map("Тест прерван")

    def next_question(self) -> None:
        if self.phase != "quiz" or not self.checked:
            return
        self.index += 1
        self.checked = False
        self.guess_fret = None
        self.feedback = ""
        if self.index >= len(self.questions):
            self.phase = "result"
            self._finish_run()
        self._update_all()
        if self.phase == "quiz":
            self.question_started = time.monotonic()

    def _finish_run(self) -> None:
        self.current_run = {
            "schema_version": 1,
            "app_version": "0.4.3",
            "run_id": self.run_id,
            "started_at": self.run_started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "configuration": {
                "preset": self.preset_name,
                "tuning_midi": list(self.tuning),
                "active_strings": self.active_strings,
                "active_frets": self.active_frets,
                "question_count": len(self.questions),
                "study_seconds": self.study_seconds,
                "mode": self.mode,
            },
            "questions": self.responses[:],
        }
        try:
            save_run(self.current_run)
            self._set_status("Результат сохранён в results/")
        except (OSError, ValueError) as exc:
            self._set_status(f"Не удалось сохранить результат: {exc}")
            messagebox.showwarning("Сохранение результата", str(exc), parent=self.root)

    def export_current(self) -> None:
        if self.current_run is not None:
            self._copy_text(export_runs_for_llm([self.current_run]))

    def open_help(self) -> None:
        messagebox.showinfo("Как пользоваться", "1. Выбери струны, лады и длительность повторения.\n"
            "2. Нажми «Повторение» — ноты появятся на время.\n"
            "3. Когда таймер закончится, начнётся тест.\n"
            "4. Ответь кнопкой или нажатием на гриф.\n"
            "5. Итог сохраняется в results/. Кнопка «Export Results» копирует JSON.\n"
            "6. Меню «История» позволяет выбрать несколько запусков и копировать их отчёт.\n"
            "Папки settings/ и results/ находятся рядом с программой и исключены из Git.", parent=self.root)

    def open_history(self) -> None:
        if getattr(self, "_history_window", None) is not None and self._history_window.winfo_exists():
            self._history_window.lift()
            return
        window = tk.Toplevel(self.root, bg=BG)
        self._history_window = window
        window.title("vGUITAR — История")
        sw, sh = window.winfo_screenwidth(), window.winfo_screenheight()
        window.geometry(f"{max(650,min(1010,sw-80))}x{max(430,min(620,sh-120))}")
        window.minsize(650, 430)
        pane = tk.Frame(window, bg=PANEL, padx=14, pady=12)
        pane.pack(fill="both", expand=True, padx=12, pady=12)
        self._label(pane, "История тестов", 17, TEXT, True).pack(anchor="w")
        runs, skipped = list_runs()
        subtitle = f"Запусков: {len(runs)}" + (f" · Повреждено: {skipped}" if skipped else "")
        self._label(pane, subtitle, 10, MUTED).pack(anchor="w", pady=(2, 10))
        area = tk.Frame(pane, bg=PANEL)
        area.pack(fill="both", expand=True)
        columns = ("date", "mode", "range", "score", "mean", "median", "tuning")
        tree = ttk.Treeview(area, columns=columns, show="headings", selectmode="extended")
        headings = {"date":"Дата UTC", "mode":"Режим", "range":"Область", "score":"Точность", "mean":"Среднее", "median":"Медиана", "tuning":"Строй"}
        widths = {"date":152, "mode":115, "range":110, "score":95, "mean":94, "median":94, "tuning":235}
        for key in columns:
            tree.heading(key,text=headings[key])
            tree.column(key,width=widths[key],minwidth=75,stretch=key=="tuning")
        vs = ttk.Scrollbar(area,orient="vertical",command=tree.yview)
        hs = ttk.Scrollbar(area,orient="horizontal",command=tree.xview)
        tree.configure(yscrollcommand=vs.set,xscrollcommand=hs.set)
        tree.grid(row=0,column=0,sticky="nsew")
        vs.grid(row=0,column=1,sticky="ns")
        hs.grid(row=1,column=0,sticky="ew")
        area.grid_rowconfigure(0,weight=1)
        area.grid_columnconfigure(0,weight=1)
        indexed = {}
        for i,run in enumerate(runs):
            stat = run_statistics(run)
            cfg = run.get("configuration",{})
            item_id = f"run_{i}"
            indexed[item_id] = run
            tree.insert("", "end", iid=item_id, values=(
                str(run.get("finished_at", ""))[:19].replace("T", " "),
                "Нота" if cfg.get("mode")=="name" else "Найти",
                f"{cfg.get('active_strings','?')} стр. / {cfg.get('active_frets','?')} л.",
                f"{stat['correct']}/{stat['total']} ({stat['accuracy_percent']}%)",
                f"{stat['mean_seconds']:.2f} с" if stat['mean_seconds'] is not None else "—",
                f"{stat['median_seconds']:.2f} с" if stat['median_seconds'] is not None else "—",
                cfg.get("preset", "—"),
            ))
        details = tk.Text(pane, bg=BG, fg=TEXT, height=5, wrap="word", font=(FONT,10), relief="flat")
        details.pack(fill="x", pady=(9, 5))
        details.configure(state="disabled")
        def selected():
            return [indexed[r] for r in tree.selection()]
        def show_details(event=None):
            current=selected()
            details.configure(state="normal")
            details.delete("1.0","end")
            if current:
                s=run_statistics(current[0])
                wrong = ", ".join(f"{k} ×{v}" for k,v in s["wrong_notes"].items()) or "нет"
                details.insert("end",f"Правильно: {s['correct']}/{s['total']} · Среднее: {s['mean_seconds']} с · Медиана: {s['median_seconds']} с\nОшибки: {wrong}\nВыбрано запусков: {len(current)}")
            details.configure(state="disabled")
        tree.bind("<<TreeviewSelect>>", show_details)
        bottom=tk.Frame(pane,bg=PANEL)
        bottom.pack(fill="x",pady=(5,0))
        def do_export():
            chosen=selected()
            if not chosen:
                messagebox.showinfo("Экспорт", "Выбери хотя бы один запуск.",parent=window)
                return
            self._copy_text(export_runs_for_llm(chosen))
        export=self._button(bottom,"Export Selected Runs for LLM",do_export,primary=True)
        export.pack(side="left")
        Tooltip(export,"Копирует выбранные запуски, включая время каждого ответа, в буфер обмена.")
        self._button(bottom,"Закрыть",window.destroy).pack(side="right")
        if runs:
            tree.selection_set("run_0")
            tree.see("run_0")
            show_details()

    def _enter_key(self, event: tk.Event) -> None:
        if self.phase == "quiz" and self.checked:
            self.next_question()

    def _update_all(self) -> None:
        self.footer_label.config(text=f"Строй: {self.preset_name}   •   Esc: подготовка   •   ? Справка в меню")
        self.strings_value.config(text=str(self.active_strings))
        self.frets_value.config(text=str(self.active_frets))
        self.questions_value.config(text=str(self.question_count))
        self.study_value.config(text=str(self.study_seconds))
        self._update_answer_layout_buttons()
        self.answer_layout_frame.pack_forget()
        if self.mode == "name":
            self.answer_layout_frame.pack(side="right")
        for mode, btn in self.mode_buttons.items():
            selected = (mode == self.mode)
            btn.config(bg=ACCENT if selected else BUTTON_BG,
                       fg="#072139" if selected else TEXT)
        if self.board.winfo_width() > 1:
            self.cell_width = max(CELL_W, min(120, self.board.winfo_width() // (self.active_frets + 1)))
        self._draw_board()
        self._update_quiz_ui()

    def _board_resized(self, event) -> None:
        usable = max(1, int(event.width))
        count = self.active_frets + 1
        # Never compress below the readable default; expand to use space instead.
        desired = max(CELL_W, min(120, usable // count))
        if desired != self.cell_width:
            self.cell_width = desired
            self._draw_board()

    def _draw_board(self) -> None:
        self.board.delete("all")
        self.string_labels.delete("all")
        width = (self.active_frets + 1) * self.cell_width
        self.board.configure(scrollregion=(0, 0, width, BOARD_H))
        self.board_heading.config(text="ПОВТОРЕНИЕ" if self.phase == "study" else "ГРИФ")
        self.board_hint.config(text=f"{self.active_strings}/6 струн · 0–{self.active_frets}")
        for fret in range(self.active_frets + 1):
            x0 = fret * self.cell_width
            self.board.create_text(x0 + self.cell_width / 2, 12, text=str(fret),
                                   fill=MUTED, font=(FONT, 10, "bold"))
        for row, (num, letter, ru, base_pc) in enumerate(STRINGS):
            pc_open = self._pitch_class(row, 0)
            letter, ru = self._note_name(pc_open), self._note_ru(pc_open)
            active = self._active(row)
            y0 = TOP + row * ROW_H
            ymid = y0 + ROW_H / 2
            label_color = TEXT if active else FAINT
            self.string_labels.create_text(4, ymid - 7, text=f"{num}-я {letter}",
                                           anchor="w", fill=label_color,
                                           font=(FONT, 10, "bold"))
            self.string_labels.create_text(4, ymid + 8, text=ru,
                                           anchor="w", fill=MUTED if active else FAINT,
                                           font=(FONT, 8))
            for fret in range(self.active_frets + 1):
                x0 = fret * self.cell_width
                color = (CELL_ACTIVE if fret % 2 == 0 else CELL_ACTIVE_ALT) if active else (
                    CELL_INACTIVE if fret % 2 == 0 else CELL_INACTIVE_ALT)
                self.board.create_rectangle(x0, y0, x0 + self.cell_width, y0 + ROW_H,
                                            fill=color, outline=BORDER if active else "#27313e",
                                            width=1)
                if fret == 0:
                    self.board.create_rectangle(x0 + self.cell_width - 3, y0,
                                                x0 + self.cell_width, y0 + ROW_H,
                                                fill=TEXT if active else FAINT, outline="")
                self.board.create_line(x0 + 7, ymid, x0 + self.cell_width - 7, ymid,
                                       fill=blend_hex("#b4d5e4", color, .45 if active else .13),
                                       width=max(1, 4 - row // 2))
                pc = self._pitch_class(row, fret)
                is_target = self.phase == "quiz" and self.mode == "name" and not self.checked and (
                    row == self._current().row and fret == self._current().fret)
                show_note = active and self.phase == "study"
                if active and self.phase == "quiz" and self.checked:
                    q = self._current()
                    if self.mode == "name" and (row, fret) == (q.row, q.fret):
                        show_note = True
                    if self.mode == "find" and row == q.row and pc == self._pitch_class(q.row, q.fret):
                        show_note = True
                if show_note:
                    highlight = self.phase == "quiz" and self.checked
                    self.board.create_oval(x0 + 13, ymid - 14, x0 + self.cell_width - 13, ymid + 14,
                                           fill="#236e70" if highlight else "#2b607f",
                                           outline=GREEN if highlight else "#4b9abd", width=1)
                    self.board.create_text(x0 + self.cell_width / 2, ymid - 5, text=self._note_name(pc),
                                           fill=TEXT, font=(FONT, 10, "bold"))
                    self.board.create_text(x0 + self.cell_width / 2, ymid + 8, text=self._note_ru(pc),
                                           fill="#c8e3ef", font=(FONT, 7))
                elif is_target:
                    self.board.create_oval(x0 + 14, ymid - 14, x0 + self.cell_width - 14, ymid + 14,
                                           fill="#245879", outline=ACCENT, width=2)
                    self.board.create_text(x0 + self.cell_width / 2, ymid, text="?",
                                           fill=TEXT, font=(FONT, 14, "bold"))
                if active and self.phase == "quiz" and self.mode == "find":
                    q = self._current()
                    if row == q.row and not self.checked:
                        self.board.create_rectangle(x0 + 3, y0 + 3, x0 + self.cell_width - 3,
                                                    y0 + ROW_H - 3, outline="#4188ad", width=2)
                    if self.checked and row == q.row and fret == self.guess_fret:
                        self.board.create_rectangle(x0 + 2, y0 + 2, x0 + self.cell_width - 2,
                                                    y0 + ROW_H - 2,
                                                    outline=GREEN if self.feedback_is_correct else RED,
                                                    width=3)
        if self.phase == "quiz":
            q = self._current()
            x0 = q.fret * self.cell_width
            if self.mode == "name":
                self.board.xview_moveto(max(0, x0 - 2 * self.cell_width) / max(width, 1))
            # In 'find' mode don't reveal the target fret by auto-scrolling.

    def _clear(self, parent: tk.Widget) -> None:
        for child in parent.winfo_children():
            child.destroy()

    def _render_row_answers(self, parent: tk.Widget, target_pc: int) -> None:
        # Seven naturals are primary; five sharps form a smaller second row.
        grid = tk.Frame(parent, bg=PANEL)
        grid.pack(fill="x", pady=1)
        for column, natural in enumerate((0, 2, 4, 5, 7, 9, 11)):
            grid.grid_columnconfigure(column, weight=1, uniform="notes")
            button = self._answer_button(grid, natural, target_pc, compact=False)
            button.grid(row=0, column=column, sticky="nsew", padx=2, pady=(2, 4))
            sharp = {0:1, 2:3, 5:6, 7:8, 9:10}.get(natural)
            if sharp is not None:
                button = self._answer_button(grid, sharp, target_pc, compact=True)
                button.grid(row=1, column=column, sticky="nsew", padx=2, pady=(0, 1))

    def _answer_button(self, parent: tk.Widget, pc: int, target_pc: int,
                       compact: bool) -> tk.Button:
        label = self._note_name(pc)
        button = self._button(parent, label, lambda n=pc: self.answer_name(n), compact=True)
        button.config(font=(FONT, 10 if compact else 15, "bold"), pady=2 if compact else 6,
                      bg="#224055" if compact else BUTTON_BG)
        Tooltip(button, self._readable_note(pc))
        if self.checked:
            chosen = self._chosen_pc
            if pc == target_pc:
                button.config(bg="#27765e", fg=TEXT, activebackground="#27765e")
            elif pc == chosen:
                button.config(bg="#813f43", fg=TEXT)
            else:
                button.config(state="disabled", disabledforeground=FAINT)
        return button

    @staticmethod
    def _circle_geometry(width: int, height: int) -> tuple[float, float, float, float]:
        cx, cy = width / 2, height / 2
        outer = max(20.0, min(125.0, (width/2 - 8)/1.23, (height/2 - 8)/1.23))
        natural_size = max(8.0, min(22.0, outer * .21))
        sharp_size = max(6.0, min(16.0, outer * .155))
        inner = outer - natural_size - sharp_size - max(5.0, outer * .08)
        return cx, cy, outer, inner

    @staticmethod
    def _circle_points(width: int, height: int) -> dict[int, tuple[float,float,float]]:
        """Seven naturals outside; every sharp aligned directly beneath its natural."""
        cx, cy, outer, inner = NoteTrainer._circle_geometry(width, height)
        natural = (0, 2, 4, 5, 7, 9, 11)
        sharps = {0:1, 2:3, 5:6, 7:8, 9:10}
        result = {}
        for i, pc in enumerate(natural):
            angle = -math.pi / 2 + 2 * math.pi * i / 7
            direction = (math.cos(angle), math.sin(angle))
            result[pc] = (cx + outer * direction[0],
                          cy + outer * direction[1], max(8.0, min(22.0, outer * .21)))
            if pc in sharps:
                result[sharps[pc]] = (cx + inner * direction[0],
                                      cy + inner * direction[1], max(6.0, min(16.0, outer * .155)))
        return result

    def _render_circle_answers(self, parent: tk.Widget, target_pc: int) -> None:
        canvas = tk.Canvas(parent, height=245, bg=PANEL, highlightthickness=0,
                           cursor="hand2")
        canvas.pack(fill="both", expand=True)
        self._answer_wheel = canvas

        def draw(event=None):
            width, height = max(canvas.winfo_width(), 180), max(canvas.winfo_height(), 190)
            canvas.delete("all")
            self.answer_wheel_regions = self._circle_points(width, height)
            cx, cy, outer, inner = self._circle_geometry(width, height)
            for radius in (outer, inner):
                canvas.create_oval(cx-radius, cy-radius, cx+radius, cy+radius,
                                   outline=BORDER, width=1)
            # Short spokes link C-C♯, D-D♯, F-F♯, G-G♯, A-A♯.
            for base, sharp in ((0,1), (2,3), (5,6), (7,8), (9,10)):
                bx, by, br = self.answer_wheel_regions[base]
                sx, sy, sr = self.answer_wheel_regions[sharp]
                canvas.create_line(bx, by, sx, sy, fill="#36536a", width=2)
            for pc, (x, y, r) in self.answer_wheel_regions.items():
                natural = pc in (0,2,4,5,7,9,11)
                fill = BUTTON_BG if natural else "#224055"
                outline = BORDER
                if self.checked:
                    if pc == target_pc:
                        fill, outline = "#27765e", GREEN
                    elif pc == self._chosen_pc:
                        fill, outline = "#813f43", RED
                    else:
                        fill = CELL_INACTIVE
                canvas.create_oval(x-r, y-r, x+r, y+r, fill=fill,
                                   outline=outline, width=2 if pc==target_pc and self.checked else 1)
                canvas.create_text(x, y, text=self._note_name(pc),
                                   fill=TEXT if not self.checked or pc in (target_pc, self._chosen_pc) else FAINT,
                                   font=(FONT, 12 if natural else 9, "bold"))
        canvas.bind("<Configure>", draw)
        def clicked(event):
            if self.checked:
                return
            for pc, (x,y,r) in self.answer_wheel_regions.items():
                if (event.x-x)**2 + (event.y-y)**2 <= (r+2)**2:
                    self.answer_name(pc)
                    return
        canvas.bind("<Button-1>", clicked)
        draw()

    def _update_quiz_ui(self) -> None:
        self._clear(self.quiz_body)
        self._clear(self.action_row)
        if self.phase in ("ready", "study"):
            self.quiz_heading.config(text="Подготовка" if self.phase == "ready" else f"Повторение · {self.study_left} с")
            if self.phase == "ready":
                self._label(self.quiz_body,"Ноты появятся на выбранное время.",10,MUTED).pack(anchor="w")
                button = self._button(self.action_row,"Повторение ▶",self.start_study,primary=True,compact=True)
                button.pack(side="left")
                Tooltip(button,"Показать ноты перед тестом, затем автоматически скрыть их.")
            else:
                self._label(self.quiz_body,"Нажимай ноты, чтобы услышать их.",10,MUTED).pack(anchor="w")
                self._button(self.action_row,"Начать тест →",self.start_quiz,primary=True,compact=True).pack(side="left")
        elif self.phase == "quiz":
            q = self._current()
            target = self._pitch_class(q.row,q.fret)
            string = f"{STRINGS[q.row][0]}-я ({self._note_name(self._pitch_class(q.row,0))})"
            self.quiz_heading.config(text=f"Вопрос {self.index+1}/{len(self.questions)} · ✓ {self.correct}")
            if self.mode == "name":
                where = f"лад {q.fret}" if q.fret else "открытая"
                self._label(self.quiz_body,f"{string} · {where} — какая нота?",11,TEXT,True).pack(anchor="w")
                if self.answer_layout == "circle":
                    self._render_circle_answers(self.quiz_body,target)
                else:
                    self._render_row_answers(self.quiz_body,target)
            else:
                self._label(self.quiz_body,f"Найди {self._readable_note(target)} на {string}",11,TEXT,True).pack(anchor="w")
            if self.checked:
                prefix = "✓ " if self.feedback_is_correct else "✕ "
                self._label(self.action_row,prefix+self.feedback,10,GREEN if self.feedback_is_correct else AMBER,
                            wraplength=440,justify="left").pack(side="left",fill="x",expand=True)
                caption = "Итог →" if self.index+1==len(self.questions) else "Дальше →"
                self._button(self.action_row,caption,self.next_question,primary=True,compact=True).pack(side="right",padx=(6,0))
            else:
                self._button(self.action_row,"Прервать",self.abort_quiz,compact=True).pack(side="left")
        else:
            total = len(self.questions)
            self.quiz_heading.config(text=f"Результат · {self.correct}/{total}")
            if self.current_run:
                stats=run_statistics(self.current_run)
                self._label(self.quiz_body,
                            f"{stats['accuracy_percent']}% точно  ·  среднее {stats['mean_seconds']} с  ·  медиана {stats['median_seconds']} с",
                            11,ACCENT,True).pack(anchor="w",pady=4)
            if self.mistakes:
                self._label(self.quiz_body,"Ошибки: " + "; ".join(self.mistakes[:2]) + ("…" if len(self.mistakes)>2 else ""),
                            9,MUTED,wraplength=560,justify="left").pack(anchor="w")
            else:
                self._label(self.quiz_body,"Без ошибок!",11,GREEN,True).pack(anchor="w")
            btn=self._button(self.action_row,"Export Results",self.export_current,primary=True,compact=True)
            btn.pack(side="left",padx=(0,6))
            Tooltip(btn,"Скопировать JSON-отчёт теста в буфер обмена.")
            self._button(self.action_row,"История",self.open_history,compact=True).pack(side="left",padx=(0,6))
            self._button(self.action_row,"Повторить",self.show_map,compact=True).pack(side="left")


def main() -> None:
    root = tk.Tk()
    NoteTrainer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
