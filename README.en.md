<p align="center">
  <img src="vguitar/assets/vguitar-icon.png" width="160" alt="vGUITAR Note Trainer logo">
</p>

<h1 align="center">vGUITAR Note Trainer</h1>

<p align="center"><strong>Interactive guitar fretboard trainer for Windows</strong></p>

<p align="center"><a href="README.md">Русский</a> · <strong>English</strong></p>

<p align="center">
  <a href="https://github.com/TheColdVoid1337/vGUITAR/releases">Releases</a> ·
  <a href="vguitar/docs/USER_GUIDE.md">User guide (RU)</a> ·
  <a href="vguitar/docs/CHANGELOG.md">Changelog (RU)</a>
</p>

**Current version: 0.5.5 (alpha)** · Python 3.9+ / Tkinter · [MIT License](LICENSE)

**vGUITAR Note Trainer** is a Windows desktop application for learning fretboard notes, intervals, scales, and chord shapes. It combines note-identification, note-location, and ear-training exercises with dedicated practice modes for scales, CAGED, power chords, and triads.

The application runs locally without an account. An internet connection may be needed to install its dependencies for the first time.

## Features

- **Note recognition.** Identify notes from a string/fret position, find notes on the fretboard, or recognize a played note by ear.
- **Configurable fretboard.** Select individual strings or combinations, practice open strings through fret 24, and choose from multiple fretboard themes.
- **Scales and fingerings.** Major, natural minor, Dorian, Phrygian, major/minor pentatonic, and blues; seven three-notes-per-string (3NPS) positions for heptatonic scales and five boxes for pentatonic and blues scales.
- **CAGED.** Five major chord shapes with associated major and natural-minor scale maps.
- **Chord shapes.** R–5 and R–5–8 power chords; major, minor, and diminished triads with inversions and string-group selection. Shapes can display notes, scale degrees, or suggested fingers.
- **Audio and tunings.** Synthesized guitar notes, output-device settings, and alternate guitar tunings.
- **Progress tracking.** Answer accuracy and response times, locally saved exercise history and preferences, and JSON result export.

## Installation

**Requirements:** Windows, Python 3.9 or later with Tkinter, and an audio output device.

Clone the repository and start the trainer:

```powershell
git clone https://github.com/TheColdVoid1337/vGUITAR.git
cd vGUITAR
.\RUN.bat
```

Alternatively, [download the source code](https://github.com/TheColdVoid1337/vGUITAR/releases), extract it, and run `RUN.bat`.

On the first launch, the script creates a `.venv` environment and installs packages from `requirements.txt` when needed. This release does not include a prebuilt Windows installer.

## Updating and local data

Run `git pull --ff-only origin main` to update a Git clone, then launch `RUN.bat` again.

Local settings and training history are stored in `vguitar/data/` and are not committed. The first launch after upgrading safely copies any existing JSON data from the old root-level `settings/` and `results/` folders without deleting the originals. After confirming that the history is available, you may remove the old copies manually.

## Getting started

1. Use the **«Режим»** (Mode) dropdown to select **«Назвать»** (Name), **«Найти»** (Find), or **«На слух»** (Ear).
2. Set the strings, fret range, and question count. The **«Выбор…»** selector supports nonconsecutive and individual strings.
3. Optionally review the fretboard before starting the quiz.
4. Answer by choosing a note name or selecting a fretboard position.
5. Open **«История»** (History) to review results or copy a JSON report.

Use **«Гаммы»** (Scales), **«CAGED»**, and **«Формы»** (Shapes) to study musical structures. Each mode provides its own choices for key, pattern, and exercise.

The **⚙** button opens tuning, audio, and appearance settings. **«История»** opens exercise history. The [user guide](vguitar/docs/USER_GUIDE.md) provides further details (currently available in Russian).

## Documentation

- [User guide (Russian)](vguitar/docs/USER_GUIDE.md)
- [Changelog (Russian)](vguitar/docs/CHANGELOG.md)
- [v0.5.4 release notes (Russian)](vguitar/docs/releases/v0.5.4.md)
- [Version history](vguitar/docs/releases/HISTORY.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## About the application

Click the **?** button in the toolbar to see a brief help section, the current version, app icon, [developer profile](https://github.com/TheColdVoid1337), and [project repository](https://github.com/TheColdVoid1337/vGUITAR).

## Project status

vGUITAR is in **alpha**. Suggested fingering labels are learning aids rather than mandatory technique. Some conventional scale and chord patterns depend on the string intervals of the selected tuning.

Bugs and feature requests can be submitted through [GitHub Issues](https://github.com/TheColdVoid1337/vGUITAR/issues).

## License

Distributed under the [MIT License](LICENSE).
