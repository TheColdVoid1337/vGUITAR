"""Compact screen bounds for quiz modes; run under xvfb."""
import os,tempfile,tkinter as tk
from unittest.mock import MagicMock
# Support standalone GUI smoke checks from the relocated tests directory.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vguitar_notes import NoteTrainer
with tempfile.TemporaryDirectory() as rootdir:
 os.environ['VGUITAR_DATA_DIR']=rootdir
 root=tk.Tk();app=NoteTrainer(root);app.audio.play=MagicMock(return_value=True)
 errors=[]
 for w,h in ((680,575),(780,650),(1024,768),(1280,720),(1366,768),(1583,842)):
  root.geometry(f'{w}x{h}+0+0');root.update()
  for mode in ('name','find','ear','scale'):
   app.change_mode(mode);app.start_quiz();root.update()
   bottom=app.action_row.winfo_rooty()+app.action_row.winfo_height()-root.winfo_rooty()
   footer=app.status_label.winfo_rooty()+app.status_label.winfo_height()-root.winfo_rooty()
   right=max(app.board_card.winfo_rootx()+app.board_card.winfo_width(),
             app.quiz_card.winfo_rootx()+app.quiz_card.winfo_width()) - root.winfo_rootx()
   if bottom>h-14 or footer>h or right>w+2:
    errors.append((w,h,mode,'overflow',bottom,footer,right))
   if mode=='ear':
    # Frame must display replay instead of the answer wheel or note name.
    assert not hasattr(app,'target_note_label')
    assert any('Слушать ещё' in str(widget.cget('text'))
               for widget in app.quiz_body.winfo_children()[0].winfo_children()
               if isinstance(widget,tk.Button))
   app.show_map();root.update()
 print('GUI ear layout checked:',w,h)
 root.destroy()
 assert not errors,errors
print('EAR LAYOUT: PASS')
