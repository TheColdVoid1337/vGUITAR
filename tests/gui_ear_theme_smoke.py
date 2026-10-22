"""Run with xvfb: PYTHONPATH=. xvfb-run -a python tests/gui_ear_theme_smoke.py"""
import tempfile,os,tkinter as tk
from unittest.mock import MagicMock
from vguitar_notes import (NoteTrainer, TOP, ROW_H, OPEN_WIDTH, fret_center,
                           FRETBOARD_THEMES, EAR_REPLAYS)
from vguitar_storage import read_preferences,list_runs

with tempfile.TemporaryDirectory() as folder:
    os.environ['VGUITAR_DATA_DIR']=folder
    root=tk.Tk();root.geometry('1024x768')
    app=NoteTrainer(root);app.audio.play=MagicMock(return_value=True)
    root.update()
    # Can audition before choosing timed study.
    app._click_board(type('E', (), {'x':OPEN_WIDTH//2,'y':TOP+5*ROW_H+ROW_H//2})())
    assert app.audio.play.call_args.args[0]==40
    for name in FRETBOARD_THEMES:
        app.fretboard_theme=name;app._save_preferences();app._draw_board();root.update()
        assert app.board.itemcget(app.board.find_withtag('fretboard')[0],'fill')==FRETBOARD_THEMES[name]['neck']
        assert read_preferences()['fretboard_theme']==name
    app.fretboard_theme='default'
    app.active_strings=2;app.active_frets=12
    app.change_mode('ear');root.update()
    assert app.mode=='ear'
    assert len(app.mode_buttons)==5
    app.start_quiz();root.update()
    assert app.phase=='quiz'
    q=app._current()
    # First sound fires automatically via scheduled callback.
    app._play_ear_question()
    assert app.audio.play.call_args.args[0]==app._pitch(q.row,q.fret)
    assert app.ear_replays_used==0
    for n in range(EAR_REPLAYS):
        assert app.replay_ear_note() is True
        assert app.ear_replays_used==n+1
    assert app.replay_ear_note() is False
    # A name-match in another octave is wrong.
    q=app._current()
    other=next(((row,f) for row in (4,5) for f in range(13)
                 if app._pitch_class(row,f)==app._pitch_class(q.row,q.fret)
                 and app._pitch(row,f)!=app._pitch(q.row,q.fret)),None)
    if other:
        row,fret=other
        app._click_board(type('E',(),{'x':fret_center(fret,app.cell_width)-app.board.canvasx(0),
                                      'y':TOP+row*ROW_H+ROW_H//2})())
        assert app.checked and not app.feedback_is_correct
        assert app.responses[0]['answer_midi']==app._pitch(row,fret)
    else:
        app._click_board(type('E',(),{'x':fret_center(q.fret,app.cell_width)-app.board.canvasx(0),
                                      'y':TOP+q.row*ROW_H+ROW_H//2})())
    assert app.responses[0]['replays_used']==EAR_REPLAYS
    app.next_question();root.update()
    q=app._current()
    # Correct exact pitch on any active string including a different one.
    matches=[(row,f) for row in (4,5) for f in range(13)
             if app._pitch(row,f)==app._pitch(q.row,q.fret)]
    row,fret=matches[-1]
    app._click_board(type('E',(),{'x':fret_center(fret,app.cell_width)-app.board.canvasx(0),
                                  'y':TOP+row*ROW_H+ROW_H//2})())
    assert app.checked and app.feedback_is_correct
    assert app.responses[1]['answer_string_number']==int(row+1)
    assert app.responses[1]['replays_used']==0
    assert app.responses[1]['expected_midi']==app.responses[1]['answer_midi']
    # Browse to results, ensure all ear response data persists.
    while app.phase=='quiz':
        if not app.checked:
            q=app._current()
            app._click_board(type('E',(),{'x':fret_center(q.fret,app.cell_width)-app.board.canvasx(0),
                                          'y':TOP+q.row*ROW_H+ROW_H//2})())
        app.next_question()
    assert len(list_runs()[0])==1
    app.export_current()
    assert '"mode": "ear"' in root.clipboard_get()
    root.destroy()
print('GUI ear mode / wood settings / pretest sound PASS')
