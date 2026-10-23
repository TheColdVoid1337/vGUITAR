"""Capture a genuine Tk application screenshot for project documentation.

Run from the repository root:
    .\\.venv\\Scripts\\python.exe -m pip install Pillow
    .\\.venv\\Scripts\\python.exe vguitar\\scripts\\capture_screenshot.py

On Linux with a virtual display:
    xvfb-run -a python vguitar/scripts/capture_screenshot.py

Uses temporary application data to avoid modifying saved exercise sessions.
The output can be reviewed before being committed to the public README.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk

try:
    from PIL import ImageGrab
except ImportError as exc:
    raise SystemExit("Pillow is required for screenshot capture: python -m pip install Pillow") from exc

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = PROJECT_ROOT / "vguitar"
sys.path.insert(0, str(APP_DIR))
from vguitar_notes import NoteTrainer


def capture() -> Path:
    target = APP_DIR / "assets" / "screenshot-main.png"
    with tempfile.TemporaryDirectory(prefix="vguitar-screenshot-") as private_data:
        original_data_dir = os.environ.get("VGUITAR_DATA_DIR")
        os.environ["VGUITAR_DATA_DIR"] = private_data
        root = tk.Tk()
        try:
            root.geometry("1180x800+30+30")
            app = NoteTrainer(root)
            app.active_frets = 7
            app.active_strings = 6
            app.selected_strings = (6, 5, 4, 3, 2, 1)
            app.change_mode("name")
            root.update_idletasks()
            root.update()
            # ImageGrab captures the genuine rendered application, not a
            # simulated mockup. The screenshot includes the entire client UI.
            x, y = root.winfo_rootx(), root.winfo_rooty()
            w, h = root.winfo_width(), root.winfo_height()
            shot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
            target.parent.mkdir(parents=True, exist_ok=True)
            shot.save(target, optimize=True)
            app.audio.close()
        finally:
            root.destroy()
            if original_data_dir is None:
                os.environ.pop("VGUITAR_DATA_DIR", None)
            else:
                os.environ["VGUITAR_DATA_DIR"] = original_data_dir
    return target


if __name__ == "__main__":
    print(f"Captured: {capture()}")
