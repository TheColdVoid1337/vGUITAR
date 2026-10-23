"""Tkinter smoke: all seven scale families, shape switching and quiz positions."""
import os
import tempfile
import tkinter as tk
from unittest.mock import MagicMock
# Support standalone GUI smoke checks from the relocated tests directory.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vguitar_notes import NoteTrainer, SCALES, NOTE_EN, TOP, ROW_H, fret_center
from vguitar_scale_patterns import DIATONIC_OFFSETS, shape_names, shape_family, scale_fingering

with tempfile.TemporaryDirectory() as tmp:
    os.environ['VGUITAR_DATA_DIR'] = tmp
    root = tk.Tk()
    app = NoteTrainer(root)
    app.audio.play = MagicMock(return_value=True)
    app.audio.preload = MagicMock()
    app.change_mode('scale')
    for width,height in ((680,575),(780,650),(1024,768),(1366,768)):
        root.geometry(f'{width}x{height}');root.update()
        for name in SCALES:
            app.scale_choice.set(name)
            app.scale_key_choice.set('D')
            app._scale_option_changed();root.update()
            assert app.scale_view == 'box',name
            assert app.scale_view_choice.get() == 'Аппликатуры'
            labels = shape_names(name)
            assert len(labels) == (7 if name in DIATONIC_OFFSETS else 5)
            available = app._scale_comboboxes[3].cget('values')
            assert len(available) == len(labels)+1,name
            app.scale_position_choice.set(labels[-1]);app._scale_option_changed();root.update()
            assert app.scale_box == len(labels),name
            expected = scale_fingering(app.tuning,name,NOTE_EN.index('D'),len(labels))
            assert len(app._scale_items()) == len(expected)
            assert len(app.board.find_withtag('scale_note')) == len(expected),(name,width)
            rightmost = max(widget.winfo_rootx()+widget.winfo_width() for widget in app._scale_comboboxes)
            assert rightmost <= root.winfo_rootx()+root.winfo_width(),(width,name,rightmost)
    app.scale_choice.set('Блюзовая');app.scale_key_choice.set('A');app._scale_option_changed();root.update()
    app.scale_position_choice.set('Box 1');app._scale_option_changed();root.update()
    assert len(app.board.find_withtag('blue_note')) == 2
    app.start_quiz();root.update()
    expected = len(app._scale_items());assert len(app.questions)==expected
    for q in app.questions:
        x = fret_center(q.fret,app.cell_width)-app.board.canvasx(0)
        y = TOP + q.row*ROW_H + ROW_H/2
        app._click_board(type('Click',(),{'x':x,'y':y})())
        assert app.checked and app.feedback_is_correct
        app.next_question()
    assert app.phase=='result'
    assert app.current_run['configuration']['scale_shape_family']=='blues_box'
    app.show_map();app.scale_choice.set('Мажор');app._scale_option_changed()
    app.scale_position_choice.set('3NPS 1');app._scale_option_changed();root.update()
    assert app._scale_items()[0][:2]==(5,10)  # D major starts at sixth-string D
    app.start_quiz();root.update()
    assert len(app.questions)==18
    q=app._current()
    x=fret_center(q.fret,app.cell_width)-app.board.canvasx(0)
    app._click_board(type('Click',(),{'x':x,'y':TOP+q.row*ROW_H+ROW_H/2})())
    assert app.checked and app.responses[0]['degree'] == '1'
    app.show_map()
    app.scale_position_choice.set('Авто');app._scale_option_changed()
    original=app.scale_box
    app.start_quiz();root.update()
    while app.phase=='quiz':
        q=app._current()
        x=fret_center(q.fret,app.cell_width)-app.board.canvasx(0)
        app._click_board(type('Click',(),{'x':x,'y':TOP+q.row*ROW_H+ROW_H/2})())
        app.next_question()
    app.show_map();assert app.scale_box == (original%7)+1
    app.scale_view_choice.set('Весь звукоряд');app._scale_option_changed();root.update()
    assert len(app._scale_items()) > 50
    app.scale_view_choice.set('Участок ладов');app._scale_option_changed();root.update()
    app.scale_position_choice.set('5');app._scale_option_changed();root.update()
    assert app._scale_area() == (5,9)
    root.destroy()
print('All 7 scale families: GUI selector, 3NPS/blues, auto, quiz, range/full and resize PASS')
