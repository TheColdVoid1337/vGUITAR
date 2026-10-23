"""Manual GUI layout & note-choice smoke check (run under xvfb on Linux)."""
import math
import os
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import MagicMock
try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

# Support standalone GUI smoke checks from the relocated tests directory.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vguitar_notes import NoteTrainer, NOTE_EN

OUT=Path(os.getenv('VGUITAR_SCREENSHOTS', str(Path(tempfile.gettempdir()) / 'vguitar_previews')))
OUT.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as folder:
    os.environ['VGUITAR_DATA_DIR']=folder
    root=tk.Tk()
    app=NoteTrainer(root)
    app.audio.play=MagicMock(return_value=True)
    failures=[]
    for w,h in ((680,575),(780,650),(1024,768),(1280,720),(1366,768),(1583,842)):
        root.geometry(f'{w}x{h}+0+0')
        root.update()
        for phase, layout in (('ready','rows'), ('quiz','rows'),('quiz','circle'),('result','rows')):
            app.show_map()
            app.change_answer_layout(layout)
            if phase in ('quiz','result'):
                app.start_quiz()
            if phase=='result':
                while app.phase=='quiz':
                    if not app.checked:
                        q=app._current()
                        app.answer_name(app._pitch_class(q.row,q.fret))
                    app.next_question()
            root.update()
            y_bottom=app.action_row.winfo_rooty()+app.action_row.winfo_height()-root.winfo_rooty()
            footer_bottom=app.status_label.winfo_rooty()+app.status_label.winfo_height()-root.winfo_rooty()
            right=max(app.quiz_heading.winfo_rootx()+app.quiz_heading.winfo_width(),app.action_row.winfo_rootx()+app.action_row.winfo_width())-root.winfo_rootx()
            # Regression: no phantom empty grid column, all cards fill the work area.
            work_left=app.content_area.winfo_rootx()
            work_right=work_left+app.content_area.winfo_width()
            panels_right=max(app.board_card.winfo_rootx()+app.board_card.winfo_width(),
                             app.quiz_card.winfo_rootx()+app.quiz_card.winfo_width())
            if abs(panels_right-work_right)>8:
                failures.append((w,h,phase,layout,'unused-right-space',work_right-panels_right))
            if app.toolbar.winfo_rootx()+app.toolbar.winfo_width()>root.winfo_rootx()+w+2:
                failures.append((w,h,phase,layout,'toolbar-oversized'))
            if y_bottom>h-15 or footer_bottom>h or right>w:
                failures.append((w,h,phase,layout,y_bottom,footer_bottom,right))
            if ImageGrab is not None:
                ImageGrab.grab(bbox=(0,0,w,h)).save(OUT/f'{w}x{h}_{phase}_{layout}.png')
            if phase=='quiz' and layout=='circle':
                if app._answer_wheel.winfo_rooty()+app._answer_wheel.winfo_height() > root.winfo_rooty()+h-20:
                    failures.append((w,h,'circle clipped'))
                natural={0,2,4,5,7,9,11}
                assert len(app.answer_wheel_regions)==12
                assert len(natural & set(app.answer_wheel_regions))==7
                assert len(set(app.answer_wheel_regions)-natural)==5
                pc=1
                x,y,r=app.answer_wheel_regions[pc]
                app._answer_wheel.event_generate('<Button-1>',x=round(x),y=round(y))
                root.update()
                assert app.checked and app._chosen_pc==pc, (w,h,app.checked,app._chosen_pc)
        print('CHECK',w,h,'full:',root.winfo_height(),'bottom:',y_bottom,'footer:',footer_bottom)
    app.change_answer_layout('circle')
    from vguitar_storage import read_preferences
    assert read_preferences()['lesson']['answer_layout']=='circle'
    root.destroy()
    if failures:
        raise AssertionError(f'Layout overflow: {failures}')
    print('LAYOUT OK: 680x575, 780x650, 1024x768, 1280x720, 1366x768, 1583x842; both note layouts')
