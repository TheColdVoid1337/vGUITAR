<p align="center">
  <img src="assets/vguitar-icon.svg" width="160" alt="vGUITAR Note Trainer app icon">
</p>

<h1 align="center">vGUITAR Note Trainer</h1>

<p align="center"><strong>Offline guitar fretboard, note recognition and fingering trainer for Windows</strong></p>

<p align="center"><a href="README.md">Русский</a> · <strong>English</strong></p>

<p align="center">
  <a href="docs/releases/v0.5.4.md">v0.5.4 release notes (RU)</a> ·
  <a href="docs/USER_GUIDE.md">User guide (RU)</a> ·
  <a href="https://github.com/TheColdVoid1337/vGUITAR/releases">GitHub releases</a>
</p>

**Version 0.5.4 (alpha)** · Python / Tkinter · offline after dependency installation · [MIT](LICENSE)

**vGUITAR** helps guitarists recognize fretboard notes without counting up from open strings, locate chord roots, and connect scale degrees to practical guitar shapes. It is a **Windows desktop app**, not an iPhone app; the icon merely uses a mobile-app-inspired aesthetic.

## Features

- **Six lesson modes:** Name, Find, Ear, Scales, CAGED and Shapes (the in-app labels are in Russian).
- **Select any individual string.** The **«Выбор…»** picker lets you practice just the 5th string or any custom combination; the existing strings counter still enables strings sequentially from the low E.
- **0–24 fretboard:** realistic fret spacing, note names, landmarks and multiple wood themes.
- **Seven scales:** major, natural minor, Dorian, Phrygian, major/minor pentatonic, and blues.
- **Actual fingerings:** seven 3NPS positions for seven-note scales, five boxes for pentatonic/blues scales, plus full-fretboard and fret-range study.
- **CAGED chord and scale shapes:** five major chord forms with linked major and natural-minor scale maps.
- **Chord shape trainer:** movable two- and three-note power chords, major/minor/diminished triads, three inversions and four string groups.
- **Audio feedback:** synthesized plucked notes, ear practice, configurable tunings and Windows audio output.
- **Local progress:** accuracy, response times, saved session history and machine-readable JSON exports.

## Get started

Requires **Windows, Python 3.9+**, Tkinter and audio output.

```powershell
git clone https://github.com/TheColdVoid1337/vGUITAR.git
cd vGUITAR
.\RUN.bat
```

`RUN.bat` prepares `.venv` and installs `sounddevice` when necessary. Internet access may be needed for the initial installation; the trainer itself does not require an account or online service.

### Quick exercises

**Isolate the A string:** choose **«Назвать»** (Name), click **«Выбор…»**, select only **5-я (A)**, and practice frets 0–7. Switch to **«Найти»** (Find) to train the reverse direction.

**Memorize chord roots:** select strings 6 and 5, frets 0–7, then practice G5 rooted at low E3 and C5 rooted at A3 using **«Формы»** (Shapes).

**Play a true pentatonic box:** **«Гаммы» → «Минорная пентатоника» → A → «Аппликатуры» → Box 1**. Unlike a generic fret range, the box contains only its defined shape notes.

## Training modes

| In-app button | What it does |
|---|---|
| **Назвать** | Name the note shown at a string/fret |
| **Найти** | Find a requested note on the indicated string |
| **На слух** | Identify an audible note on the fretboard |
| **Гаммы** | Study scale positions, intervals and full-scale maps |
| **CAGED** | Connect chord roots, five shapes and major/minor patterns |
| **Формы** | Practice power chords, triads, inversions and finger suggestions |

The timed **«Повторение»** preview can precede a quiz. Press **Space** for the next question after answering, or **Esc** to return to preparation.

## Data, tunings and development

Preferences are stored in `settings/` and session results in `results/`, next to the application. Open **«История»** to inspect previous sessions and copy a JSON export containing exact selected strings, scores and individual answer times.

The audio and tuning settings include standard, down-tuned, Drop/Open and custom tunings. Some conventional scale or chord fingering generators require standard relative string intervals; unsupported tuning layouts are not silently presented as canonical shapes.

Run the unit tests locally:

```powershell
python -m unittest discover -s tests -v
python -m py_compile vguitar_notes.py
```

GUI smoke scripts live under `tests/gui_*.py` and require a graphical display or Xvfb. **GitHub Actions are intentionally disabled.** Documentation is gated by `#syncdocs`; the machine-readable change journal lives at `docs/dev/events.json`.

## Documentation and releases

- [Russian user guide](docs/USER_GUIDE.md)
- [Russian changelog](docs/CHANGELOG.md)
- [v0.5.4 release notes](docs/releases/v0.5.4.md)
- [Historical tags and local GitHub release procedure](docs/releases/HISTORY.md)
- [Русский README](README.md)

## License

[MIT License](LICENSE).
