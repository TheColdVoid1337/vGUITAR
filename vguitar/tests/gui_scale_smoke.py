"""Real Tk exercises: changing keys, scale steps, fret geometry, history."""
import os, tempfile, tkinter as tk
from unittest.mock import MagicMock
# Support standalone GUI smoke checks from the relocated tests directory.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vguitar_notes import (NoteTrainer, NOTE_EN, SCALES, TOP, ROW_H, fret_center,
                           fret_width, board_width, OPEN_WIDTH)
from vguitar_storage import list_runs, read_preferences

with tempfile.TemporaryDirectory() as rootpath:
    os.environ['VGUITAR_DATA_DIR']=rootpath
    root=tk.Tk(); app=NoteTrainer(root); app.audio.play=MagicMock(return_value=True)
    root.geometry('1024x768');root.update()
    app.change_mode('scale');root.update()
    app.scale_view_choice.set('Участок ладов');app._scale_option_changed();root.update()
    assert app.mode=='scale'
    assert app.scale_position_mode=='auto'
    assert app.scale_position_choice.get()=='Авто'
    # Note labels are present in ready mode, before the study timer.
    assert app.phase=='ready'
    assert len(app.board.find_withtag('note_disc'))>0
    assert app._active(0) and app._active(5)
    assert app.scale_options.winfo_manager()=='pack'
    assert not app._counter_boxes['strings'].winfo_manager()
    assert len(app.mode_buttons)==6
    app.scale_choice.set('Натуральный минор')
    app.scale_key_choice.set('E')
    app.scale_position_choice.set('0')
    app._scale_option_changed();root.update()
    app.start_study();root.update()
    assert app.phase=='study'
    app.start_quiz();root.update()
    assert app.phase=='quiz' and len(app.questions)>8
    expected_count=len(app.scale_steps)
    assert app.scale_steps[0][3]=='1'
    assert app.quiz_body.winfo_children()
    # Wrong click on an adjacent semitone on first step (E2 vs F2): recorded.
    q=app._current(); r=5;f=1
    canvas_x=fret_center(f,app.cell_width)-app.board.canvasx(0)
    app._click_board(type('Event',(),{'x':canvas_x,'y':TOP+r*ROW_H+ROW_H/2})())
    assert app.checked and not app.feedback_is_correct
    assert app.responses[0]['degree']=='1'
    assert app.responses[0]['answer_fret']==1
    assert app.responses[0]['answer_midi']==41
    app._space_key(type('Event',(),{'widget':app.board})());root.update()
    assert app.index==1 and not app.checked
    # Complete each remaining step with the canonical position.
    while app.phase=='quiz':
        q=app._current()
        xpos=fret_center(q.fret,app.cell_width)-app.board.canvasx(0)
        app._click_board(type('Event',(),{'x':xpos,'y':TOP+q.row*ROW_H+ROW_H/2})())
        assert app.checked and app.feedback_is_correct, (app.index, q, xpos)
        app.next_question();root.update()
    assert app.phase=='result' and len(app.responses)==expected_count
    assert app.correct==expected_count-1
    runs,_=list_runs();assert len(runs)==1
    assert runs[0]['configuration']['scale']=='Натуральный минор'
    assert runs[0]['configuration']['key']=='E'
    assert runs[0]['configuration']['scale_shape_notes']==expected_count
    assert runs[0]['configuration']['position_mode']=='manual'
    assert len({(e['string_number'],e['fret']) for e in runs[0]['questions']}) == expected_count
    app.export_current();assert 'scale_step' in root.clipboard_get()
    app.show_map();app.change_mode('name');root.update()
    assert app._counter_boxes['strings'].winfo_manager()=='pack'
    assert not app.scale_options.winfo_manager()
    prefs=read_preferences()['lesson']
    assert prefs['scale_name']=='Натуральный минор'
    root.destroy()
print('GUI scales PASS')
