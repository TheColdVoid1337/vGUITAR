"""About dialog and application icon for vGUITAR Note Trainer."""
from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
import webbrowser

AUTHOR = "TheColdVoid1337"
AUTHOR_URL = "https://github.com/TheColdVoid1337"
REPOSITORY_URL = "https://github.com/TheColdVoid1337/vGUITAR"
ICON_PATH = Path(__file__).resolve().parent / "assets" / "vguitar-icon.png"
VERSION_PATH = Path(__file__).resolve().parent.parent / "VERSION.json"
BACKGROUND = "#f8fbf8"
TEXT = "#17382d"
MUTED = "#5d756c"
LINK = "#057e62"


def app_version() -> str:
    """Read the single source of truth instead of duplicating the version."""
    try:
        data = json.loads(VERSION_PATH.read_text(encoding="utf-8"))
        return str(data["version"])
    except (OSError, KeyError, ValueError, TypeError):
        return "unknown"


def load_icon(master: tk.Misc) -> tk.PhotoImage | None:
    """Load the complete transparent PNG, without cropping its boundaries."""
    try:
        return tk.PhotoImage(master=master, file=str(ICON_PATH))
    except (OSError, tk.TclError):
        return None


def open_about(root: tk.Tk) -> tk.Toplevel:
    window = tk.Toplevel(root)
    window.title(f"О программе — vGUITAR {app_version()}")
    window.configure(bg=BACKGROUND)
    window.resizable(False, False)
    window.transient(root)
    panel = tk.Frame(window, bg=BACKGROUND, padx=34, pady=20)
    panel.pack(fill="both", expand=True)

    icon = load_icon(window)
    if icon is not None:
        # No canvas clipping or cover/zoom: the full square icon remains visible.
        window._vguitar_icon = icon
        tk.Label(panel, image=icon, bg=BACKGROUND, bd=0).pack(pady=(0, 10))

    tk.Label(panel, text="vGUITAR Note Trainer", bg=BACKGROUND, fg=TEXT,
             font=("Segoe UI", 16, "bold")).pack()
    tk.Label(panel, text=f"Версия {app_version()} · alpha", bg=BACKGROUND,
             fg=MUTED, font=("Segoe UI", 10)).pack(pady=(4, 12))
    tk.Label(panel, text="Тренажёр гитарного грифа, гамм и аккордов",
             bg=BACKGROUND, fg=TEXT, font=("Segoe UI", 10)).pack(pady=(0, 13))

    def link(label: str, url: str) -> None:
        widget = tk.Label(panel, text=label, bg=BACKGROUND, fg=LINK,
                          font=("Segoe UI", 10, "underline"), cursor="hand2")
        widget.pack(pady=3)
        widget.bind("<Button-1>", lambda _event: webbrowser.open_new_tab(url))

    tk.Label(panel, text="Разработчик", bg=BACKGROUND, fg=MUTED,
             font=("Segoe UI", 9)).pack()
    link(AUTHOR, AUTHOR_URL)
    link("GitHub · Исходный код проекта", REPOSITORY_URL)

    tk.Frame(panel, bg="#d4e8de", height=1).pack(fill="x", pady=(13, 9))
    tk.Label(panel, text="Краткая справка", bg=BACKGROUND, fg=TEXT,
             font=("Segoe UI", 10, "bold")).pack(anchor="w")
    tk.Label(
        panel,
        text=("Выберите режим в верхней панели. Для тренировки нот задайте "
              "струны, лады и количество вопросов. «Повторение» показывает "
              "карту нот перед тестом. Результаты доступны в «Истории»."),
        bg=BACKGROUND, fg=MUTED, font=("Segoe UI", 9),
        justify="left", wraplength=380,
    ).pack(anchor="w", pady=(5, 0))
    tk.Button(panel, text="Закрыть", command=window.destroy,
              bg="#d9f4e8", fg=TEXT, relief="flat", cursor="hand2",
              font=("Segoe UI", 10), padx=20, pady=6).pack(pady=(17, 0))

    window.bind("<Escape>", lambda _event: window.destroy())
    window.update_idletasks()
    width, height = window.winfo_reqwidth(), window.winfo_reqheight()
    x = root.winfo_rootx() + max(0, (root.winfo_width() - width) // 2)
    y = root.winfo_rooty() + max(0, (root.winfo_height() - height) // 2)
    window.geometry(f"+{x}+{y}")
    window.focus_set()
    window.grab_set()
    return window
