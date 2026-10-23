"""Manual Tk string-selection integration smoke.

Run with: xvfb-run -a python tests/gui_string_picker_smoke.py
"""
import os
import tempfile
import tkinter as tk
from unittest.mock import MagicMock
# Support standalone GUI smoke checks from the relocated tests directory.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vguitar_notes import NoteTrainer
from vguitar_storage import read_preferences

with tempfile.TemporaryDirectory() as temp:
    os.environ["VGUITAR_DATA_DIR"] = temp
    root = tk.Tk()
    app = NoteTrainer(root)
    app.audio.play = MagicMock(return_value=True)
    app.audio.preload = MagicMock()
    root.update()
    assert app.selected_strings == (6, 5)
    app.open_string_picker()
    root.update()
    app._string_picker_vars[6].set(False)
    def press_apply(widget):
        for child in widget.winfo_children():
            if isinstance(child, tk.Button) and child.cget("text") == "Применить":
                child.invoke()
                return True
            if press_apply(child):
                return True
        return False
    assert press_apply(app._string_picker_window)
    root.update()
    assert app.selected_strings == (5,)
    assert app.active_strings == 1
    assert app._active(4) and not app._active(5)
    assert "Струны 5" in app.board_hint.cget("text")
    assert read_preferences()["lesson"]["selected_strings"] == [5]
    for mode in ("name", "find", "ear"):
        app.change_mode(mode)
        assert all(q.row == 4 for q in app._make_questions())
    app.change_setting("strings", 1)
    assert app.selected_strings == (6, 5)
    app.open_string_picker()
    root.update()
    for number, var in app._string_picker_vars.items():
        var.set(number in (2, 5))
    assert press_apply(app._string_picker_window)
    root.update()
    assert app.selected_strings == (5, 2)
    assert set(q.row for q in app._make_questions()).issubset({4, 1})
    root.destroy()
print("GUI string-picker smoke PASS")
