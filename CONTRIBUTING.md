# Contributing to vGUITAR

Thank you for helping improve guitar fretboard education. Contributions are welcome, including bug reports, guitar-theory corrections, accessible interface improvements, and focused pull requests.

## Development environment

- Python 3.9 or newer with Tkinter.
- Windows: launch with `RUN.bat`. For direct development: `python vguitar/vguitar_notes.py`.
- Dependencies are listed in `requirements.txt`.
- Keep changes focused and compatible with the current data format whenever possible.

## Validation

Before submitting a pull request, run:

```powershell
python -m unittest discover -s vguitar/tests -t vguitar -v
python -m py_compile vguitar/vguitar_notes.py vguitar/vguitar_visual.py vguitar/vguitar_i18n.py vguitar/vguitar_wood.py
```

Changes affecting the interface should also be checked manually on Windows. GUI smoke scripts live in `vguitar/tests/gui_*.py` and require a display. For v0.5.5, run `gui_fret_hardware_smoke.py`, `gui_localization_wood_smoke.py`, `gui_ear_theme_smoke.py`, and `gui_toolbar_responsive_smoke.py` alongside the unit tests. These scenarios use isolated temporary preferences; never commit real session files. GitHub Actions are not configured as a required verification step.

Musical accuracy matters: test pitch classes, string numbering, tunings, interval labels, and playable shape geometry when modifying exercises.

## Pull requests

Include a brief description of the behavior change, relevant tests, and screenshots when visual changes require them. Documentation and release notes should match the behavior actually present in the code. Existing release tags must not be rewritten.

## Privacy and repository hygiene

- Do not commit credentials, API keys, access tokens, private URLs, personal file IDs, local machine paths, or account-specific settings.
- Do not include real user exercise results, screenshots containing personal information, or internal coordination notes in issues, examples, or test fixtures.
- Keep local environment configuration and generated outputs outside version control. See `.gitignore`.
- Use sanitized sample data in tests and reports. Release materials should be reproducible from committed sources.
- The tracked engineering event log (`vguitar/docs/dev/events.json`) uses non-identifying event metadata only; never add external storage IDs or secret-bearing descriptions to it.

## Project references

- [User guide](vguitar/docs/USER_GUIDE.md)
- [Changelog](vguitar/docs/CHANGELOG.md)
- [v0.5.5 release notes](vguitar/docs/releases/v0.5.5.md)
- [License](LICENSE)
- [Security policy](SECURITY.md)
