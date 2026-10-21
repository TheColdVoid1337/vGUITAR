"""Optional interactive widget smoke-check; requires a graphical display (or xvfb)."""
import os
import tempfile
import tkinter as tk
from tkinter import ttk
from unittest.mock import MagicMock

from vguitar_notes import NoteTrainer, TUNINGS, CELL_W, ROW_H, TOP

with tempfile.TemporaryDirectory() as config:
    os.environ['HOME'] = config
    root = tk.Tk()
    app = NoteTrainer(root)
    app.audio.play = MagicMock(return_value=True)
    root.update()
    assert app.phase == 'study'
    assert app._pitch(5, 0) == 40
    # Study mode click: open low E string, preview sound.
    app._click_board(type('E', (), {'x': CELL_W//2, 'y': TOP + 5*ROW_H + 20})())
    assert app.audio.play.call_args.args[0] == 40
    # Correct and incorrect note naming.
    app.start_quiz()
    q = app._current()
    app.answer_name((app._pitch_class(q.row, q.fret)+1) % 12)
    assert app.checked and app.correct == 0 and len(app.mistakes) == 1
    assert app.audio.play.call_args.kwargs.get('buzzing') is True
    app.next_question()
    q = app._current()
    app.answer_name(app._pitch_class(q.row, q.fret))
    assert app.checked and app.correct == 1
    assert app.audio.play.call_args.kwargs.get('buzzing') is None
    app.show_map()
    app.change_mode('find')
    app.start_quiz()
    q = app._current()
    app._click_board(type('E', (), {'x': q.fret*CELL_W+20, 'y': TOP + q.row*ROW_H + 20})())
    assert app.checked and app.feedback_is_correct
    app.show_map()

    app.open_settings()
    root.update()
    window = app._settings_window
    assert window.winfo_exists()
    combos = []
    def descend(widget):
        for child in widget.winfo_children():
            if isinstance(child, ttk.Combobox):
                combos.append(child)
            descend(child)
    descend(window)
    assert len(combos) == 7
    presets = combos[0]
    presets.set('Drop D (D A D G B E)')
    presets.event_generate('<<ComboboxSelected>>')
    root.update()
    assert 'D2' in combos[-1].get()
    # Drive the Save button, inspect resulting tuning/map.
    buttons = []
    def collect(widget):
        for child in widget.winfo_children():
            if isinstance(child, tk.Button):
                buttons.append(child)
            collect(child)
    collect(window)
    next(b for b in buttons if b.cget('text') == 'Сохранить').invoke()
    root.update()
    assert app.preset_name.startswith('Drop D')
    assert app.tuning == TUNINGS[app.preset_name]
    assert app._pitch(5, 0) == 38
    assert app.phase == 'study'
    root.destroy()
print('GUI smoke PASSED (study, sounds triggered, both quiz modes, preset dialog, saved tuning)')
