"""Run with xvfb-run -a python tests/gui_caged_smoke.py; no audio hardware needed."""
import os
import tempfile
import tkinter as tk
from unittest.mock import MagicMock, patch
from vguitar_notes import NoteTrainer, STANDARD_MIDI, fret_center, TOP, ROW_H
from vguitar_caged import caged_positions
from vguitar_storage import list_runs, export_runs_for_llm

with tempfile.TemporaryDirectory() as folder:
    os.environ["VGUITAR_DATA_DIR"] = folder
    root = tk.Tk()
    app = NoteTrainer(root)
    app.audio.preload = MagicMock()
    app.audio.play = MagicMock(return_value=True)
    for size in ("680x575", "780x650", "1024x768", "1366x768"):
        root.geometry(size)
        root.update()
        app.change_mode("caged")
        root.update()
        assert app.caged_options.winfo_manager() == "pack"
        assert len(app._caged_shape()) >= 4
        assert app.board.find_withtag("note_disc")
        assert (app.mode_buttons["caged"].winfo_rootx() + app.mode_buttons["caged"].winfo_width()
                <= root.winfo_rootx() + root.winfo_width()), size
    app.caged_form = "E"
    app.caged_key = 7
    app.start_study()
    root.update()
    assert app.phase == "study"
    app.start_quiz()
    root.update()
    assert app.phase == "quiz"
    assert len(app.questions) == len(caged_positions(STANDARD_MIDI, 7, "E"))
    for i, question in enumerate(app.questions):
        x = fret_center(question.fret, app.cell_width) - app.board.canvasx(0)
        y = TOP + question.row * ROW_H + ROW_H / 2
        app._click_board(type("Click", (), {"x": x, "y": y})())
        assert app.checked and app.feedback_is_correct
        assert app.responses[-1]["degree"] == app.caged_steps[i][3]
        app.next_question()
    assert app.phase == "result"
    assert app.current_run["configuration"]["caged_form"] == "E"
    assert app.current_run["configuration"]["caged_key"] == "G"
    assert len(list_runs()[0]) == 1
    assert "caged_shape_notes" in export_runs_for_llm([app.current_run])
    app.show_map()
    root.update()
    assert app.caged_form == "D"
    app.caged_form_choice.set("C")
    app._caged_option_changed()
    assert app.caged_form_mode == "manual" and app.caged_form == "C"
    app.tuning = (64, 59, 55, 50, 45, 38)
    with patch("vguitar_notes.messagebox.showwarning") as warning:
        app.start_quiz()
        warning.assert_called_once()
    root.destroy()
print("CAGED GUI smoke PASS")
