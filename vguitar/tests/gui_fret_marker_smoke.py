"""GUI regressions: round fret-note badges and real fretboard position dots."""
import os
import tempfile
import tkinter as tk
from unittest.mock import MagicMock

# Support standalone GUI smoke checks from the relocated tests directory.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vguitar_notes import NoteTrainer, fret_inlay_centers, note_disc_bbox, ROW_H, TOP

with tempfile.TemporaryDirectory() as d:
    os.environ['VGUITAR_DATA_DIR'] = d
    root=tk.Tk()
    app=NoteTrainer(root)
    app.audio.play=MagicMock(return_value=True)
    root.geometry('1250x720+0+0')
    root.update()
    app.active_strings=6
    app.active_frets=12
    app.show_map()
    app.start_study()
    root.update()

    # Fretboard dots, unlike note discs, are not the open string / incidental frets.
    expected={3:1,5:1,7:1,9:1,12:2}
    for fret in range(13):
        matches=app.board.find_withtag(f'fret_inlay_{fret}')
        assert len(matches)==expected.get(fret,0),(fret,len(matches))
        for item in matches:
            assert app.board.type(item)=='oval'
            bbox=app.board.coords(item)
            assert abs((bbox[2]-bbox[0])-(bbox[3]-bbox[1])) < .1
            assert app.board.itemcget(item,'fill')=='#f1f5fa'
    discs=app.board.find_withtag('note_disc')
    assert len(discs)==6*13,len(discs)
    for disc in discs:
        x1,y1,x2,y2=app.board.coords(disc)
        assert abs((x2-x1)-(y2-y1)) < .1,(x1,y1,x2,y2)
        assert y1>=TOP and y2<TOP+6*ROW_H+1
    # Change to sparse frets on a WIDE window: note discs cannot stretch.
    app.active_frets=4
    app._draw_board()
    root.update()
    assert app.cell_width>=66
    for disc in app.board.find_withtag('note_disc'):
        x1,y1,x2,y2=app.board.coords(disc)
        assert x2-x1<=29 and abs((x2-x1)-(y2-y1))<.1
    app.phase='quiz';app.mode='find';app.start_quiz()
    root.update()
    assert len(app.board.find_withtag('note_disc'))==0
    assert len(app.board.find_withtag('fret_inlay_3'))==1
    root.destroy()
print('Fret marker + note circles GUI PASS')
