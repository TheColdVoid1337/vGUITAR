"""Interactive/in-memory Tk geometry + Space/Audio settings smoke test."""
import os, tempfile, tkinter as tk
from tkinter import ttk
from unittest.mock import MagicMock
from vguitar_notes import NoteTrainer, TOP, ROW_H, OPEN_WIDTH
from vguitar_storage import read_preferences
with tempfile.TemporaryDirectory() as d:
    os.environ['VGUITAR_DATA_DIR']=d
    root=tk.Tk();root.geometry('1024x768+0+0')
    app=NoteTrainer(root);app.audio.play=MagicMock(return_value=True)
    app.active_frets=12;app.active_strings=6
    root.update();app.show_map();root.update()
    lines=app.board.find_withtag('guitar_string')
    assert len(lines)==6, lines
    widths=[]
    for ix, line in enumerate(lines):
        coords=app.board.coords(line)
        assert len(coords)==4 and coords[1]==coords[3]
        assert coords[0]<OPEN_WIDTH and coords[2]>OPEN_WIDTH+app.cell_width*11
        widths.append(float(app.board.itemcget(line,'width')))
    assert widths==sorted(widths) and widths[-1]>widths[0]*2, widths
    nuts=app.board.find_withtag('nut')
    frets=app.board.find_withtag('fret_wire')
    assert len(nuts)==1 and len(frets)==11
    x1,y1,x2,y2=app.board.coords(nuts[0])
    assert abs((x1+x2)/2-OPEN_WIDTH)<1
    for fret in frets:
        x1,y1,x2,y2=app.board.coords(fret)
        assert y1>TOP and y2<TOP+ROW_H*6
        assert float(app.board.itemcget(fret,'width'))<x2-x1+2 # geometric sanity
    app.start_study();app.start_quiz();root.update()
    q=app._current();app.answer_name(app._pitch_class(q.row,q.fret));root.update()
    assert app.checked
    root.focus_force()
    root.event_generate('<space>');root.update()
    assert app.index==1 or app.phase=='result'
    app.open_settings();root.update()
    win=app._settings_window
    tabs=[]
    def walk(widget):
        if isinstance(widget,ttk.Notebook):tabs.append(widget)
        for child in widget.winfo_children():walk(child)
    walk(win)
    assert tabs and tabs[0].tabs() and len(tabs[0].tabs())==3
    tabs[0].select(1);root.update()
    assert win.winfo_height()<=768 and win.winfo_width()<=1024
    win.destroy();root.destroy()
print('FRETBOARD, SPACE, AUDIO UI SMOKE PASS')
