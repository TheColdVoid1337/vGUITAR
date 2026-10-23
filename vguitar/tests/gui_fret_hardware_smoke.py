"""Interactive visual-hardware regression on Windows or xvfb-run.

No real audio output; settings and history are written to a temp directory.
"""
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vguitar_notes import NoteTrainer
from vguitar_storage import read_preferences
from vguitar_visual import FRET_CROWNS_MM, fret_width_px, nut_width_px, string_widths


def first(parent, kind, caption=None):
    for widget in parent.winfo_children():
        if isinstance(widget, kind) and (caption is None or widget.cget("text") == caption):
            return widget
        found = first(widget, kind, caption)
        if found is not None:
            return found
    return None


def choose(app, root, key, label):
    widget = app._fret_visual_controls[key]
    assert widget.instate(("readonly",)), f"{key}: {widget.state()}"
    widget.set(label)
    widget.event_generate("<<ComboboxSelected>>")
    root.update()


with tempfile.TemporaryDirectory() as folder:
    os.environ["VGUITAR_DATA_DIR"] = folder
    root = tk.Tk()
    app = NoteTrainer(root)
    app.audio.play = MagicMock(return_value=True)
    app.audio.preload = MagicMock()
    root.update()
    originals = dict(app.fretboard_visual)
    original_seed = app.fretboard_grain_seed

    app.open_settings()
    dialog = app._settings_window
    tabs = first(dialog, ttk.Notebook)
    assert tabs is not None
    tabs.select(2)
    root.update()

    assert len(app._wood_previews) == 4
    assert set(app._fret_visual_controls) == {
        "string_set", "string_material", "nut_mm", "nut_material",
        "fret_mm", "fret_material", "inlay_radius",
    }
    assert app._wood_grain_shuffle_button.cget("state") == "disabled"

    ebony = app._wood_previews["ebony"][0]
    ebony.event_generate("<Button-1>", x=15, y=15)
    root.update()
    app._wood_texture_checkbox.invoke()
    root.update()
    assert app.fretboard_texture
    assert app._wood_grain_shuffle_button.cget("state") == "normal"
    assert app.board.find_withtag("wood_texture")
    previous_lines = [app.board.coords(i) for i in app.board.find_withtag("wood_texture")]
    app._wood_grain_shuffle_button.invoke()
    root.update()
    assert app.fretboard_grain_seed != original_seed
    assert previous_lines != [app.board.coords(i) for i in app.board.find_withtag("wood_texture")]
    assert ebony.find_withtag("wood_texture")

    choose(app, root, "string_set", "12–56")
    choose(app, root, "string_material", "Чистый никель")
    choose(app, root, "nut_mm", "8 mm")
    choose(app, root, "nut_material", "Медь")
    choose(app, root, "fret_mm", "SINTOMS 4.3mm")
    choose(app, root, "fret_material", "EVO Gold")
    app._fret_visual_controls["inlay_radius"].set(7)
    root.update()
    assert app.fretboard_visual == {
        "string_set": "12–56", "string_material": "pure_nickel",
        "nut_mm": 8.0, "nut_material": "copper",
        "fret_mm": 4.3, "fret_material": "evo_gold", "inlay_radius": 7.0,
    }
    nut = app.board.find_withtag("nut")[0]
    x0, _, x1, _ = app.board.coords(nut)
    assert abs(x1 - x0 - nut_width_px(8.0)) < .01
    wire = app.board.find_withtag("fret_wire")[0]
    assert app.board.itemcget(wire, "fill") == "#d2ad61"
    assert abs(float(app.board.itemcget(wire, "width")) - fret_width_px(4.3)) < .01
    high_e = app.board.find_withtag("guitar_string_1")[0]
    assert abs(float(app.board.itemcget(high_e, "width")) - string_widths("12–56")[0]) < .01

    # Cancellation rolls back all live changes, including randomly chosen grain.
    cancel = first(dialog, tk.Button, "Отмена")
    assert cancel is not None
    cancel.invoke()
    root.update()
    assert app.fretboard_theme == "default"
    assert app.fretboard_visual == originals
    assert app.fretboard_grain_seed == original_seed

    app.open_settings()
    dialog = app._settings_window
    tabs = first(dialog, ttk.Notebook)
    tabs.select(2)
    root.update()
    maple = app._wood_previews["maple"][0]
    maple.event_generate("<Button-1>", x=16, y=15)
    app._wood_texture_checkbox.invoke()
    app._wood_grain_shuffle_button.invoke()
    choose(app, root, "string_set", "9–42")
    choose(app, root, "nut_mm", "8 mm")
    choose(app, root, "fret_mm", "SINTOMS 4.3mm")
    choose(app, root, "nut_material", "Кость")
    choose(app, root, "fret_material", "Нержавеющая сталь")
    root.update()
    new_seed = app.fretboard_grain_seed
    save = first(dialog, tk.Button, "Сохранить")
    assert save is not None
    save.invoke()
    root.update()
    prefs = read_preferences()
    assert prefs["fretboard_theme"] == "maple"
    assert prefs["fretboard_texture"]
    assert prefs["fretboard_grain_seed"] == new_seed
    assert prefs["fretboard_visual"]["string_set"] == "9–42"
    assert prefs["fretboard_visual"]["nut_mm"] == 8.0
    assert prefs["fretboard_visual"]["fret_mm"] == 4.3
    assert prefs["fretboard_visual"]["nut_material"] == "bone"
    assert prefs["fretboard_visual"]["fret_material"] == "stainless"

    app.audio.close()
    root.destroy()
    root = tk.Tk()
    app = NoteTrainer(root)
    app.audio.play = MagicMock(return_value=True)
    root.update()
    assert app.fretboard_theme == "maple"
    assert app.fretboard_texture
    assert app.fretboard_grain_seed == new_seed
    assert app.fretboard_visual["string_set"] == "9–42"
    assert app.fretboard_visual["nut_mm"] == 8.0
    assert app.fretboard_visual["fret_mm"] == 4.3
    assert app.board.find_withtag("wood_texture")
    app.audio.close()
    root.destroy()

print("PASS: nut/fret/string hardware, reroll, preview, cancel and persisted settings")
