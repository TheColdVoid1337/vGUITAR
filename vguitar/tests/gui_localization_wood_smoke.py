"""Interactive smoke for clickable woods, isolated texture layer, and locale."""
import os
import tempfile
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sys
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vguitar_notes import NoteTrainer
from vguitar_storage import read_preferences


def find_one(parent, kind, caption=None):
    for child in parent.winfo_children():
        if isinstance(child, kind) and (caption is None or child.cget("text") == caption):
            return child
        match = find_one(child, kind, caption)
        if match is not None:
            return match
    return None


with tempfile.TemporaryDirectory() as folder:
    os.environ["VGUITAR_DATA_DIR"] = folder
    root = tk.Tk()
    app = NoteTrainer(root)
    app.audio.play = MagicMock(return_value=True)
    app.audio.preload = MagicMock()
    root.update()
    assert app.language == "ru"
    assert app.history_button.cget("text") == "📖"
    assert app.fretboard_theme == "default"

    app.open_settings()
    window = app._settings_window
    tabs = find_one(window, ttk.Notebook)
    assert tabs is not None and len(tabs.tabs()) == 4
    tabs.select(2)
    root.update()
    assert len(app._wood_previews) == 4

    maple = app._wood_previews["maple"][0]
    maple.event_generate("<Button-1>", x=20, y=20)
    root.update()
    assert app.fretboard_theme == "maple"
    assert app._wood_texture_checkbox.cget("state") == "normal"
    app._wood_texture_checkbox.invoke()
    root.update()
    assert app.fretboard_texture
    assert app.board.find_withtag("wood_texture")
    assert maple.find_withtag("wood_texture")

    original = app._wood_previews["default"][0]
    original.event_generate("<Button-1>", x=20, y=20)
    root.update()
    assert app.fretboard_theme == "default"
    assert not app.fretboard_texture
    assert app._wood_texture_checkbox.cget("state") == "disabled"
    assert not app.board.find_withtag("wood_texture")

    find_one(window, tk.Button, "Отмена").invoke()
    root.update()
    assert app.fretboard_theme == "default"

    app.open_settings()
    window = app._settings_window
    tabs = find_one(window, ttk.Notebook)
    tabs.select(2)
    root.update()
    rosewood = app._wood_previews["rosewood"][0]
    rosewood.event_generate("<Button-1>", x=20, y=20)
    app._wood_texture_checkbox.invoke()
    root.update()
    assert app.fretboard_theme == "rosewood" and app.fretboard_texture

    tabs.select(3)
    root.update()
    english = find_one(window, tk.Radiobutton, "ENGLISH")
    assert english is not None
    english.invoke()
    find_one(window, tk.Button, "Сохранить").invoke()
    root.update()

    assert app.language == "en"
    assert app.mode_combo.get() == "Name"
    assert app.history_button.cget("text") == "📖"
    assert app.fretboard_theme == "rosewood"
    assert app.board.find_withtag("wood_texture")
    prefs = read_preferences()
    assert prefs["language"] == "en"
    assert prefs["fretboard_texture"] is True
    assert prefs["fretboard_theme"] == "rosewood"

    # Existing preferences should initialize the English interface directly.
    app.audio.close()
    root.destroy()
    root = tk.Tk()
    app = NoteTrainer(root)
    app.audio.play = MagicMock(return_value=True)
    root.update()
    assert app.language == "en" and app.mode_combo.get() == "Name"
    assert app.fretboard_theme == "rosewood" and app.fretboard_texture
    app.audio.close()
    root.destroy()
print("PASS: wood previews, separate texture, cancel/save, language switch and restart")
