# Contributing to vGUITAR

Thank you for helping make guitar practice easier and more accessible.

## Scope

vGUITAR is a small, offline-first guitar-learning project. Prefer focused changes, straightforward Python, clear guitar-theory explanations, and standard-library solutions.

## Development

1. Use Python 3.9 or newer with Tkinter available.
2. Launch the application with `python vguitar_notes.py` (Windows: `RUN.bat`).
3. Run `python -m unittest discover -s tests -v`.
4. Run `python -m py_compile vguitar_notes.py`.
5. If you change pitch classes, tuning, or quiz logic, add or update tests.

## Pull requests

Describe the problem, user-facing behavior, tests run, and screenshots **only when UI changes justify them**. Keep generated ZIP files, screenshots, local environments, and caches out of the repository.

Documentation is **frozen by default**: do not change README, CONTRIBUTING, SECURITY, code of conduct, or explanatory docs unless the project owner explicitly issues `#syncdocs`. The operational JSON event log under `docs/dev/` is exempt from this freeze and must be updated with **every repository/asset action**.

## Asset storage and traceability

Source code belongs in GitHub. Non-repository release bundles and screenshots belong in the dedicated project Google Drive folder. Before uploading, check its `file_index.json` for the same logical asset or SHA-256. Update the index **in place**, preserving file IDs when replacing an existing asset; do not create duplicate copies by default.

Every GitHub change must be represented in `docs/dev/events.json` as a machine-readable action event. Document synchronization requires an explicit `#syncdocs`.

## Conduct and security

Follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) and [SECURITY.md](SECURITY.md).
