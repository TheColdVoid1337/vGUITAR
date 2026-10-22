"""Check preview, quiz, strict box geometry, legacy range and complete fretboard."""
import os
import tempfile
import tkinter as tk
from unittest.mock import MagicMock
from vguitar_notes import NoteTrainer, fret_center, TOP, ROW_H
from vguitar_storage import read_preferences

with tempfile.TemporaryDirectory() as home:
    os.environ['VGUITAR_DATA_DIR']=home
    root=tk.Tk()
    app=NoteTrainer(root)
    app.audio.play=MagicMock(return_value=True)
    app.audio.preload=MagicMock()
    root.geometry('1024x768'); root.update()
    app.change_mode('scale')
    app.scale_choice.set('Минорная пентатоника')
    app.scale_key_choice.set('A')
    app._scale_option_changed();root.update()
    assert app.scale_view=='box'
    assert app.scale_view_choice.get()=='Аппликатуры'
    assert app.scale_position_choice.get()=='Авто'
    app.scale_position_choice.set('Box 1')
    app._scale_option_changed();root.update()
    assert app.scale_box==1 and app.scale_box_mode=='manual'
    coords={(r,f) for r,f,_m,_d in app._scale_items()}
    assert len(coords)==12
    assert (2,9) not in coords
    assert app._scale_area()==(5,8)
    assert len(app.board.find_withtag('scale_note'))==12
    assert len(app.board.find_withtag('scale_outside')) > 0
    assert app.phase=='ready'
    app.start_quiz();root.update()
    assert len(app.questions)==12
    assert {(q.row,q.fret) for q in app.questions}==coords
    for q in app.questions:
        x=fret_center(q.fret,app.cell_width)-app.board.canvasx(0)
        y=TOP+q.row*ROW_H+ROW_H/2
        app._click_board(type('Click',(),{'x':x,'y':y})())
        assert app.checked and app.feedback_is_correct
        app.next_question();root.update()
    assert app.phase=='result'
    cfg=app.current_run['configuration']
    assert cfg['scale_view']=='box' and cfg['scale_box']==1 and cfg['scale_box_mode']=='manual'
    assert cfg['scale_shape_notes']==12
    app.show_map();root.update()
    app.scale_position_choice.set('Авто');app._scale_option_changed();root.update()
    assert app.scale_box_mode=='auto'
    app.start_quiz();root.update()
    before=app.scale_box
    for q in app.questions:
        x=fret_center(q.fret,app.cell_width)-app.board.canvasx(0)
        y=TOP+q.row*ROW_H+ROW_H/2
        app._click_board(type('Click',(),{'x':x,'y':y})())
        app.next_question()
    app.show_map();root.update()
    assert app.scale_box == before % 5 + 1
    # Full scale map is separate from individual 12-dot boxes.
    app.scale_view_choice.set('Весь звукоряд'); app._scale_option_changed();root.update()
    assert app.scale_view=='full' and app._scale_area()==(0,24)
    assert len(app._scale_items())>45
    assert len(app.board.find_withtag('scale_note'))==len(app._scale_items())
    app.scale_view_choice.set('Участок ладов');app._scale_option_changed();root.update()
    app.scale_position_choice.set('5');app._scale_option_changed();root.update()
    assert app.scale_view=='range' and app._scale_area()==(5,9)
    assert (2,9) in {(r,f) for r,f,_m,_d in app._scale_items()}
    # The former behavior is retained but explicitly called an arbitrary range.
    assert len(app.board.find_withtag('scale_note'))==len(app._scale_items())
    assert read_preferences()['lesson']['scale_view']=='range'
    # Unsupported classic box shapes never silently turn into incorrect Drop-D geometry.
    app.scale_view_choice.set('Аппликатуры');app._scale_option_changed();root.update()
    app.tuning=(64,59,55,50,45,38);app._update_all();root.update()
    assert len(app.board.find_withtag('scale_note'))==0
    for size in ('680x575','780x650','1024x768','1366x768'):
        root.geometry(size);root.update()
        scale_right=max(x.winfo_rootx()+x.winfo_width() for x in app._scale_comboboxes)
        assert scale_right <= root.winfo_rootx()+root.winfo_width(), (size,scale_right)
        assert app.action_row.winfo_rooty()+app.action_row.winfo_height() <= root.winfo_rooty()+root.winfo_height(),size
    root.destroy()
print('GUI pentatonic boxes, A minor box 1, full scale, range and responsive layout PASS')
