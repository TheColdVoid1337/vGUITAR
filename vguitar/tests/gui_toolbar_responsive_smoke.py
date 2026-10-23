"""Manual responsive-toolbar regression check (Windows or xvfb-run).

Run from the repository root:
    python vguitar/tests/gui_toolbar_responsive_smoke.py
or, on Linux:
    xvfb-run -a python vguitar/tests/gui_toolbar_responsive_smoke.py

Uses Tk's real requested widths so font sizes and Windows DPI are covered.
"""
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vguitar_notes import NoteTrainer


def bounds(widget):
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    return x, y, x + widget.winfo_width(), y + widget.winfo_height()


def overlaps(a, b):
    ax1, ay1, ax2, ay2 = bounds(a)
    bx1, by1, bx2, by2 = bounds(b)
    return min(ax2, bx2) > max(ax1, bx1) and min(ay2, by2) > max(ay1, by1)


with tempfile.TemporaryDirectory() as data_dir:
    os.environ["VGUITAR_DATA_DIR"] = data_dir
    root = tk.Tk()
    app = NoteTrainer(root)
    app.audio.play = MagicMock(return_value=True)
    # Tkinter prints callback exceptions instead of propagating them from
    # button.invoke(). Collect them so the smoke check fails reliably.
    callback_errors = []
    root.report_callback_exception = (
        lambda kind, exc, trace: callback_errors.append(f"{kind.__name__}: {exc}")
    )
    try:
        sizes = (
            (1583, 842), (1366, 768), (1280, 720), (1227, 840),
            (1024, 768), (780, 650), (680, 575), (1227, 840),
        )
        for width, height in sizes:
            root.geometry(f"{width}x{height}+0+0")
            root.update()
            # Clicking each mode must not attempt to pack a widget before a
            # sibling that lives in a different Tk parent frame.
            # Real dropdown selections must not change toolbar group positions.
            initial_grid = {
                "brand": app.brand.grid_info(),
                "mode": app.mode_strip.grid_info(),
                "controls": app.counter_strip.grid_info(),
                "utilities": app.utility_strip.grid_info(),
            }
            for selected_mode, label in (
                ("scale", "Гаммы"), ("name", "Назвать"),
                ("find", "Найти"), ("ear", "На слух"),
                ("caged", "CAGED"), ("forms", "Формы"),
                ("name", "Назвать"),
            ):
                app.mode_combo.set(label)
                app.mode_combo.event_generate("<<ComboboxSelected>>")
                root.update()
                if callback_errors:
                    raise AssertionError(
                        f"mode {selected_mode}, {width}x{height}: {callback_errors}"
                    )
                if app.mode != selected_mode:
                    raise AssertionError(f"mode dropdown did not select {selected_mode}")
                is_quiz = selected_mode in ("name", "find", "ear")
                expected = "normal" if is_quiz else "disabled"
                if app.string_picker_button.cget("state") != expected:
                    raise AssertionError("incorrect string selector state")
                if any(button.cget("state") != expected
                       for kind in ("strings", "frets", "questions")
                       for button in app._counter_buttons[kind]):
                    raise AssertionError("incorrect counter state")
                positions = {
                    "brand": app.brand.grid_info(),
                    "mode": app.mode_strip.grid_info(),
                    "controls": app.counter_strip.grid_info(),
                    "utilities": app.utility_strip.grid_info(),
                }
                if any(positions[k] != initial_grid[k] for k in positions):
                    raise AssertionError(f"toolbar moved after selecting {selected_mode}")
            toolbar = app.toolbar
            groups = (app.brand, app.counter_strip, app.mode_strip, app.utility_strip)
            left, top, right, bottom = bounds(toolbar)
            errors = []
            for group in groups:
                if not group.winfo_ismapped():
                    errors.append(f"hidden: {group}")
                x1, y1, x2, y2 = bounds(group)
                if x1 < left or x2 > right or y1 < top or y2 > bottom:
                    errors.append(f"outside toolbar: {group}, {x1,y1,x2,y2}")
            for i, group in enumerate(groups):
                for other in groups[i+1:]:
                    if overlaps(group, other):
                        errors.append(f"overlap: {group} / {other}")
            for button in (app.settings_button, app.history_button,
                           app.about_button, app.string_picker_button):
                x1, y1, x2, y2 = bounds(button)
                if not (left <= x1 < x2 <= right and top <= y1 < y2 <= bottom):
                    errors.append(f"button clipped: {button.cget('text')}")
            mode = app._toolbar_layout
            full_requested = (
                app.brand.winfo_reqwidth() +
                app.counter_strip.winfo_reqwidth() +
                app.mode_strip.winfo_reqwidth() +
                app.utility_strip.winfo_reqwidth() + 24
            )
            available = width - 46
            if full_requested <= available and mode != "single":
                errors.append(f"missed single-row fit: {full_requested} <= {available}")
            if width >= 1227 and not errors:
                print(f"DESKTOP {width}: {mode} (required={full_requested}, available={available})")
            else:
                print(f"RESIZE {width}: {mode} (required={full_requested}, available={available})")
            if errors:
                raise AssertionError(f"{width}x{height}: {'; '.join(errors)}")
        print("PASS: toolbar groups are visible, non-overlapping and within bounds.")
    finally:
        app.audio.close()
        root.destroy()
