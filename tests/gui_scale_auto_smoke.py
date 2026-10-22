"""Real-Tk smoke: auto positions, full shape and the untimed study map."""
import os
import tempfile
import tkinter as tk
from unittest.mock import MagicMock
from vguitar_notes import NoteTrainer, fret_center, TOP, ROW_H, scale_positions
from vguitar_storage import read_preferences

with tempfile.TemporaryDirectory() as tmp:
    os.environ['VGUITAR_DATA_DIR'] = tmp
    root = tk.Tk()
    app = NoteTrainer(root)
    app.audio.play = MagicMock(return_value=True)
    root.geometry('1024x768'); root.update()
    app.change_mode('scale'); root.update()
    assert app.scale_position_mode == 'auto'
    assert app.scale_position_choice.get() == 'Авто'
    assert app.phase == 'ready'
    assert len(app.board.find_withtag('note_disc')) > 0, 'Labels must be visible before test'
    auto_fret = app.scale_position
    expected = scale_positions(app.tuning, app.scale_name, app.scale_key, auto_fret)
    app.start_quiz(); root.update()
    assert app.phase == 'quiz'
    assert len(app.scale_steps) == len(expected) and len(expected) > 8
    assert app.scale_position == auto_fret
    assert 'Струна' in ''.join(str(w.cget('text')) for w in app.quiz_body.winfo_children()
                                    if hasattr(w,'cget') and 'text' in w.keys()) or app.quiz_body.winfo_children()
    # Questions MUST be tied to a particular string. Don't accept a different
    # string/fret even if it produces the same absolute MIDI pitch.
    for k, q in enumerate(app.questions):
        duplicate = next(((r,f) for r,f,m,_ in expected
                          if m == app._pitch(q.row,q.fret) and (r,f)!=(q.row,q.fret)),None)
        if duplicate:
            r,f = duplicate
            x=fret_center(f,app.cell_width)-app.board.canvasx(0)
            app._click_board(type('E',(),{'x':x,'y':TOP+r*ROW_H+ROW_H/2})())
            assert app.checked and not app.feedback_is_correct
            app.next_question()
            break
        # Move to the next question to look for a duplicate without invalidating run.
        x=fret_center(q.fret,app.cell_width)-app.board.canvasx(0)
        app._click_board(type('E',(),{'x':x,'y':TOP+q.row*ROW_H+ROW_H/2})())
        assert app.checked and app.feedback_is_correct
        app.next_question()
    while app.phase=='quiz':
        q=app._current()
        x=fret_center(q.fret,app.cell_width)-app.board.canvasx(0)
        app._click_board(type('E',(),{'x':x,'y':TOP+q.row*ROW_H+ROW_H/2})())
        assert app.checked
        app.next_question()
    assert app.phase=='result' and len(app.responses)==len(expected)
    assert app.current_run['configuration']['position_mode']=='auto'
    assert app.current_run['configuration']['position_start_fret']==auto_fret
    assert app.current_run['configuration']['scale_shape_notes']==len(expected)
    app.show_map(); root.update()
    assert app.phase == 'ready'
    assert app.scale_position != auto_fret, 'New auto run picks another position'
    assert len(app.board.find_withtag('note_disc')) > 0
    assert read_preferences()['lesson']['scale_position_mode']=='auto'
    root.destroy()
print('GUI auto-scale / full fretboard / ready preview PASS')
