# vGUITAR Note Trainer — English user guide

**v0.5.5 (alpha)** · [English README](../../README.en.md) · [Руководство на русском](USER_GUIDE.md)

## Installation and first launch

Windows with **Python 3.9+ (Tkinter)** and an audio output device is required. Run **RUN.bat** from the repository root; it creates a local Python environment and installs missing audio dependencies if needed. To update an existing clone, use `git pull --ff-only origin main`, then **RUN.bat**.

If the preferences file does not exist, select **ENGLISH** or **РУССКИЙ** in the language-choice window. This choice is stored locally and is not requested on later launches. Change language using **⚙ → Language**, not the main toolbar.

## Toolbar and settings

Select **Name**, **Find**, **Ear training**, **Scales**, **CAGED** or **Chord forms** from the Mode dropdown. Counter groups stay in place and are disabled where irrelevant. **⚙** opens Settings, **📖** opens History and **?** opens About (version, icon and project links).

Settings has **Tuning**, **Audio**, **Fretboard** and **Language** tabs. Audio Test and Audio Log are within **Audio**. Changing fretboard appearance shows a preview immediately; **Save** persists it, **Cancel** restores the prior values.

## Fretboard appearance (Settings → Fretboard)

Click one of four swatches: **Original** (virtual blue surface), **Ebony** (almost black), **Maple** (light cream/honey) or **Rosewood** (dark reddish brown). Ebony distinguishes inactive parts by a subtle gray tone. Switch **Wood grain texture** on for a separate procedural layer underneath the strings and frets; **Randomize grain** produces a new irregular pattern. The random seed is saved with preferences, so the pattern does not change on resize. Original has no wood texture.

The page scrolls vertically on short screens. The rest of its controls are **visual only**, affecting the color and stroke width of the drawing rather than actual sound, tuning, MIDI pitches or clickable note locations.

| Control | Choices |
|---|---|
| String gauge | 8–38, 9–42, 9–46, 10–46, 10–52, 11–48, 12–56 (thousandths of an inch, strings 1–6) |
| String finish | Nickel-plated steel, pure nickel, stainless steel, cobalt alloy |
| Nut thickness | **3–8 mm** in **0.5 mm** increments |
| Nut material/finish | Plastic, bone, TUSQ, graphite, brass, copper |
| Fret crown width | 2.03, 2.28, 2.41, 2.54, 2.79, 2.99 mm; **SINTOMS 4.3mm** |
| Fret wire material/finish | Nickel silver, stainless steel, EVO Gold |
| Position marker radius | **2.5–7.5 px**, 0.5-pixel increments |

Legacy settings for **ash** and **mahogany** are mapped to Maple and Rosewood. Local appearance and selected language are persisted without deleting training history.

## Fretboard layout and selected strings

The display has six strings: first/high E at the top, sixth/low E at the bottom. Standard tuning from sixth to first is **E A D G B E**. Fret 0 denotes an open string; the fretboard extends to 24.

For Name/Find/Ear training, the **Strings** counter selects consecutive low strings starting with string 6. **Choose…** instead lets you select any individual strings or nonadjacent combination (for example, only string 5). Changing the counter restores the consecutive low-string selection.

## A typical practice session

1. Choose a mode in **Mode**, set strings, fret range and number of questions (5–100).
2. Study the note map in preparation, optionally with a timed **Study** countdown.
3. Start the test: in **Name**, identify the displayed note; in **Find**, locate the requested note on the given string; in **Ear**, locate the sounded absolute pitch.
4. Respond through the buttons or fretboard. After a checked answer, **Space** goes to the next question; **Esc** returns to preparation. Ear training permits up to three additional replays.
5. Open **📖** to inspect results, accuracy and response times or copy JSON reports for one or several sessions.

## Scales, CAGED and chord forms

Seven scales are provided: major, natural minor, Dorian, Phrygian, major and minor pentatonic, and blues. **Fingerings** limits the map to a genuine position; **Full fretboard** displays all scale notes, while **Fret range** is an arbitrary window and should not be confused with a standard guitar fingering. Seven 3NPS positions serve heptatonic scales, and pentatonic/blues scales have five boxes. The blues scale adds the ♭5 blue note.

In **CAGED**, select a root and one of five C/A/G/E/D shapes, then choose chord, major-scale or natural-minor-scale views. Some shapes need standard intervals between adjacent strings.

**Chord forms** covers two- and three-note power chords **R–5 / R–5–8**, and major/minor/diminished triads with root position and first/second inversion. Display labels can show notes, scale degrees or suggested fingers; suggestions are not mandatory technique.

## Local data and limitations

Settings and exercise results are stored locally under **vguitar/data/settings/** and **vguitar/data/results/**. On first launch after the folder migration, the app copies legacy JSON from the old root-level **settings/** and **results/** folders without deleting the originals. The data is ignored by Git.

This is **alpha** software released as source code, without a Windows installer or automated GitHub CI. Validate GUI and sound on your own Windows installation. See [Changelog](CHANGELOG.md) and [v0.5.5 release notes](releases/v0.5.5.md).
