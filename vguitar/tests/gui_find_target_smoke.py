"""GUI contract for the high-contrast target note in the find-on-fretboard quiz."""
import os
import tempfile
import tkinter as tk
from unittest.mock import MagicMock
# Support standalone GUI smoke checks from the relocated tests directory.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vguitar_notes import NoteTrainer, FONT, ACCENT, AMBER

with tempfile.TemporaryDirectory() as d:
    os.environ['VGUITAR_DATA_DIR'] = d
    root = tk.Tk()
    root.geometry('680x575+0+0')
    app = NoteTrainer(root)
    app.audio.play = MagicMock(return_value=True)
    app.audio.preload = MagicMock()
    app.change_mode('find')
    app.start_quiz()
    root.update()
    assert app.phase == 'quiz'
    target = app._current()
    pc = app._pitch_class(target.row, target.fret)
    labels = []
    def descend(w):
        for child in w.winfo_children():
            if isinstance(child, tk.Label):
                labels.append(child)
            descend(child)
    descend(app.quiz_body)
    prominent = [l for l in labels if l.cget('text') == app._note_name(pc)
                 and int(l.cget('font').split(' ')[-2]) >= 30]
    assert prominent, [(l.cget('text'),l.cget('font')) for l in labels]
    assert prominent[0].cget('fg') in (ACCENT, AMBER)
    assert any(l.cget('text') == app._note_ru(pc) for l in labels)
    assert any('НАЙДИ НОТУ' in l.cget('text') for l in labels)
    app.show_map()
    root.destroy()
print('GUI find-target prominent note PASS')
