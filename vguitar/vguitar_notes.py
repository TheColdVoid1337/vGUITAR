#!/usr/bin/env python3
"""vGUITAR Note Trainer — an offline fretboard study and quiz app.

Python 3.9+, Tkinter and sounddevice on Windows. Offline; no accounts.
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

from vguitar_about import load_icon, open_about
from vguitar_audio import AudioPlayer
from vguitar_caged import (CAGED_ORDER, INTERVAL_DESCRIPTIONS,
                           caged_positions, caged_shift, next_caged_form)
from vguitar_forms import (caged_scale, power_chord, triad_voicing,
    suggested_fingers, TRIAD_QUALITIES, TRIAD_INVERSIONS, POWER_VOICES)
from vguitar_scale_shapes import BOX_SCALES, BOX_NAMES, pentatonic_box, next_box
from vguitar_scale_patterns import (FINGERING_SCALES, shape_names, shape_family,
                                   scale_fingering, next_shape)
from vguitar_strings import normalize_selected_strings, rows_for_strings, strings_from_count
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
OPEN_WIDTH = 52  # narrow open string area, but room for a note badge
FRET_RATIO = 2 ** (-1 / 12)  # equal-tempered fret spacing toward the bridge
FRET_MIN_WIDTH = 29  # enough click area at the highest fret
FRETBOARD_THEMES = {
    "default": {"name": "Оригинальная", "neck": "#163349", "open": "#101c2a", "inactive": "#0b1929", "wire": "#8497a9", "string": "#b8d4df", "muted": "#506273", "dot": "#f1f5fa", "dot_outline": "#a8b8c9"},
    "ebony": {"name": "Ebony", "neck": "#1b1a1c", "open": "#101013", "inactive": "#101113", "wire": "#8d8d92", "string": "#c0c4c9", "muted": "#53555a", "dot": "#f6f4ee", "dot_outline": "#77787a"},
    "ash": {"name": "Светлый ясень", "neck": "#cba876", "open": "#987b58", "inactive": "#766956", "wire": "#62584e", "string": "#413f3a", "muted": "#756d61", "dot": "#fffdf5", "dot_outline": "#584b3a"},
    "mahogany": {"name": "Махагон", "neck": "#693a2d", "open": "#3d241f", "inactive": "#332520", "wire": "#ac9189", "string": "#f0d7c6", "muted": "#78655e", "dot": "#fff6e6", "dot_outline": "#9e7b6d"},
}
EAR_REPLAYS = 3
TOP = 24
ROW_H = 31
BOARD_H = TOP + ROW_H * 6 + 6
FONT = "Segoe UI"
SCALES = {
    "Мажор": ((0,2,4,5,7,9,11,12), ("1","2","3","4","5","6","7","8")),
    "Натуральный минор": ((0,2,3,5,7,8,10,12), ("1","2","♭3","4","5","♭6","♭7","8")),
    "Минорная пентатоника": ((0,3,5,7,10,12), ("1","♭3","4","5","♭7","8")),
    "Мажорная пентатоника": ((0,2,4,7,9,12), ("1","2","3","5","6","8")),
    "Блюзовая": ((0,3,5,6,7,10,12), ("1","♭3","4","♭5","5","♭7","8")),
    "Дорийский": ((0,2,3,5,7,9,10,12), ("1","2","♭3","4","5","6","♭7","8")),
    "Фригийский": ((0,1,3,5,7,8,10,12), ("1","♭2","♭3","4","5","♭6","♭7","8")),
}
SCALE_POSITION_SPAN = 5

# Physical fretboard inlays (single and double dots), independent of tuning.
INLAY_SINGLE = frozenset((3, 5, 7, 9, 15, 17, 19, 21))
INLAY_DOUBLE = frozenset((12, 24))


def fret_width(fret: int, cell_width: float) -> float:
    """Physical frets narrow by 2**(-1/12) per fret. Open area is separate."""
    if fret < 0:
        raise ValueError("Fret must be nonnegative")
    return OPEN_WIDTH if fret == 0 else cell_width * FRET_RATIO ** (fret - 1)


def fret_start(fret: int, cell_width: float) -> float:
    if fret < 0:
        raise ValueError("Fret must be nonnegative")
    return 0.0 if fret == 0 else OPEN_WIDTH + cell_width * (1 - FRET_RATIO ** (fret-1)) / (1-FRET_RATIO)


def fret_center(fret: int, cell_width: float) -> float:
    return fret_start(fret, cell_width) + fret_width(fret, cell_width) / 2


def fret_from_x(x: float, cell_width: float) -> int:
    if x < OPEN_WIDTH:
        return 0
    for fret in range(1, 25):
        if x < fret_start(fret+1, cell_width):
            return fret
    return 25


def board_width(n_frets: int, cell_width: float) -> float:
    return fret_start(n_frets, cell_width) + fret_width(n_frets, cell_width)


def board_base_width(available: float, n_frets: int) -> float:
    """Fit short ranges; long necks scroll instead of making top frets unclickable."""
    if n_frets < 1:
        return CELL_W
    ratio_sum = (1-FRET_RATIO**n_frets)/(1-FRET_RATIO)
    by_available = (max(OPEN_WIDTH+1,available)-OPEN_WIDTH)/ratio_sum
    by_click_target = FRET_MIN_WIDTH/(FRET_RATIO ** (n_frets-1))
    return max(CELL_W, by_click_target, min(145.0,by_available))


def fret_inlay_centers(fret: int, cell_width: float) -> list[tuple[float, float]]:
    """Inlays on the real fretted neck; none on the short open cell."""
    x = fret_center(fret, cell_width)
    if fret in INLAY_DOUBLE:
        return [(x, TOP + ROW_H * 2), (x, TOP + ROW_H * 4)]
    if fret in INLAY_SINGLE:
        return [(x, TOP + ROW_H * 3)]
    return []

def note_disc_bbox(x: float, y: float, cell_width: float) -> tuple[float, float, float, float]:
    """Circular note badges stay circular when fret cells become wide."""
    radius = min(13.4, ROW_H * .43, cell_width * .24)
    return (x-radius, y-radius, x+radius, y+radius)


def scale_pattern(name: str, key: int) -> tuple[list[int], tuple[str, ...]]:
    if name not in SCALES or not 0 <= key < 12:
        raise ValueError("Unknown scale or key")
    offsets, degrees = SCALES[name]
    return [(key+n)%12 for n in offsets], degrees


def scale_positions(tuning: tuple[int, ...], name: str, key: int, start_fret: int,
                    span: int = SCALE_POSITION_SPAN) -> list[tuple[int, int, int, str]]:
    """Every scale tone on ALL six strings in the chosen position, bass to treble.

    A step is (string row, fret, absolute MIDI pitch, interval degree). Unlike
    a single-octave run, this covers the entire five-fret guitar scale shape.
    Each question names its string, so a response must select that exact fret.
    """
    if len(tuning) != 6 or not 0 <= start_fret <= 24 or span < 1 or start_fret + span - 1 > 24:
        raise ValueError("Invalid position window")
    allowed, labels = scale_pattern(name, key)
    degree_by_pc = {pc: degree for pc, degree in zip(allowed, labels)}
    result: list[tuple[int, int, int, str]] = []
    for row in range(5, -1, -1):
        for fret in range(start_fret, start_fret + span):
            midi = pitch_at(tuning, row, fret)
            degree = degree_by_pc.get(midi % 12)
            if degree is not None:
                result.append((row, fret, midi, degree if degree != "8" else "1"))
    if not result or not set(allowed[:-1]).issubset({item[2] % 12 for item in result}):
        raise ValueError("Scale not fully available in selected position")
    return result


def auto_scale_position(tuning: tuple[int, ...], name: str, key: int,
                        previous: int | None = None, *, rng=None) -> int:
    """Choose a complete 5-fret scale shape; avoid immediately repeating it."""
    valid = []
    for start in range(25 - SCALE_POSITION_SPAN):
        try:
            shape = scale_positions(tuning, name, key, start)
        except ValueError:
            continue
        # Root in the shape makes the pattern easier to orient musically.
        if any(midi % 12 == key for _, _, midi, _ in shape):
            valid.append(start)
    if not valid:
        raise ValueError("No playable position for this scale and tuning")
    choices = [n for n in valid if n != previous] or valid
    return (rng or random).choice(choices)


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
        self._window_icon = load_icon(self.root)
        if self._window_icon is not None:
            self.root.iconphoto(True, self._window_icon)
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
        preferences = read_preferences()
        lesson = preferences.get("lesson", {})
        if not isinstance(lesson, dict):
            lesson = {}
        audio_settings = preferences.get('audio', {})
        if not isinstance(audio_settings, dict):
            audio_settings = {}
        self.audio = AudioPlayer(initial_volume,
            output_id=str(audio_settings.get('output_id', '')),
            latency=str(audio_settings.get('latency', 'high')),
            blocksize=audio_settings.get('blocksize', 0),
            exclusive=bool(audio_settings.get('exclusive', False)))
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.active_strings = self._bounded(lesson.get("active_strings", 2), 1, 6, 2)
        self.selected_strings = normalize_selected_strings(lesson.get("selected_strings"), self.active_strings)
        self.active_strings = len(self.selected_strings)
        self.active_frets = self._bounded(lesson.get("active_frets", 7), 1, 24, 7)
        self.question_count = self._bounded(lesson.get("question_count", 10), 5, 100, 10)
        self.study_seconds = self._bounded(lesson.get("study_seconds", 60), 10, 300, 60)
        self.mode = lesson.get("mode") if lesson.get("mode") in ("name", "find", "ear", "scale", "caged") else "name"
        self.fretboard_theme = preferences.get("fretboard_theme", "default")
        if self.fretboard_theme not in FRETBOARD_THEMES:
            self.fretboard_theme = "default"
        self.answer_layout = lesson.get("answer_layout") if lesson.get("answer_layout") in ("rows", "circle") else "rows"
        self.scale_name = lesson.get("scale_name") if lesson.get("scale_name") in SCALES else "Натуральный минор"
        self.scale_key = self._bounded(lesson.get("scale_key",4),0,11,4)
        self.scale_position_mode = (lesson.get("scale_position_mode")
                                    if lesson.get("scale_position_mode") in ("auto", "manual") else "auto")
        self.scale_position = self._bounded(lesson.get("scale_position",0),0,20,0)
        # Explicit 3NPS positions for 7-note scales, blues and pentatonic boxes.
        # Range/full-neck study remain separate choices.
        preferred_view = "box" if self.scale_name in FINGERING_SCALES else "range"
        self.scale_view = lesson.get("scale_view", preferred_view)
        if self.scale_view not in ("box", "full", "range"):
            self.scale_view = preferred_view
        if self.scale_view == "box" and self.scale_name not in FINGERING_SCALES:
            self.scale_view = "range"
        self.scale_box_mode = lesson.get("scale_box_mode") if lesson.get("scale_box_mode") in ("auto", "manual") else "auto"
        self.scale_box = self._bounded(lesson.get("scale_box", 1), 1, 7, 1)
        if self.scale_view == "box":
            self.scale_box = min(self.scale_box, len(shape_names(self.scale_name)))
        if self.scale_position_mode == "auto":
            self.scale_position = auto_scale_position(self.tuning, self.scale_name, self.scale_key)
        self.scale_steps: list[tuple[int,int,int,str]] = []
        self.caged_key = self._bounded(lesson.get("caged_key", 7), 0, 11, 7)
        self.caged_form_mode = (lesson.get("caged_form_mode")
                                if lesson.get("caged_form_mode") in ("auto", "manual") else "auto")
        self.caged_form = lesson.get("caged_form") if lesson.get("caged_form") in CAGED_ORDER else "E"
        self.caged_steps: list[tuple[int,int,int,str]] = []
        self.caged_view = lesson.get("caged_view") if lesson.get("caged_view") in ("chord", "major", "minor") else "chord"
        self.forms_kind = lesson.get("forms_kind") if lesson.get("forms_kind") in ("Power chord", "Трезвучие") else "Power chord"
        self.forms_key = self._bounded(lesson.get("forms_key", 7), 0, 11, 7)
        self.forms_quality = lesson.get("forms_quality") if lesson.get("forms_quality") in TRIAD_QUALITIES else "Мажор"
        self.forms_voice = lesson.get("forms_voice") if lesson.get("forms_voice") in POWER_VOICES else "1–5–8"
        self.forms_root_string = self._bounded(lesson.get("forms_root_string", 6), 4, 6, 6)
        self.forms_string_set = lesson.get("forms_string_set") if lesson.get("forms_string_set") in ("1–2–3", "2–3–4", "3–4–5", "4–5–6") else "1–2–3"
        self.forms_inversion = self._bounded(lesson.get("forms_inversion", 0), 0, 2, 0)
        self.form_label_view = lesson.get("form_label_view") if lesson.get("form_label_view") in ("Ноты", "Ступени", "Пальцы") else "Ноты"
        self.forms_steps: list[tuple[int,int,int,str]] = []
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
        self.guess_row: Optional[int] = None
        self.ear_replays_used = 0
        self._ear_sound_after_id: Optional[str] = None
        self.feedback = ""
        self.feedback_is_correct = False
        self.study_message = "Выбери область и запусти повторение."
        self._chosen_pc: Optional[int] = None
        self.cell_width = CELL_W
        self.answer_wheel_regions: dict[int, tuple[float, float, float]] = {}

        self._create_layout()
        self._update_all()
        self.root.bind("<Return>", self._enter_key)
        self.root.bind("<space>", self._space_key)
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
                "fretboard_theme": self.fretboard_theme,
                "audio": {
                    "output_id": self.audio.output_id,
                    "latency": self.audio.latency,
                    "blocksize": self.audio.blocksize,
                    "exclusive": self.audio.exclusive,
                },
                "lesson": {
                    "active_strings": self.active_strings,
                    "selected_strings": list(self.selected_strings),
                    "active_frets": self.active_frets,
                    "question_count": self.question_count,
                    "study_seconds": self.study_seconds,
                    "mode": self.mode,
                    "answer_layout": self.answer_layout,
                    "scale_name": self.scale_name,
                    "scale_key": self.scale_key,
                    "scale_position": self.scale_position,
                    "scale_position_mode": self.scale_position_mode,
                    "scale_view": self.scale_view,
                    "scale_box": self.scale_box,
                    "scale_box_mode": self.scale_box_mode,
                    "caged_key": self.caged_key,
                    "caged_form_mode": self.caged_form_mode,
                    "caged_form": self.caged_form,
                    "caged_view": self.caged_view,
                    "forms_kind": self.forms_kind,
                    "forms_key": self.forms_key,
                    "forms_quality": self.forms_quality,
                    "forms_voice": self.forms_voice,
                    "forms_root_string": self.forms_root_string,
                    "forms_string_set": self.forms_string_set,
                    "forms_inversion": self.forms_inversion,
                    "form_label_view": self.form_label_view,
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
        menu.add_command(label="О программе", command=lambda: open_about(self.root))
        self.root.config(menu=menu)

        toolbar = tk.Frame(self.outer, bg=PANEL, padx=9, pady=6,
                           highlightbackground=BORDER, highlightthickness=1)
        toolbar.pack(fill="x", padx=10, pady=(7, 5))
        self.toolbar = toolbar
        self.brand = tk.Frame(toolbar, bg=PANEL)
        self._label(self.brand, "vGUITAR", 14, ACCENT, True).pack(side="left")
        self._label(self.brand, "  NOTES", 9, MUTED, True).pack(side="left")
        self.counter_strip = tk.Frame(toolbar, bg=PANEL)
        # Keep related counters together; split into two rows only if they
        # genuinely cannot fit at the current window/font/DPI size.
        self.counter_primary = tk.Frame(self.counter_strip, bg=PANEL)
        self.counter_secondary = tk.Frame(self.counter_strip, bg=PANEL)
        self.counter_primary.pack(side="left")
        self.counter_secondary.pack(side="left")
        self.strings_value = self._counter(self.counter_primary, "Струны", "strings", 1, 6)
        self.string_picker_button = self._button(self.counter_primary, "Выбор…", self.open_string_picker, compact=True)
        self.string_picker_button.configure(padx=4)
        self.string_picker_button.pack(side="left", padx=(0, 4))
        Tooltip(self.string_picker_button, "Отметь отдельные струны, например только пятую.")
        self.frets_value = self._counter(self.counter_primary, "Лады", "frets", 1, 24)
        self.questions_value = self._counter(self.counter_secondary, "Вопросы", "questions", 5, 100, step=5)
        self.study_value = self._counter(self.counter_secondary, "Повтор", "study", 10, 300, step=10)
        self.mode_strip = tk.Frame(toolbar, bg=PANEL)
        self.mode_buttons: dict[str, tk.Button] = {}
        for mode, title in (("name", "Назвать"), ("find", "Найти"), ("ear", "На слух"), ("scale", "Гаммы"), ("caged", "CAGED"), ("forms", "Формы")):
            btn = self._button(self.mode_strip, title, lambda m=mode: self.change_mode(m), compact=True)
            btn.configure(padx=4)
            btn.pack(side="left", padx=(0, 3))
            self.mode_buttons[mode] = btn
            Tooltip(btn, {"name": "Назвать ноту на указанном ладу.",
                          "find": "Найти названную ноту на указанной струне.",
                          "ear": "На слух определить высоту и показать её на грифе; 3 повтора.",
                          "scale": "Все гаммы: 7 позиций 3NPS, 5 пентатонических/блюзовых боксов, карта грифа.",
                           "caged": "Пять CAGED-форм аккорда и мажорной/минорной гаммы.",
                           "forms": "Power chords, трезвучия и обращения на группах из трёх струн."}[mode])
        self.utility_strip = tk.Frame(toolbar, bg=PANEL)
        self.history_button = self._button(self.utility_strip, "История", self.open_history, compact=True)
        self.history_button.configure(padx=4)
        self.history_button.pack(side="left", padx=(0, 4))
        Tooltip(self.history_button, "Результаты прошлых тестов и экспорт выбранных запусков.")
        self.about_button = self._button(self.utility_strip, "?", lambda: open_about(self.root), compact=True, width=2)
        self.about_button.configure(padx=3)
        self.about_button.pack(side="left")
        Tooltip(self.about_button, "О программе, разработчике и исходном коде.")
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
        self.string_labels = tk.Canvas(chart_row, width=94, height=BOARD_H,
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
        Tooltip(self.board, "Нажми струну и лад перед тестом или при повторении, чтобы услышать звук.")

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
        self.scale_options = tk.Frame(quiz_card, bg=PANEL)
        self.scale_choice = tk.StringVar(value=self.scale_name)
        self.scale_key_choice = tk.StringVar(value=NOTE_EN[self.scale_key])
        self.scale_view_choice = tk.StringVar(value={"box":"Аппликатуры", "range":"Участок ладов",
                                                    "full":"Весь звукоряд"}[self.scale_view])
        self.scale_position_choice = tk.StringVar()
        self._scale_groups = []
        self._scale_comboboxes = []
        for heading, variable, choices, width in (
            ("Гамма", self.scale_choice, list(SCALES), 19),
            ("Вид", self.scale_view_choice, ["Аппликатуры", "Весь звукоряд", "Участок ладов"], 17),
            ("Key", self.scale_key_choice, list(NOTE_EN), 6),
            ("Позиция", self.scale_position_choice, [], 14),
        ):
            group = tk.Frame(self.scale_options, bg=PANEL)
            self._scale_groups.append(group)
            self._label(group, heading, 9, MUTED).pack(anchor="w")
            combo = ttk.Combobox(group, textvariable=variable, values=choices,
                                 state="readonly", width=width)
            combo.pack(anchor="w")
            combo.bind("<<ComboboxSelected>>", self._scale_option_changed)
            self._scale_comboboxes.append(combo)
        self._refresh_scale_choices()
        self.caged_options = tk.Frame(quiz_card, bg=PANEL)
        self.caged_key_choice = tk.StringVar(value=NOTE_EN[self.caged_key])
        self.caged_form_choice = tk.StringVar(value="Авто" if self.caged_form_mode == "auto" else self.caged_form)
        self._caged_groups = []
        for col, (heading, variable, values, width) in enumerate((
                ("Аккорд", self.caged_key_choice, list(NOTE_EN), 6),
                ("Форма", self.caged_form_choice, ["Авто", *CAGED_ORDER], 9))):
            group = tk.Frame(self.caged_options, bg=PANEL)
            group.grid(row=0, column=col, sticky="w", padx=(0, 8))
            self._caged_groups.append(group)
            self._label(group, heading, 9, MUTED).pack(anchor="w")
            combo = ttk.Combobox(group, textvariable=variable, values=values,
                                 state="readonly", width=width)
            combo.pack(anchor="w")
            combo.bind("<<ComboboxSelected>>", self._caged_option_changed)
        self.caged_view_choice = tk.StringVar(value={"chord":"Аккорд", "major":"Мажорная гамма",
                                                  "minor":"Минорная гамма"}[self.caged_view])
        g = tk.Frame(self.caged_options, bg=PANEL)
        g.grid(row=0, column=2, sticky="w", padx=(0, 8))
        self._label(g, "Вид", 9, MUTED).pack(anchor="w")
        c = ttk.Combobox(g, textvariable=self.caged_view_choice, state="readonly", width=18,
                         values=["Аккорд", "Мажорная гамма", "Минорная гамма"])
        c.pack(anchor="w")
        c.bind("<<ComboboxSelected>>", self._caged_option_changed)

        self.forms_options = tk.Frame(quiz_card, bg=PANEL)
        self.forms_kind_choice = tk.StringVar(value=self.forms_kind)
        self.forms_key_choice = tk.StringVar(value=NOTE_EN[self.forms_key])
        self.forms_quality_choice = tk.StringVar(value=self.forms_voice if self.forms_kind == "Power chord" else self.forms_quality)
        self.forms_strings_choice = tk.StringVar(value=f"{self.forms_root_string}-я" if self.forms_kind == "Power chord" else self.forms_string_set)
        self.forms_inv_choice = tk.StringVar(value=TRIAD_INVERSIONS[self.forms_inversion])
        self.form_label_choice = tk.StringVar(value=self.form_label_view)
        self._forms_groups = []
        self._forms_combos = []
        for title,variable,options,cbwidth in (
                ("Тип", self.forms_kind_choice, ["Power chord", "Трезвучие"], 14),
                ("Key", self.forms_key_choice, list(NOTE_EN), 6),
                ("Форма", self.forms_quality_choice, [], 16),
                ("Струны", self.forms_strings_choice, [], 12),
                ("Обращение", self.forms_inv_choice, list(TRIAD_INVERSIONS), 17),
                ("Подписи", self.form_label_choice, ["Ноты", "Ступени", "Пальцы"], 11)):
            group = tk.Frame(self.forms_options, bg=PANEL)
            self._forms_groups.append(group)
            self._label(group, title, 9, MUTED).pack(anchor="w")
            combo = ttk.Combobox(group, textvariable=variable, values=options,
                                 state="readonly", width=cbwidth)
            combo.pack(anchor="w")
            combo.bind("<<ComboboxSelected>>", self._forms_option_changed)
            self._forms_combos.append(combo)
        for i, group in enumerate(self._forms_groups):
            group.grid(row=i//3, column=i%3, sticky="w", padx=(0,8), pady=(2,0))
        self._refresh_forms_options()
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
        self._layout_scale_options(self.root.winfo_width())
        self._layout_forms_options(self.root.winfo_width(), self.root.winfo_height())
        self.root.bind("<Configure>", self._resize_main, add="+")

    def _resize_main(self, event) -> None:
        if event.widget is self.root:
            self._layout_toolbar(event.width)
            self._layout_content()
            self._layout_scale_options(event.width)
            self._layout_forms_options(event.width, event.height)

    def _layout_scale_options(self, width: int) -> None:
        # Two rows prevent four scale controls clipping in side-by-side layout.
        for group in self._scale_groups:
            group.grid_forget()
        for idx, group in enumerate(self._scale_groups):
            group.grid(row=idx // 2, column=idx % 2, sticky='w',
                       padx=(0, 7), pady=(2, 0))

    def _layout_forms_options(self, width: int, height: int) -> None:
        cols = 2 if (height < 710 and width < 1250) else 3
        for index, group in enumerate(self._forms_groups):
            group.grid_forget()
            group.grid(row=index // cols, column=index % cols, sticky="w",
                       padx=(0, 6), pady=(2, 0))

    def _layout_toolbar(self, width: int) -> None:
        """Fit the actual controls, rather than using hard-coded breakpoints.

        At a normal desktop width all four groups stay on one row. On narrow
        windows the controls reflow into two readable rows, and a third row is
        used only if larger system fonts/DPI make the navigation too wide.
        No widget gets hidden or clipped to force a particular arrangement.
        """
        # Toolbar has an outside 10px margin, 9px inner padding, and a border
        # on each side. Leave a little breathing room for window decorations.
        available = max(0, width - 2 * (10 + 9 + 1) - 6)
        self.toolbar.update_idletasks()
        primary_width = self.counter_primary.winfo_reqwidth()
        secondary_width = self.counter_secondary.winfo_reqwidth()
        stack_counters = primary_width + secondary_width > available
        orientation = "stacked" if stack_counters else "inline"
        if orientation != getattr(self, "_counter_orientation", None):
            self.counter_primary.pack_forget()
            self.counter_secondary.pack_forget()
            if stack_counters:
                self.counter_primary.pack(side="top", anchor="w")
                self.counter_secondary.pack(side="top", anchor="w", pady=(3, 0))
            else:
                self.counter_primary.pack(side="left")
                self.counter_secondary.pack(side="left")
            self._counter_orientation = orientation
            self.counter_strip.update_idletasks()

        brand_width = self.brand.winfo_reqwidth()
        mode_width = self.mode_strip.winfo_reqwidth()
        utility_width = self.utility_strip.winfo_reqwidth()
        counter_width = self.counter_strip.winfo_reqwidth()
        full_width = brand_width + counter_width + mode_width + utility_width + 3 * 8
        navigation_width = brand_width + mode_width + utility_width + 2 * 10
        if full_width <= available:
            layout = "single"
        elif navigation_width <= available and counter_width <= available:
            layout = "double"
        else:
            layout = "triple"
        if (layout, orientation) == self._toolbar_layout:
            return
        self._toolbar_layout = (layout, orientation)

        for widget in (self.brand, self.counter_strip, self.mode_strip, self.utility_strip):
            widget.grid_forget()
        for row in range(3):
            self.toolbar.grid_rowconfigure(row, weight=0, minsize=0)
        for col in range(4):
            self.toolbar.grid_columnconfigure(col, weight=0, minsize=0)

        if layout == "single":
            self.toolbar.grid_columnconfigure(3, weight=1)
            self.brand.grid(row=0, column=0, sticky="w", padx=(0, 8))
            self.counter_strip.grid(row=0, column=1, sticky="w", padx=(0, 8))
            self.mode_strip.grid(row=0, column=2, sticky="w", padx=(0, 8))
            self.utility_strip.grid(row=0, column=3, sticky="e")
        elif layout == "double":
            self.toolbar.grid_columnconfigure(1, weight=1)
            self.brand.grid(row=0, column=0, sticky="w")
            self.mode_strip.grid(row=0, column=1, sticky="w", padx=(10, 10))
            self.utility_strip.grid(row=0, column=2, sticky="e")
            self.counter_strip.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))
        else:
            self.toolbar.grid_columnconfigure(1, weight=1)
            self.brand.grid(row=0, column=0, sticky="w")
            self.utility_strip.grid(row=0, column=1, sticky="e")
            self.mode_strip.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
            self.counter_strip.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def _layout_content(self) -> None:
        width, height = self.root.winfo_width(), self.root.winfo_height()
        orientation = "side" if height < 710 or width >= 1250 else "stack"
        if orientation == self._responsive_orientation:
            if orientation == "side":
                self.content_area.grid_columnconfigure(1, minsize=300 if width < 900 else 0)
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
            area.grid_columnconfigure(1, weight=0 if width < 900 else 1,
                                      minsize=300 if width < 900 else 0)
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
        self._cancel_ear_sound()
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
        window.title("vGUITAR — Настройки")
        sw, sh = window.winfo_screenwidth(), window.winfo_screenheight()
        window.geometry(f"{min(560, sw - 40)}x{min(620, sh - 85)}")
        window.minsize(495, 450)
        window.transient(self.root)
        window.grab_set()
        frame = tk.Frame(window, bg=PANEL, padx=12, pady=12)
        frame.pack(fill="both", expand=True, padx=9, pady=9)

        # Two tabs keep the configuration window within laptop screen height.
        tabs = ttk.Notebook(frame)
        tabs.pack(fill="both", expand=True)
        tuning_tab = tk.Frame(tabs, bg=PANEL, padx=15, pady=12)
        audio_tab = tk.Frame(tabs, bg=PANEL, padx=15, pady=12)
        fret_tab = tk.Frame(tabs, bg=PANEL, padx=15, pady=12)
        tabs.add(tuning_tab, text="Строй")
        tabs.add(audio_tab, text="Аудио")
        tabs.add(fret_tab, text="Гриф")
        self._label(fret_tab, "Накладка грифа", 13, TEXT, True).pack(anchor="w")
        theme_name = {key: p["name"] for key, p in FRETBOARD_THEMES.items()}
        theme_by_name = {v: k for k, v in theme_name.items()}
        wood_var = tk.StringVar(value=theme_name[self.fretboard_theme])
        wood_combo = ttk.Combobox(fret_tab, state="readonly", textvariable=wood_var,
                                  values=list(theme_by_name), width=24)
        wood_combo.pack(fill="x", pady=(12, 10))
        self._label(fret_tab, "Цвета меняют только накладку, не интерфейс теста.", 9, MUTED).pack(anchor="w")
        swatches = tk.Frame(fret_tab, bg=PANEL)
        swatches.pack(fill="x", pady=(12, 0))
        for key, theme in FRETBOARD_THEMES.items():
            tile = tk.Frame(swatches, bg=theme["neck"], width=90, height=42,
                            highlightbackground=BORDER, highlightthickness=1)
            tile.pack(side="left", padx=(0, 7))
            tile.pack_propagate(False)
        def preview_wood(event=None):
            self.fretboard_theme = theme_by_name.get(wood_var.get(), "default")
            self._draw_board()
        wood_combo.bind("<<ComboboxSelected>>", preview_wood)
        original_wood = self.fretboard_theme

        chosen_preset = tk.StringVar(value=self.preset_name)
        self._label(tuning_tab, "Строй", 13, TEXT, True).pack(anchor="w")
        preset_combo = ttk.Combobox(tuning_tab, state="readonly", textvariable=chosen_preset,
                                    values=[*TUNINGS, CUSTOM_TUNING])
        preset_combo.pack(fill="x", pady=(6, 12))
        note_choices = [midi_label(n) for n in range(24, 97)]
        midi_values = [tk.StringVar(value=midi_label(n)) for n in self.tuning]
        rows = tk.Frame(tuning_tab, bg=PANEL)
        rows.pack(fill="x")
        updating = False
        def preset_changed(event=None):
            nonlocal updating
            if chosen_preset.get() in TUNINGS:
                updating = True
                for v, midi in zip(midi_values, TUNINGS[chosen_preset.get()]):
                    v.set(midi_label(midi))
                updating = False
        def note_changed(event=None):
            if not updating:
                chosen_preset.set(CUSTOM_TUNING)
        preset_combo.bind('<<ComboboxSelected>>', preset_changed)
        for i, var in enumerate(midi_values):
            line = tk.Frame(rows, bg=PANEL)
            line.pack(fill="x", pady=3)
            self._label(line, f"{i + 1}-я струна", 10, TEXT, width=12, anchor='w').pack(side="left")
            combo = ttk.Combobox(line, state='readonly', textvariable=var,
                                 values=note_choices, width=19)
            combo.pack(side='left', padx=8)
            combo.bind('<<ComboboxSelected>>', note_changed)

        self._label(audio_tab, "Аудиоустройство", 13, TEXT, True).pack(anchor="w")
        device_choices: dict[str, str] = {}
        selected_id = self.audio.output_id
        device_var = tk.StringVar()
        device_box = ttk.Combobox(audio_tab, textvariable=device_var, state='readonly')
        def refresh_outputs() -> None:
            device_choices.clear()
            device_choices['Авто · WASAPI'] = ''
            for device in self.audio.list_outputs():
                title = f"{device['name']} · {device['hostapi']}"
                if title in device_choices:
                    title += f" #{device['index']}"
                device_choices[title] = device['id']
            device_box.configure(values=list(device_choices))
            matching = next((k for k, v in device_choices.items() if v == selected_id),
                            'Авто · WASAPI')
            device_var.set(matching)
        device_box.pack(fill="x", pady=(9, 7))
        refresh_outputs()
        refresh_button = self._button(audio_tab, 'Обновить список', refresh_outputs, compact=True)
        refresh_button.pack(anchor='w', pady=(0, 12))
        Tooltip(device_box, 'PortAudio outputs. Auto prefers the Windows WASAPI default.')

        volume = tk.IntVar(value=self.audio.volume)
        self._label(audio_tab, 'Громкость', 10, TEXT, True).pack(anchor='w')
        tk.Scale(audio_tab, from_=0, to=100, resolution=1, orient='horizontal',
                 variable=volume, bg=PANEL, fg=TEXT, troughcolor=CELL_ACTIVE,
                 highlightthickness=0, activebackground=ACCENT).pack(fill='x')
        setting_line = tk.Frame(audio_tab, bg=PANEL)
        setting_line.pack(fill='x', pady=(12, 8))
        self._label(setting_line, 'Задержка', 10, MUTED).grid(row=0, column=0, sticky='w')
        self._label(setting_line, 'Буфер', 10, MUTED).grid(row=0, column=1, sticky='w', padx=(14, 0))
        latency_var = tk.StringVar(value='Надёжная' if self.audio.latency == 'high' else 'Низкая')
        ttk.Combobox(setting_line, values=['Надёжная', 'Низкая'], state='readonly',
                     textvariable=latency_var, width=19).grid(row=1, column=0, sticky='ew', pady=4)
        block_values = {'Авто': 0, '256': 256, '512': 512, '1024': 1024, '2048': 2048}
        block_var = tk.StringVar(value=next((k for k, v in block_values.items()
                                             if v == self.audio.blocksize), 'Авто'))
        ttk.Combobox(setting_line, values=list(block_values), state='readonly',
                     textvariable=block_var, width=15).grid(row=1, column=1, sticky='ew', padx=(14, 0), pady=4)
        setting_line.grid_columnconfigure(0, weight=1)
        setting_line.grid_columnconfigure(1, weight=1)
        exclusive_var = tk.BooleanVar(value=self.audio.exclusive)
        tk.Checkbutton(audio_tab, text='WASAPI Exclusive', variable=exclusive_var,
                       bg=PANEL, fg=TEXT, selectcolor=BUTTON_BG, activebackground=PANEL,
                       activeforeground=TEXT).pack(anchor='w', pady=(4, 3))
        self._label(audio_tab, 'Shared: по умолчанию · Exclusive: устройство занято только vGUITAR',
                    9, MUTED).pack(anchor='w')

        original = (self.audio.output_id, self.audio.latency, self.audio.blocksize,
                    self.audio.exclusive, self.audio.volume)
        def chosen_audio() -> tuple[str, str, int, bool]:
            return (device_choices.get(device_var.get(), ''),
                    'low' if latency_var.get() == 'Низкая' else 'high',
                    block_values[block_var.get()], exclusive_var.get())
        def apply_audio() -> bool:
            try:
                ident, latency, buffer, exclusive = chosen_audio()
                self.audio.configure_output(output_id=ident, latency=latency,
                                            blocksize=buffer, exclusive=exclusive)
                self.audio.volume = volume.get()
                return True
            except (ValueError, OSError, RuntimeError) as exc:
                messagebox.showerror('Аудио', str(exc), parent=window)
                return False
        def test_audio() -> None:
            if apply_audio():
                self._preview_audio(note_choices.index(midi_values[5].get()) + 24, volume.get())
        def restore() -> None:
            self.fretboard_theme = original_wood
            self._draw_board()
            ident, latency, buffer, exclusive, old_volume = original
            try:
                self.audio.configure_output(output_id=ident, latency=latency,
                                            blocksize=buffer, exclusive=exclusive)
            except ValueError:
                pass
            self.audio.volume = old_volume
            window.destroy()
        def apply_settings() -> None:
            if not apply_audio():
                return
            self.fretboard_theme = theme_by_name.get(wood_var.get(), "default")
            new_tuning = tuple(note_choices.index(v.get()) + 24 for v in midi_values)
            new_preset = chosen_preset.get()
            try:
                write_settings(settings_path(), new_preset, new_tuning, volume.get())
            except OSError as exc:
                self.study_message = f'Не удалось сохранить строй: {exc}'
            changed = new_tuning != self.tuning
            self.preset_name, self.tuning = new_preset, new_tuning
            self._save_preferences()
            if changed:
                self.show_map('Строй изменён. Изучи обновлённые ноты перед тестом.')
            else:
                self._update_all()
            window.destroy()

        bottom = tk.Frame(frame, bg=PANEL)
        bottom.pack(fill='x', pady=(10, 0))
        self._button(bottom, '♫ Тест', test_audio, compact=True).pack(side='left')
        self._button(bottom, 'Лог звука', self._copy_audio_diagnostic, compact=True).pack(side='left', padx=6)
        self._button(bottom, 'Сохранить', apply_settings, primary=True).pack(side='right')
        self._button(bottom, 'Отмена', restore).pack(side='right', padx=7)
        window.protocol('WM_DELETE_WINDOW', restore)

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
        if not hasattr(self, '_counter_boxes'):
            self._counter_boxes = {}
        self._counter_boxes[kind] = box
        box.pack(side="left", padx=(0, 3))
        row = tk.Frame(box, bg=PANEL)
        row.pack(anchor="w")
        self._label(row, label, 9, MUTED).pack(side="left", padx=(0, 2))
        minus = self._button(row, "−", lambda: self.change_setting(kind, -step), compact=True)
        minus.configure(padx=3)
        minus.pack(side="left")
        value = self._label(row, "", 10, TEXT, True, width=2)
        value.pack(side="left", padx=1)
        plus = self._button(row, "+", lambda: self.change_setting(kind, step), compact=True)
        plus.configure(padx=3)
        plus.pack(side="left")
        Tooltip(box, {"strings": "Счётчик: 6-я, затем 5-я и так далее. Для одной струны — «Выбор…».",
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

    def _selected_rows(self) -> tuple[int, ...]:
        # Legacy stubs/settings without an explicit selection still work.
        selected = getattr(self, "selected_strings", strings_from_count(self.active_strings))
        return rows_for_strings(selected)

    def _active(self, row: int) -> bool:
        return getattr(self, "mode", "name") in ("scale", "caged", "forms") or row in self._selected_rows()

    def open_string_picker(self) -> None:
        """Select individual physical strings for Name / Find / Ear lessons."""
        old_window = getattr(self, "_string_picker_window", None)
        if old_window is not None and old_window.winfo_exists():
            old_window.lift()
            return
        window = tk.Toplevel(self.root, bg=BG)
        self._string_picker_window = window
        window.title("vGUITAR — Выбор струн")
        window.resizable(False, False)
        window.transient(self.root)
        panel = tk.Frame(window, bg=PANEL, padx=16, pady=14)
        panel.pack(fill="both", expand=True)
        self._label(panel, "Какие струны тренировать?", 12, TEXT, True).pack(anchor="w", pady=(0, 4))
        self._label(panel, "Можно выбрать одну или несколько. Нужна хотя бы одна.",
                    9, MUTED).pack(anchor="w", pady=(0, 9))
        options = tk.Frame(panel, bg=PANEL)
        options.pack(anchor="w")
        variables = {}
        for i, number in enumerate((6, 5, 4, 3, 2, 1)):
            var = tk.BooleanVar(master=window, value=number in self.selected_strings)
            variables[number] = var
            tk.Checkbutton(
                options, text=f"{number}-я · {STRINGS[number-1][1]}",
                variable=var, bg=PANEL, fg=TEXT, activebackground=PANEL,
                activeforeground=TEXT, selectcolor=BG, font=(FONT, 11),
                bd=0, highlightthickness=0, anchor="w",
            ).grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 12), pady=5)
        self._string_picker_vars = variables
        buttons = tk.Frame(panel, bg=PANEL)
        buttons.pack(fill="x", pady=(13, 0))

        def apply() -> None:
            chosen = [number for number in (6, 5, 4, 3, 2, 1) if variables[number].get()]
            if not chosen:
                messagebox.showwarning("Выбор струн", "Нужно выбрать хотя бы одну струну.", parent=window)
                return
            self.selected_strings = normalize_selected_strings(chosen)
            self.active_strings = len(self.selected_strings)
            window.destroy()
            self._save_preferences()
            self.show_map("Выбранные струны изменены")

        self._button(buttons, "Отмена", window.destroy, compact=True).pack(side="right")
        self._button(buttons, "Применить", apply, primary=True, compact=True).pack(side="right", padx=(0, 8))
        window.bind("<Return>", lambda event: apply())
        window.grab_set()
        window.focus_set()

    def _scale_active_fret(self, fret: int) -> bool:
        left,right = self._scale_area()
        return left <= fret <= right

    def change_setting(self, kind: str, delta: int) -> None:
        if kind == "strings":
            count = max(1, min(6, self.active_strings + delta))
            if count != self.active_strings:
                self.selected_strings = strings_from_count(count)
                self.active_strings = count
        elif kind == "frets":
            self.active_frets = max(1, min(24, self.active_frets + delta))
        elif kind == "questions":
            self.question_count = max(5, min(100, self.question_count + delta))
        elif kind == "study":
            self.study_seconds = max(10, min(300, self.study_seconds + delta))
        self._save_preferences()
        self.show_map("Параметры изменены")

    def change_mode(self, mode: str) -> None:
        if mode not in ("name","find","ear","scale","caged","forms"):
            raise ValueError("Unknown mode")
        self.mode = mode
        self.board.xview_moveto(0)
        self._save_preferences()
        self.show_map("Режим изменён")

    def _refresh_scale_choices(self) -> None:
        if self.scale_view == "box":
            names = shape_names(self.scale_name)
            self.scale_box = max(1, min(self.scale_box, len(names)))
            self._scale_comboboxes[3].config(values=["Авто", *names], state="readonly")
            self.scale_position_choice.set("Авто" if self.scale_box_mode == "auto"
                                           else names[self.scale_box - 1])
        elif self.scale_view == "range":
            self._scale_comboboxes[3].config(values=["Авто", *[str(n) for n in range(21)]], state="readonly")
            self.scale_position_choice.set("Авто" if self.scale_position_mode == "auto"
                                           else str(self.scale_position))
        else:
            self._scale_comboboxes[3].config(values=["0–24"], state="disabled")
            self.scale_position_choice.set("0–24")

    def _scale_option_changed(self, event=None) -> None:
        previous_scale = self.scale_name
        self.scale_name = self.scale_choice.get()
        self.scale_key = NOTE_EN.index(self.scale_key_choice.get())
        view = {"Аппликатуры":"box", "Весь звукоряд":"full",
                "Участок ладов":"range"}.get(self.scale_view_choice.get(), "range")
        # Every scale now has its own fingering family; legacy fret ranges
        # still exist separately and are never presented as canonical boxes.
        if self.scale_name != previous_scale and (event is None or event.widget is self._scale_comboboxes[0]):
            if view == "range":
                view = "box"
        if view == "box" and self.scale_name not in FINGERING_SCALES:
            view = "range"
        changed_view = self.scale_view != view
        self.scale_view = view
        self.scale_view_choice.set({"box":"Аппликатуры", "full":"Весь звукоряд",
                                    "range":"Участок ладов"}[view])
        if not changed_view:
            selected = self.scale_position_choice.get()
            if view == "box":
                names = shape_names(self.scale_name)
                if selected in names:
                    self.scale_box_mode, self.scale_box = "manual", names.index(selected) + 1
                elif selected == "Авто":
                    self.scale_box_mode = "auto"
            elif view == "range":
                if selected == "Авто":
                    self.scale_position_mode = "auto"
                    self.scale_position = auto_scale_position(self.tuning, self.scale_name,
                                                              self.scale_key, previous=self.scale_position)
                elif selected.isdigit():
                    self.scale_position_mode, self.scale_position = "manual", int(selected)
        self._refresh_scale_choices()
        self._save_preferences()
        self.show_map("Гамма или аппликатура изменена")

    def _scale_items(self) -> list[tuple[int, int, int, str]]:
        if self.scale_view == "box":
            return scale_fingering(self.tuning, self.scale_name, self.scale_key, self.scale_box)
        if self.scale_view == "range":
            return scale_positions(self.tuning, self.scale_name, self.scale_key, self.scale_position)
        allowed, labels = scale_pattern(self.scale_name, self.scale_key)
        degrees = {pc: label if label != "8" else "1" for pc,label in zip(allowed,labels)}
        return [(r,f,self._pitch(r,f),degrees[self._pitch_class(r,f)])
                for r in range(5,-1,-1) for f in range(25)
                if self._pitch_class(r,f) in degrees]

    def _caged_option_changed(self, event=None) -> None:
        self.caged_key = NOTE_EN.index(self.caged_key_choice.get())
        self.caged_view = {"Аккорд":"chord", "Мажорная гамма":"major",
                           "Минорная гамма":"minor"}.get(self.caged_view_choice.get(), "chord")
        value = self.caged_form_choice.get()
        self.caged_form_mode = "auto" if value == "Авто" else "manual"
        if self.caged_form_mode == "manual":
            self.caged_form = value
        self._save_preferences()
        self.show_map("Аккорд или форма изменены")

    def _caged_shape(self) -> list[tuple[int, int, int, str]]:
        if self.caged_view == "chord":
            return caged_positions(self.tuning, self.caged_key, self.caged_form)
        return caged_scale(self.tuning, self.caged_key, self.caged_form, self.caged_view == "minor")

    def _refresh_forms_options(self) -> None:
        if self.forms_kind == "Power chord":
            self._forms_combos[2].config(values=POWER_VOICES)
            self.forms_quality_choice.set(self.forms_voice)
            self._forms_combos[3].config(values=["6-я", "5-я", "4-я"])
            self.forms_strings_choice.set(f"{self.forms_root_string}-я")
            self._forms_combos[4].config(state="disabled")
        else:
            self._forms_combos[2].config(values=list(TRIAD_QUALITIES))
            self.forms_quality_choice.set(self.forms_quality)
            self._forms_combos[3].config(values=["1–2–3", "2–3–4", "3–4–5", "4–5–6"])
            self.forms_strings_choice.set(self.forms_string_set)
            self._forms_combos[4].config(state="readonly")
        self.forms_inv_choice.set(TRIAD_INVERSIONS[self.forms_inversion])

    def _forms_option_changed(self, event=None) -> None:
        chosen = self.forms_kind_choice.get()
        switched = chosen != self.forms_kind
        self.forms_kind = chosen
        self.forms_key = NOTE_EN.index(self.forms_key_choice.get())
        if switched:
            self._refresh_forms_options()
        elif chosen == "Power chord":
            self.forms_voice = self.forms_quality_choice.get()
            self.forms_root_string = int(self.forms_strings_choice.get()[0])
        else:
            self.forms_quality = self.forms_quality_choice.get()
            self.forms_string_set = self.forms_strings_choice.get()
            self.forms_inversion = TRIAD_INVERSIONS.index(self.forms_inv_choice.get())
        self.form_label_view = self.form_label_choice.get()
        self._save_preferences()
        self.show_map("Аккордовая аппликатура изменена")

    def _forms_shape(self) -> list[tuple[int, int, int, str]]:
        if self.forms_kind == "Power chord":
            return power_chord(self.tuning, self.forms_key, self.forms_root_string, self.forms_voice)
        return triad_voicing(self.tuning, self.forms_key, self.forms_quality,
                             self.forms_string_set, self.forms_inversion)

    def _scale_area(self) -> tuple[int,int]:
        if self.scale_view == "full":
            return 0, 24
        if self.scale_view == "box":
            try:
                frets = [f for _r, f, _m, _d in self._scale_items()]
                return min(frets), max(frets)
            except ValueError:
                return 0, 12
        return self.scale_position, min(24,self.scale_position+SCALE_POSITION_SPAN-1)

    def _board_frets(self) -> int:
        if self.mode == "forms":
            try:
                return max(7, min(24, max(f for _, f, _, _ in self._forms_shape()) + 1))
            except ValueError:
                return max(12, self.active_frets)
        if self.mode == "caged":
            try:
                return max(12, min(24, max(f for _, f, _, _ in self._caged_shape()) + 1))
            except ValueError:
                return max(12, self.active_frets)
        return self._scale_area()[1] if self.mode == "scale" else self.active_frets

    def show_map(self, message: Optional[str] = None) -> None:
        """Preparation shows the working note map; timed study stays optional."""
        self._cancel_ear_sound()
        self._cancel_study_timer()
        if self.mode == "caged" and self.caged_form_mode == "auto" and self.phase == "result":
            self.caged_form = next_caged_form(self.caged_form)
        if self.mode == "scale" and self.phase == "result":
            if self.scale_view == "box" and self.scale_box_mode == "auto":
                self.scale_box = next_shape(self.scale_name, self.scale_box)
                self._refresh_scale_choices()
            elif self.scale_view == "range" and self.scale_position_mode == "auto":
                self.scale_position = auto_scale_position(self.tuning, self.scale_name,
                                                          self.scale_key, previous=self.scale_position)
        self.phase = "ready"
        self.checked = False
        self.guess_fret = None
        self.study_message = message or "Готов к повторению?"
        self._update_all()

    def start_study(self) -> None:
        if self.mode == "forms":
            try:
                self._forms_shape()
            except ValueError as exc:
                messagebox.showwarning("Форма недоступна", str(exc), parent=self.root)
                return
        if self.mode == "caged":
            try:
                self._caged_shape()
            except ValueError as exc:
                messagebox.showwarning("CAGED недоступен", str(exc), parent=self.root)
                return
        if self.mode == "scale":
            try:
                self._scale_items()
            except ValueError:
                messagebox.showwarning("Позиция недоступна",
                    "Аппликатура недоступна для этого строя или диапазона ладов. "
                    "Для нестандартного строя попробуй «Участок ладов» или «Весь звукоряд».",
                    parent=self.root)
                return
        self._cancel_study_timer()
        self.phase = "study"
        # Start WASAPI early and pre-render the exact working-area pitches while
        # the student studies the fretboard. All computation stays off Tk's thread.
        self.audio.preload(([midi for _, _, midi, _ in self._scale_items()]
                            if self.mode == "scale" else
                            [midi for _, _, midi, _ in self._forms_shape()]
                            if self.mode == "forms" else
                            [self._pitch(row, fret) for row in range(6) if self._active(row)
                             for fret in range(self._board_frets() + 1)]))
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
        if self.mode == "forms":
            self.forms_steps = self._forms_shape()
            return [Question(row, fret) for row,fret,_,_ in self.forms_steps]
        if self.mode == "caged":
            self.caged_steps = self._caged_shape()
            return [Question(row, fret) for row, fret, _, _ in self.caged_steps]
        if self.mode == "scale":
            self.scale_steps = self._scale_items()
            return [Question(row,fret) for row,fret,_,_ in self.scale_steps]
        pool = [Question(row, fret)
                for row in self._selected_rows()
                for fret in range(self.active_frets + 1)]
        if self.mode == "ear":
            # One MIDI pitch per question: never require guessing which of two
            # equivalent string/fret positions was chosen by the generator.
            unique_midi: dict[int, Question] = {}
            for q in pool:
                unique_midi.setdefault(self._pitch(q.row, q.fret), q)
            pool = list(unique_midi.values())
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

    def _cancel_ear_sound(self) -> None:
        if self._ear_sound_after_id is not None:
            try:
                self.root.after_cancel(self._ear_sound_after_id)
            except tk.TclError:
                pass
        self._ear_sound_after_id = None

    def _play_ear_question(self) -> None:
        self._ear_sound_after_id = None
        if self.phase == "quiz" and self.mode == "ear" and not self.checked:
            q = self._current()
            self.audio.play(self._pitch(q.row, q.fret))

    def _schedule_ear_question(self) -> None:
        self._cancel_ear_sound()
        if self.phase == "quiz" and self.mode == "ear" and not self.checked:
            self._ear_sound_after_id = self.root.after(20, self._play_ear_question)

    def replay_ear_note(self) -> bool:
        if self.phase != "quiz" or self.mode != "ear" or self.checked:
            return False
        if self.ear_replays_used >= EAR_REPLAYS:
            return False
        self.ear_replays_used += 1
        self._cancel_ear_sound()
        self._play_ear_question()
        self._update_quiz_ui()
        return True

    def start_quiz(self) -> None:
        self._cancel_study_timer()
        self._cancel_ear_sound()
        self.run_started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.run_id = uuid4().hex
        self.responses = []
        self.current_run = None
        try:
            self.questions = self._make_questions()
        except ValueError:
            self.show_map("Упражнение недоступно")
            messagebox.showwarning("Позиция недоступна",
                ("Классические формы требуют Standard, E♭ Standard или D Standard."
                 if self.mode in ("caged", "forms") else "Аппликатура недоступна для выбранного строя. "
                 "Используй стандартные интервалы струн или переключись на карту грифа."),
                parent=self.root)
            return
        self.audio.preload([self._pitch(q.row, q.fret) for q in self.questions])
        self.index = 0
        self.correct = 0
        self.mistakes = []
        self.checked = False
        self.guess_fret = None
        self.guess_row = None
        self.ear_replays_used = 0
        self.feedback = ""
        self.phase = "quiz"
        self._update_all()
        self.question_started = time.monotonic()
        self._schedule_ear_question()

    def _current(self) -> Question:
        return self.questions[self.index]

    def _feedback(self, correct: bool, actual_pc: Optional[int] = None) -> None:
        self._cancel_ear_sound()
        q = self._current()
        target_pc = self._pitch_class(q.row, q.fret)
        # Record response BEFORE sound synthesis/UI rendering delays.
        duration = round(max(0.0, time.monotonic() - self.question_started), 3) if self.question_started is not None else 0.0
        self.question_started = None
        self.checked = True
        self.feedback_is_correct = correct
        answer_pc = actual_pc if self.mode in ("find", "ear", "scale", "caged", "forms") else getattr(self, "_chosen_pc", None)
        self.responses.append({
            "index": self.index + 1,
            "mode": self.mode,
            "string_number": int(STRINGS[q.row][0]),
            "fret": q.fret,
            "expected_note": self._note_name(target_pc),
            "expected_midi": self._pitch(q.row, q.fret),
            "answer_note": self._note_name(answer_pc) if answer_pc is not None else None,
            "answer_fret": self.guess_fret if self.mode in ("find", "ear", "scale", "caged", "forms") else None,
            "degree": (self.caged_steps[self.index][3] if self.mode == "caged" else
                       self.forms_steps[self.index][3] if self.mode == "forms" else
                       self.scale_steps[self.index][3] if self.mode == "scale" else None),
            "scale_step": self.index+1 if self.mode == "scale" else None,
            "caged_step": self.index+1 if self.mode == "caged" else None,
            "forms_step": self.index+1 if self.mode == "forms" else None,
            "answer_string_number": (int(STRINGS[self.guess_row][0]) if self.guess_row is not None else None),
            "answer_midi": (self._pitch(self.guess_row, self.guess_fret)
                            if self.guess_row is not None and self.guess_fret is not None else None),
            "replays_used": self.ear_replays_used if self.mode == "ear" else None,
            "correct": bool(correct),
            "response_seconds": duration,
        })
        if correct:
            self.correct += 1
            self.feedback = f"Верно · {self._readable_note(target_pc)} · {duration:.2f} с"
            self.audio.play(self._pitch(self.guess_row, self.guess_fret)
                            if self.mode in ("find", "ear") and self.guess_row is not None and self.guess_fret is not None
                            else self._pitch(q.row, q.fret))
        else:
            n = STRINGS[q.row][0]
            if self.mode == "name":
                self.feedback = f"{self._readable_note(target_pc)} · {duration:.2f} с"
                self.mistakes.append(f"{n}-я струна, лад {q.fret}: {self._readable_note(target_pc)}")
            elif self.mode == "forms":
                degree = self.forms_steps[self.index][3]
                self.feedback = (f"Ступень {degree} · {midi_label(self._pitch(q.row,q.fret))} · "
                                 f"струна {STRINGS[q.row][0]}, лад {q.fret} · {duration:.2f} с")
                self.mistakes.append(f"{self.forms_kind} {NOTE_EN[self.forms_key]} · {self.feedback}")
            elif self.mode == "caged":
                degree = self.caged_steps[self.index][3]
                self.feedback = (f"{INTERVAL_DESCRIPTIONS.get(degree, 'Ступень '+degree)} · {midi_label(self._pitch(q.row, q.fret))} · "
                                 f"струна {STRINGS[q.row][0]}, лад {q.fret} · {duration:.2f} с")
                self.mistakes.append(f"CAGED {NOTE_EN[self.caged_key]} {self.caged_form}-форма · {self.feedback}")
            elif self.mode == "scale":
                correct_midi = self._pitch(q.row,q.fret)
                self.feedback = (f"{midi_label(correct_midi)} · струна {STRINGS[q.row][0]}, "
                                 f"лад {q.fret} · {duration:.2f} с")
                self.mistakes.append(f"{self.scale_name} · {NOTE_EN[self.scale_key]} · {self.feedback}")
            elif self.mode == "ear":
                positions = [(int(STRINGS[r][0]), fret)
                             for r in self._selected_rows()
                             for fret in range(self.active_frets + 1)
                             if self._pitch(r, fret) == self._pitch(q.row, q.fret)]
                options = ", ".join(f"{string}-я/{fret}" for string, fret in positions)
                self.feedback = (f"{self._readable_note(target_pc)} · {midi_label(self._pitch(q.row, q.fret))} "
                                 f"(позиции: {options}) · {duration:.2f} с")
                self.mistakes.append(f"На слух: {self.feedback}")
            else:
                valid = [f for f in range(self.active_frets + 1)
                         if self._pitch_class(q.row, f) == target_pc]
                frets = ", ".join(map(str, valid))
                self.feedback = (f"{self._readable_note(actual_pc)} → {self._readable_note(target_pc)} "
                                 f"(лад: {frets}) · {duration:.2f} с")
                self.mistakes.append(f"{n}-я струна: найти {self._readable_note(target_pc)} (лады {frets})")
            self.audio.play(self._pitch(self.guess_row, self.guess_fret)
                            if self.guess_row is not None and self.guess_fret is not None
                            else self._pitch(q.row, q.fret), buzzing=True)
        self._update_all()

    def answer_name(self, pitch_class: int) -> None:
        if self.phase != "quiz" or self.checked or self.mode != "name":
            return
        self._chosen_pc = pitch_class
        self._feedback(pitch_class == self._pitch_class(self._current().row, self._current().fret))

    def _click_board(self, event: tk.Event) -> None:
        x = self.board.canvasx(event.x)
        fret = fret_from_x(x, self.cell_width)
        row = int((event.y - TOP) // ROW_H)
        if not (0 <= fret <= self._board_frets() and 0 <= row < 6 and self._active(row)):
            return
        if self.mode == "scale" and not self._scale_active_fret(fret):
            return
        if self.phase == "ready" or (self.phase == "study" and self.study_deadline is not None
                                      and time.monotonic() < self.study_deadline):
            self.audio.play(self._pitch(row, fret))
            return
        if self.phase != "quiz" or self.checked or self.mode not in ("find", "ear", "scale", "caged", "forms"):
            return
        q = self._current()
        if self.mode == "find" and row != q.row:
            return  # In this mode a target string is specified.
        self.guess_fret = fret
        self.guess_row = row
        pc = self._pitch_class(row, fret)
        correct = ((row, fret) == (q.row, q.fret) if self.mode in ("scale", "caged") else
                   self._pitch(row, fret) == self._pitch(q.row, q.fret) if self.mode == "ear" else
                   pc == self._pitch_class(q.row, q.fret))
        self._feedback(correct, actual_pc=pc)

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
        self.guess_row = None
        self.ear_replays_used = 0
        self.feedback = ""
        if self.index >= len(self.questions):
            self.phase = "result"
            self._finish_run()
        self._update_all()
        if self.phase == "quiz":
            self.question_started = time.monotonic()
            self._schedule_ear_question()

    def _finish_run(self) -> None:
        self.current_run = {
            "schema_version": 1,
            "app_version": "0.5.4",
            "run_id": self.run_id,
            "started_at": self.run_started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "configuration": {
                "preset": self.preset_name,
                "tuning_midi": list(self.tuning),
                "active_strings": self.active_strings,
                "selected_strings": list(self.selected_strings),
                "active_frets": self.active_frets,
                "question_count": len(self.questions),
                "study_seconds": self.study_seconds,
                "mode": self.mode,
                "scale": self.scale_name if self.mode == "scale" else None,
                "key": NOTE_EN[self.scale_key] if self.mode == "scale" else None,
                "position_start_fret": self._scale_area()[0] if self.mode == "scale" else None,
                "position_end_fret": self._scale_area()[1] if self.mode == "scale" else None,
                "position_mode": (self.scale_box_mode if self.scale_view == "box" else
                                  self.scale_position_mode if self.scale_view == "range" else "full")
                                 if self.mode == "scale" else None,
                "scale_shape_notes": len(self.scale_steps) if self.mode == "scale" else None,
                "caged_key": NOTE_EN[self.caged_key] if self.mode == "caged" else None,
                "caged_form": self.caged_form if self.mode == "caged" else None,
                "caged_view": self.caged_view if self.mode == "caged" else None,
                "forms_kind": self.forms_kind if self.mode == "forms" else None,
                "forms_key": NOTE_EN[self.forms_key] if self.mode == "forms" else None,
                "forms_quality": self.forms_quality if self.mode == "forms" and self.forms_kind == "Трезвучие" else None,
                "forms_voice": self.forms_voice if self.mode == "forms" and self.forms_kind == "Power chord" else None,
                "forms_root_string": self.forms_root_string if self.mode == "forms" and self.forms_kind == "Power chord" else None,
                "forms_string_set": self.forms_string_set if self.mode == "forms" and self.forms_kind == "Трезвучие" else None,
                "forms_inversion": TRIAD_INVERSIONS[self.forms_inversion] if self.mode == "forms" and self.forms_kind == "Трезвучие" else None,
                "forms_shape_notes": len(self.forms_steps) if self.mode == "forms" else None,
                "form_label_view": self.form_label_view if self.mode in ("caged", "forms") else None,
                "caged_form_mode": self.caged_form_mode if self.mode == "caged" else None,
                "caged_shape_notes": len(self.caged_steps) if self.mode == "caged" else None,
                "scale_view": self.scale_view if self.mode == "scale" else None,
                "scale_box": self.scale_box if self.mode == "scale" and self.scale_view == "box" else None,
                "scale_shape_family": shape_family(self.scale_name) if self.mode == "scale" and self.scale_view == "box" else None,
                "scale_shape_label": shape_names(self.scale_name)[self.scale_box - 1] if self.mode == "scale" and self.scale_view == "box" else None,
                "scale_box_mode": self.scale_box_mode if self.mode == "scale" and self.scale_view == "box" else None,
                "position_width_frets": (self._scale_area()[1] - self._scale_area()[0] + 1
                                         if self.mode == "scale" else None),
                "fretboard_theme": self.fretboard_theme,
                "ear_max_replays": EAR_REPLAYS if self.mode == "ear" else None,
            },
            "questions": self.responses[:],
        }
        try:
            save_run(self.current_run)
            self._set_status("Результат сохранён в локальной истории")
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
            "5. Итог сохраняется локально. Кнопка «Export Results» копирует JSON.\n"
            "6. Меню «История» позволяет выбрать несколько запусков и копировать их отчёт.\n"
            "Данные занятий сохраняются локально в vguitar/data/ и исключены из Git.", parent=self.root)

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
                {"name": "Нота", "find": "Найти", "ear": "На слух", "scale":"Гаммы"}.get(cfg.get("mode"), "?"),
                (f"{','.join(map(str, cfg['selected_strings']))} стр. / {cfg.get('active_frets','?')} л."
                 if cfg.get("selected_strings") else
                 f"{cfg.get('active_strings','?')} стр. / {cfg.get('active_frets','?')} л."),
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

    def _space_key(self, event: tk.Event) -> str | None:
        if self.phase == "quiz" and self.checked and event.widget.winfo_toplevel() == self.root:
            self.next_question()
            return "break"
        return None

    def _update_all(self) -> None:
        self.footer_label.config(text=f"Строй: {self.preset_name}   •   Esc: подготовка   •   ? Справка в меню")
        self.strings_value.config(text=str(self.active_strings))
        self.string_picker_button.config(text="Выбор: " + ",".join(map(str, self.selected_strings)))
        self.frets_value.config(text=str(self.active_frets))
        self.questions_value.config(text=str(self.question_count))
        self.study_value.config(text=str(self.study_seconds))
        for kind in ("strings","frets","questions"):
            frame = self._counter_boxes[kind]
            if self.mode in ("scale", "caged", "forms"):
                frame.pack_forget()
            elif not frame.winfo_manager():
                frame.pack(side="left",before=self._counter_boxes["study"],padx=(0,7))
        if self.mode in ("scale", "caged", "forms"):
            self.string_picker_button.pack_forget()
        elif not self.string_picker_button.winfo_manager():
            self.string_picker_button.pack(side="left", before=self._counter_boxes["frets"], padx=(0, 7))
        self._update_answer_layout_buttons()
        self.answer_layout_frame.pack_forget()
        self.scale_options.pack_forget()
        self.caged_options.pack_forget()
        self.forms_options.pack_forget()
        if self.mode == "name":
            self.answer_layout_frame.pack(side="right")
        if self.mode == "scale":
            self.scale_options.pack(fill="x",before=self.quiz_body,pady=(4,2))
        if self.mode == "caged":
            self.caged_options.pack(fill="x",before=self.quiz_body,pady=(4,2))
        if self.mode == "forms":
            self.forms_options.pack(fill="x",before=self.quiz_body,pady=(4,2))
        for mode, btn in self.mode_buttons.items():
            selected = (mode == self.mode)
            btn.config(bg=ACCENT if selected else BUTTON_BG,
                       fg="#072139" if selected else TEXT)
        if self.board.winfo_width() > 1:
            self.cell_width = board_base_width(self.board.winfo_width(),self._board_frets())
        self._draw_board()
        self._update_quiz_ui()

    def _board_resized(self, event) -> None:
        usable = max(1, int(event.width))
        # The open-string area stays narrow while fretted cells expand.
        desired = board_base_width(usable,self._board_frets())
        if desired != self.cell_width:
            self.cell_width = desired
            self._draw_board()

    def _draw_board(self) -> None:
        self.board.delete("all")
        self.string_labels.delete("all")
        limit = self._board_frets()
        width = board_width(limit,self.cell_width)
        self.board.configure(scrollregion=(0, 0, width, BOARD_H))
        self.board_heading.config(text="ПОВТОРЕНИЕ" if self.phase == "study" else "ГРИФ")
        self.board_hint.config(text=(
            (f"6/6 · {self.scale_name} · {shape_names(self.scale_name)[self.scale_box-1]}" if self.scale_view == "box"
             else f"6/6 · {self.scale_name} · весь гриф" if self.scale_view == "full"
             else f"6/6 · участок {self.scale_position}–{limit}") if self.mode == "scale"
                                     else f"{NOTE_EN[self.caged_key]} · {self.caged_form}-форма · {self.caged_view}" if self.mode == "caged"
                                     else f"{self.forms_kind} · {NOTE_EN[self.forms_key]}" if self.mode == "forms"
                 else f"Струны {','.join(map(str, self.selected_strings))} · 0–{self.active_frets}"))
        for fret in range(limit + 1):
            self.board.create_text(fret_center(fret,self.cell_width),11,text=str(fret),
                                   fill=TEXT,font=(FONT,13,"bold"),tags=("fret_number",))

        # Continuous fretboard surface.  Only real strings run horizontally:
        # there are no horizontal lane outlines between the strings.
        neck_bottom = TOP + ROW_H * 6
        wood = FRETBOARD_THEMES[self.fretboard_theme]
        self.board.create_rectangle(0, TOP, width, neck_bottom,
                                    fill=wood["neck"], outline='', tags=('fretboard',))
        # The open string is outside the fretted neck, before the real nut.
        self.board.create_rectangle(0, TOP, OPEN_WIDTH - 3, neck_bottom,
                                    fill=wood["open"], outline='', tags=('open_area',))
        for row, (num, _letter, _ru, _pc) in enumerate(STRINGS):
            pc_open = self._pitch_class(row, 0)
            active = self._active(row)
            y0 = TOP + row * ROW_H
            ymid = y0 + ROW_H / 2
            self.string_labels.create_text(4, ymid, text=f'{self._note_name(pc_open)}  {self._note_ru(pc_open)}  {num}',
                                           anchor='w', fill=TEXT if active else FAINT,
                                           font=(FONT, 11, 'bold'),tags=('string_name',))
            if not active:
                self.board.create_rectangle(0, y0, width, y0 + ROW_H,
                                            fill=blend_hex(wood["neck"], wood["inactive"], .40), outline='',
                                            tags=('inactive_overlay',))
        if self.mode == "scale" and self.scale_view != "full":
            left, _right = self._scale_area()
            first = fret_start(left,self.cell_width)
            if first > 0:
                self.board.create_rectangle(0,TOP,first,neck_bottom,
                    fill=blend_hex(wood["neck"],BG,.25),outline='',tags=('outside_position',))
        scale_coords = {}
        if self.mode == "scale":
            try:
                scale_coords = {(r,f): degree for r,f,_m,degree in self._scale_items()}
            except ValueError:
                pass
        form_notes = {}
        finger_labels = {}
        if self.mode == "forms":
            try:
                steps = self._forms_shape()
                form_notes = {(r, f): degree for r,f,_,degree in steps}
                finger_labels = suggested_fingers(steps)
            except ValueError:
                pass
        caged_notes = {}
        if self.mode == "caged":
            try:
                steps = self._caged_shape()
                caged_notes = {(r, f): degree for r, f, _, degree in steps}
                finger_labels = suggested_fingers(steps)
                start = caged_shift(self.tuning, self.caged_key, self.caged_form)
                first = fret_start(start, self.cell_width)
                if first > 0:
                    self.board.create_rectangle(0, TOP, first, neck_bottom,
                        fill=blend_hex(wood["neck"], BG, .20), outline='', tags=('outside_position',))
            except ValueError:
                pass
        # The nut separates fret 0 (open) from fret 1.  Each later fret wire
        # is thinner and does not quite reach the neck's upper/lower edge.
        self.board.create_rectangle(OPEN_WIDTH - 3, TOP + 2, OPEN_WIDTH + 2,
                                    neck_bottom - 2, fill='#d5dfe8', outline='', tags=('nut',))
        for fret in range(2, limit + 1):
            x = fret_start(fret, self.cell_width)
            self.board.create_line(x, TOP + 7, x, neck_bottom - 7,
                                   fill=wood["wire"], width=3, tags=('fret_wire',))
        # Standard guitar position markers: single 3/5/7/9 etc, double 12/24.
        # White markers remain clearly visible even when those strings are grey.
        dot_radius = min(4.7, ROW_H * .15)
        for fret in range(1, limit + 1):
            for cx, cy in fret_inlay_centers(fret, self.cell_width):
                self.board.create_oval(cx - dot_radius, cy - dot_radius,
                                       cx + dot_radius, cy + dot_radius,
                                       fill=wood["dot"], outline=wood["dot_outline"], width=1,
                                       tags=("fret_inlay", f"fret_inlay_{fret}"))

        # Six uninterrupted strings from open-string area to the end of neck.
        string_widths = (1.15, 1.35, 1.65, 2.0, 2.4, 3.1)
        for row, thickness in enumerate(string_widths):
            y = TOP + row * ROW_H + ROW_H / 2
            self.board.create_line(6, y, width - 6, y, width=thickness,
                                   fill=wood["string"] if self._active(row) else wood["muted"],
                                   capstyle=tk.ROUND, tags=('guitar_string', f'guitar_string_{row + 1}'))

        # Foreground: notes and quiz target.  These are true circles, even when
        # the window gets much wider than the nominal fret cells.
        for row, (_num, _letter, _ru, _base_pc) in enumerate(STRINGS):
            active = self._active(row)
            y0 = TOP + row * ROW_H
            ymid = y0 + ROW_H / 2
            for fret in range(limit + 1):
                x0 = fret_start(fret, self.cell_width)
                span = fret_width(fret, self.cell_width)
                center_x = fret_center(fret, self.cell_width)
                disc = note_disc_bbox(center_x, ymid, span)
                pc = self._pitch_class(row, fret)
                is_target = self.phase == "quiz" and self.mode == "name" and not self.checked and (
                    row == self._current().row and fret == self._current().fret)
                show_note = active and self.phase in ("ready", "study")
                if active and self.phase == "quiz" and self.checked:
                    q = self._current()
                    if self.mode == "name" and (row, fret) == (q.row, q.fret):
                        show_note = True
                    if self.mode == "find" and row == q.row and pc == self._pitch_class(q.row, q.fret):
                        show_note = True
                    if (self.mode == "ear" and self._pitch(row, fret) == self._pitch(q.row, q.fret)) or (self.mode in ("scale", "caged", "forms") and (row, fret) == (q.row, q.fret)):
                        show_note = True
                if self.mode == "scale" and self.phase == "quiz" and not self._scale_active_fret(fret):
                    show_note = False
                if show_note:
                    highlight = self.phase == "quiz" and self.checked
                    in_shape = ((row, fret) in caged_notes if self.mode == "caged" else
                                (row, fret) in form_notes if self.mode == "forms" else
                                self.mode != "scale" or (row, fret) in scale_coords)
                    degree = (caged_notes.get((row, fret)) if self.mode == "caged" else
                              form_notes.get((row, fret)) if self.mode == "forms" else None)
                    scale_root = (self.mode == "scale" and in_shape and
                                  scale_coords.get((row, fret)) == "1")
                    scale_blue = (self.mode == "scale" and in_shape and
                                  scale_coords.get((row, fret)) == "♭5" and
                                  self.scale_name == "Блюзовая")
                    special = AMBER if scale_root else "#d3a5ff" if scale_blue else {
                        "1": ACCENT, "8": ACCENT, "3": AMBER, "♭3": AMBER,
                        "5": GREEN, "♭5": GREEN}.get(degree)
                    fill_color = ("#236e70" if highlight else "#2b607f") if in_shape else "#283443"
                    self.board.create_oval(*disc, fill=fill_color,
                                           outline=(GREEN if highlight else special or "#4b9abd") if in_shape else "#475363",
                                           width=2 if degree or scale_root else 1,
                                           tags=("note_disc", "scale_note" if self.mode == "scale" and in_shape
                                                 else "scale_outside" if self.mode == "scale" else "other_note",
                                                  "blue_note" if scale_blue else "ordinary_note"))
                    main_label = self._note_name(pc)
                    sub_label = degree if degree else self._note_ru(pc)
                    if in_shape and self.mode in ("caged", "forms"):
                        if self.form_label_view == "Ступени":
                            main_label, sub_label = degree or main_label, self._note_name(pc)
                        elif self.form_label_view == "Пальцы":
                            main_label, sub_label = finger_labels.get((row,fret), "—"), self._note_name(pc)
                    self.board.create_text(center_x, ymid - 5, text=main_label,
                                           fill=special or (TEXT if in_shape else FAINT), font=(FONT, 10, "bold"))
                    self.board.create_text(center_x, ymid + 7,
                                           text=sub_label,
                                           fill=special or ("#c8e3ef" if in_shape else FAINT), font=(FONT, 7, "bold" if degree else "normal"))
                elif is_target:
                    self.board.create_oval(*disc, fill="#245879", outline=ACCENT,
                                           width=2, tags=("note_disc",))
                    self.board.create_text(center_x, ymid, text="?",
                                           fill=TEXT, font=(FONT, 14, "bold"))
                if active and self.phase == "quiz" and self.mode in ("find", "ear", "scale", "caged", "forms"):
                    q = self._current()
                    if self.mode == "find" and row == q.row and not self.checked:
                        self.board.create_rectangle(x0 + 3, y0 + 3, x0 + span - 3,
                                                    y0 + ROW_H - 3, outline="#4188ad", width=2)
                    if self.checked and row == self.guess_row and fret == self.guess_fret:
                        self.board.create_rectangle(x0 + 2, y0 + 2, x0 + span - 2,
                                                    y0 + ROW_H - 2,
                                                    outline=GREEN if self.feedback_is_correct else RED,
                                                    width=3)
        if self.phase == "quiz":
            q = self._current()
            x0 = fret_start(q.fret, self.cell_width)
            if self.mode == "name":
                self.board.xview_moveto(max(0, x0 - 2 * self.cell_width) / max(width, 1))
            # In find/ear don't reveal the target fret by auto-scrolling.
        if self.mode == "scale":
            left, _right = self._scale_area()
            self.board.xview_moveto(max(0,fret_start(left,self.cell_width)-10)/max(width,1))
        if self.mode == "forms":
            try:
                first = min(f for _, f, _, _ in self._forms_shape())
                self.board.xview_moveto(max(0, fret_start(max(0,first-1), self.cell_width)-10)/max(width,1))
            except ValueError:
                pass
        if self.mode == "caged":
            try:
                start = min(f for _, f, _, _ in self._caged_shape())
                self.board.xview_moveto(max(0, fret_start(max(0, start-1), self.cell_width)-10)/max(width,1))
            except ValueError:
                pass

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

    def _render_find_target(self, pitch_class: int, string: str) -> None:
        """High-contrast answer target: identify the desired note at a glance."""
        accidental = pitch_class in (1, 3, 6, 8, 10)
        emphasis = AMBER if accidental else ACCENT
        heading = "НАЙДИ НОТУ"
        card = tk.Frame(self.quiz_body, bg="#172d43", padx=10, pady=7,
                        highlightthickness=2, highlightbackground=emphasis)
        card.pack(fill="x", pady=(2, 6))
        text_row = tk.Frame(card, bg="#172d43")
        text_row.pack(fill="x")
        self._label(text_row, heading, 9, MUTED, True, bg="#172d43").pack(side="left")
        self._label(text_row, string, 10, TEXT, True, bg="#172d43").pack(side="right")
        note = self._label(card, self._note_name(pitch_class), 32, emphasis, True,
                           bg="#172d43", anchor="center")
        note.pack(fill="x", pady=(0, 0))
        self._label(card, self._note_ru(pitch_class), 12, TEXT, True,
                    bg="#172d43").pack(fill="x")

    def _update_quiz_ui(self) -> None:
        self._clear(self.quiz_body)
        self._clear(self.action_row)
        if self.phase in ("ready", "study"):
            self.quiz_heading.config(text="Подготовка" if self.phase == "ready" else f"Повторение · {self.study_left} с")
            if self.phase == "ready":
                caption = ("Power chords: корень и квинта; трезвучия: три обращения. Пальцы — подсказка." if self.mode == "forms" else
                           "CAGED: пять семей форм; минорная гамма показывает ♭3, ♭6, ♭7." if self.mode == "caged" else
                           f"{shape_names(self.scale_name)[self.scale_box-1]} · "
                           f"{'3 ноты на каждой струне' if shape_family(self.scale_name) == '3nps' else 'Блюзовая ♭5 — фиолетовая' if shape_family(self.scale_name) == 'blues_box' else '2 ноты на каждой струне'}; корни — янтарные."
                           if self.mode == "scale" and self.scale_view == "box" else
                           "Карта открыта. Изучи ноты перед тестом.")
                self._label(self.quiz_body,caption,10,MUTED,wraplength=320,justify="left").pack(anchor="w")
                button = self._button(self.action_row,"Повторение ▶",self.start_study,primary=True,compact=True)
                button.pack(side="left")
                Tooltip(button,"Начать повторение с таймером; ноты уже видны в подготовке.")
                self._button(self.action_row,"Начать тест →",self.start_quiz,compact=True).pack(side="left",padx=(7,0))
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
            elif self.mode == "find":
                self._render_find_target(target, string)
            elif self.mode == "caged":
                degree = self.caged_steps[self.index][3]
                degree_color = {"1": ACCENT, "3": AMBER, "♭3": AMBER, "5": GREEN}.get(degree, ACCENT)
                box = tk.Frame(self.quiz_body, bg="#19364d", padx=13, pady=9,
                               highlightbackground=degree_color,
                               highlightthickness=2)
                box.pack(fill="x", pady=(3, 4))
                view_title = {"chord":"Аккорд", "major":"Мажорная гамма", "minor":"Минорная гамма"}[self.caged_view]
                self._label(box, f"{NOTE_EN[self.caged_key]} · {view_title} · {self.caged_form}-форма", 11, MUTED, True,
                            bg="#19364d").pack(anchor="w")
                self._label(box, f"{INTERVAL_DESCRIPTIONS.get(degree, 'Ступень '+degree)} · {self._note_name(target)}",
                            22, degree_color, True,
                            bg="#19364d").pack(anchor="w", pady=(4, 1))
                self._label(box, f"Найди на струне {STRINGS[q.row][0]}", 11, TEXT,
                            bg="#19364d").pack(anchor="w")
            elif self.mode == "forms":
                degree = self.forms_steps[self.index][3]
                caption = (f"{self.forms_kind} · {NOTE_EN[self.forms_key]} · "
                           f"{self.forms_voice if self.forms_kind == 'Power chord' else self.forms_quality+' · '+TRIAD_INVERSIONS[self.forms_inversion]}")
                block = tk.Frame(self.quiz_body, bg="#19364d", padx=13, pady=9,
                                 highlightbackground=ACCENT, highlightthickness=2)
                block.pack(fill="x", pady=(3, 4))
                self._label(block, caption, 11, MUTED, True, bg="#19364d").pack(anchor="w")
                self._label(block, f"{self._note_name(target)} · {degree}", 22, ACCENT, True,
                            bg="#19364d").pack(anchor="w", pady=(3, 2))
                self._label(block, f"Найди на струне {STRINGS[q.row][0]}", 11, TEXT,
                            bg="#19364d").pack(anchor="w")
            elif self.mode == "scale":
                degree = self.scale_steps[self.index][3]
                shape_name = (shape_names(self.scale_name)[self.scale_box-1] if self.scale_view == "box" else
                              "Весь гриф" if self.scale_view == "full" else
                              f"Лады {self.scale_position}–{self.scale_position+4}")
                heading = f"{self.scale_name} · {NOTE_EN[self.scale_key]} · {shape_name} · {self.index+1}/{len(self.scale_steps)}"
                self._label(self.quiz_body,heading,11,MUTED,True).pack(anchor="w",pady=(2,7))
                box = tk.Frame(self.quiz_body,bg="#19364d",padx=15,pady=12,highlightbackground=ACCENT,highlightthickness=1)
                box.pack(anchor="w")
                self._label(box,f"{self._note_name(target)}  ·  {degree}",22,ACCENT,True,bg="#19364d").pack(anchor="w")
                left, right = self._scale_area()
                self._label(box,f"Струна {STRINGS[q.row][0]} · лады {left}–{right}",
                            11,TEXT,bg="#19364d").pack(anchor="w",pady=(4,0))
                if self.checked:
                    self._label(box,f"{midi_label(self._pitch(q.row,q.fret))}",12,GREEN,True,bg="#19364d").pack(anchor="w",pady=(5,0))
            else:
                block = tk.Frame(self.quiz_body, bg="#172d43", padx=12, pady=10,
                                 highlightthickness=2, highlightbackground=ACCENT)
                block.pack(fill="x", pady=(3, 5))
                self._label(block, "НА СЛУХ · НАЙДИ ВЫСОТУ НА ГРИФЕ", 10, ACCENT, True,
                            bg="#172d43").pack(anchor="center", pady=(0, 8))
                button = self._button(block,
                    f"♫  Слушать ещё   {max(0, EAR_REPLAYS - self.ear_replays_used)}/{EAR_REPLAYS}",
                    self.replay_ear_note, primary=True)
                button.pack(anchor="center", pady=(1, 7))
                if self.checked or self.ear_replays_used >= EAR_REPLAYS:
                    button.config(state="disabled")
                Tooltip(button, "Начальное звучание автоматическое; ещё 3 повтора на каждый вопрос.")
                if self.checked:
                    self._label(block, f"{self._note_name(target)} · {midi_label(self._pitch(q.row, q.fret))}",
                                14, GREEN if self.feedback_is_correct else AMBER, True,
                                bg="#172d43").pack(anchor="center")
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
