"""Smoke new chord / CAGED scale UI. Run under xvfb-run -a python tests/gui_forms_smoke.py."""
import os
import tempfile
import tkinter as tk
from unittest.mock import MagicMock
# Support standalone GUI smoke checks from the relocated tests directory.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vguitar_notes import NoteTrainer, fret_center, TOP, ROW_H
from vguitar_forms import caged_scale, power_chord, triad_voicing

with tempfile.TemporaryDirectory() as home:
    os.environ['VGUITAR_DATA_DIR']=home
    root=tk.Tk(); app=NoteTrainer(root)
    app.audio.play=MagicMock(return_value=True)
    app.audio.preload=MagicMock()
    for size in ('680x575','780x650','1024x768','1366x768'):
        root.geometry(size); root.update()
        app.change_mode('forms'); root.update()
        assert app.forms_options.winfo_manager()=='pack'
        assert app.mode_combo.get() == 'Формы', size
        assert root.winfo_rootx() <= app.mode_combo.winfo_rootx(), size
        assert app.mode_combo.winfo_rootx()+app.mode_combo.winfo_width() <= root.winfo_rootx()+root.winfo_width(), size
        assert app._forms_groups[-1].winfo_rootx()+app._forms_groups[-1].winfo_width() <= root.winfo_rootx()+root.winfo_width(),size
    app.forms_kind_choice.set('Power chord')
    app.forms_key_choice.set('G')
    app.forms_quality_choice.set('1–5–8')
    app.forms_strings_choice.set('6-я')
    app._forms_option_changed();root.update()
    assert [(r,f) for r,f,_,_ in app._forms_shape()]==[(5,3),(4,5),(3,5)]
    app.start_quiz();root.update()
    assert len(app.questions)==3
    for q in app.questions:
        app._click_board(type('Click',(),{'x':fret_center(q.fret,app.cell_width)-app.board.canvasx(0),
                                           'y':TOP+q.row*ROW_H+ROW_H/2})())
        assert app.checked and app.feedback_is_correct
        app.next_question();root.update()
    assert app.phase=='result' and app.current_run['configuration']['forms_key']=='G'
    app.show_map()
    app.forms_kind_choice.set('Трезвучие');app._forms_option_changed();root.update()
    app.forms_quality_choice.set('Минор')
    app.forms_strings_choice.set('1–2–3')
    app.forms_inv_choice.set('1-е обращение')
    app._forms_option_changed();root.update()
    assert app.forms_inversion==1 and app.forms_quality=='Минор'
    assert len(app._forms_shape())==3
    app.change_mode('caged')
    app.caged_key_choice.set('D')
    app.caged_form_choice.set('E')
    app.caged_view_choice.set('Мажорная гамма')
    app._caged_option_changed();root.update()
    assert app.caged_view=='major' and len(app._caged_shape())>12
    assert (5,10,50,'1') in app._caged_shape()
    app.caged_view_choice.set('Минорная гамма')
    app._caged_option_changed();root.update()
    assert app.caged_view=='minor'
    assert any(d=='♭3' for _,_,_,d in app._caged_shape())
    app.change_mode('name');root.update()
    assert app.phase=='ready'
    root.destroy()
print('GUI forms/CAGED scales smoke PASS')
