"""Interactive Tk widget smoke-check. Run: xvfb-run -a python tests/gui_smoke.py"""
import os
import tempfile
import tkinter as tk
from tkinter import ttk
from unittest.mock import MagicMock
from time import monotonic

from vguitar_notes import NoteTrainer, TUNINGS, CELL_W, ROW_H, TOP, fret_center
from vguitar_storage import list_runs

with tempfile.TemporaryDirectory() as config:
    os.environ['VGUITAR_DATA_DIR'] = config
    root = tk.Tk()
    app = NoteTrainer(root)
    app.audio.play = MagicMock(return_value=True)
    root.update()
    assert app.phase == 'ready'
    assert app._pitch(5, 0) == 40
    assert app.study_value.cget('text') == '60'
    app.change_answer_layout('circle')
    root.update()
    assert app.answer_layout == 'circle'
    assert app._responsive_orientation in ('side','stack')
    app.start_study()
    root.update()
    assert app.phase == 'study' and app.study_deadline is not None
    app._click_board(type('E', (), {'x': fret_center(0, app.cell_width)-app.board.canvasx(0), 'y': TOP + 5*ROW_H + 20})())
    assert app.audio.play.call_args.args[0] == 40
    # Simulate expiry without sleeping.
    app.study_deadline = monotonic() - 0.1
    app._study_tick()
    assert app.phase == 'quiz'
    q = app._current()
    app.answer_name((app._pitch_class(q.row,q.fret)+1)%12)
    assert app.responses[0]['response_seconds'] >= 0
    assert not app.responses[0]['correct']
    assert app.audio.play.call_args.kwargs.get('buzzing') is True
    app.next_question()
    q = app._current()
    app.answer_name(app._pitch_class(q.row,q.fret))
    assert app.responses[1]['correct']
    assert app.audio.play.call_args.kwargs.get('buzzing') is None
    # Complete all remaining questions and store exactly one file.
    while app.phase == 'quiz':
        if not app.checked:
            q = app._current()
            app.answer_name(app._pitch_class(q.row,q.fret))
        app.next_question()
    assert app.phase == 'result'
    assert app.current_run is not None
    assert len(app.current_run['questions']) == app.question_count
    assert len(list_runs()[0]) == 1
    app.export_current()
    assert 'vGUITAR_NOTE_TRAINER_REPORT' in root.clipboard_get()
    app.open_history()
    root.update()
    assert app._history_window.winfo_exists()
    app._history_window.destroy()
    # Find a note in custom tuning and verify recorded answer position.
    app.show_map()
    app.change_mode('find')
    app.start_quiz()
    q = app._current()
    app._click_board(type('E', (), {'x':fret_center(q.fret,app.cell_width)-app.board.canvasx(0),'y':TOP+q.row*ROW_H+20})())
    assert app.responses[0]['answer_fret']==q.fret
    assert app.checked and app.feedback_is_correct
    app.show_map()
    app.open_settings()
    root.update()
    window = app._settings_window
    assert window.winfo_exists()
    combos=[]
    def descend(w):
        for child in w.winfo_children():
            if isinstance(child,ttk.Combobox): combos.append(child)
            descend(child)
    descend(window)
    assert len(combos)>=10  # 7 tuning comboboxes + output/latency/buffer
    combos[0].set('Drop D (D A D G B E)')
    combos[0].event_generate('<<ComboboxSelected>>')
    root.update()
    assert 'D2' in combos[6].get()
    buttons=[]
    def collect(w):
        for child in w.winfo_children():
            if isinstance(child,tk.Button): buttons.append(child)
            collect(child)
    collect(window)
    next(b for b in buttons if b.cget('text')=='Сохранить').invoke()
    root.update()
    assert app.tuning==TUNINGS['Drop D (D A D G B E)']
    assert app._pitch(5,0)==38
    assert app.phase=='ready'
    assert os.path.isdir(os.path.join(config,'settings'))
    assert os.path.isdir(os.path.join(config,'results'))
    from vguitar_storage import read_preferences
    assert read_preferences()['lesson']['answer_layout'] == 'circle'
    root.destroy()
print('GUI smoke PASS (timed study, response clock, history, clipboard, settings, audio triggers)')
