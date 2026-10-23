"""UI localization adapters. Stored exercise/settings tokens remain canonical."""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

_LANGUAGE = "ru"
TEXT = {
    "Настройки": "Settings",
    "История": "History",
    "Аудио": "Audio",
    "Гриф": "Fretboard",
    "ГРИФ": "FRETBOARD",
    "ПОВТОРЕНИЕ": "STUDY",
    "Подготовка": "Preparation",
    "Строй": "Tuning",
    "Струны": "Strings",
    "Струна": "String",
    "Лады": "Frets",
    "лад": "fret",
    "лады": "frets",
    "Вопросы": "Questions",
    "Вопрос": "Question",
    "Повтор": "Study",
    "Режим": "Mode",
    "Назвать": "Name",
    "Найти": "Find",
    "На слух": "Ear training",
    "Гаммы": "Scales",
    "Формы": "Chord forms",
    "Нота": "Note",
    "Выбор…": "Choose…",
    "Выбор струн": "String selection",
    "Какие струны тренировать?": "Which strings would you like to practice?",
    "Можно выбрать одну или несколько. Нужна хотя бы одна.": "Choose one or more strings. At least one is required.",
    "Нужно выбрать хотя бы одну струну.": "Select at least one string.",
    "Отмена": "Cancel",
    "Сохранить": "Save",
    "Закрыть": "Close",
    "Применить": "Apply",
    "Общие": "General",
    "Язык": "Language",
    "Выберите язык": "Choose a language",
    "Язык интерфейса": "Interface language",
    "Накладка грифа": "Fretboard wood",
    "Оригинальная": "Original",
    "Черное дерево (Ebony)": "Ebony",
    "Клён (Maple)": "Maple",
    "Палисандр (Rosewood)": "Rosewood",
    "Текстура дерева": "Wood grain texture",
    "Рандомизировать": "Randomize grain",
    "Для оригинальной накладки текстура недоступна.": "The original virtual fretboard has no wood texture.",
    "Цвета меняют только накладку, не интерфейс теста.": "Wood selection changes only the fretboard surface.",
    "Громкость": "Volume",
    "Аудиоустройство": "Output device",
    "Обновить список": "Refresh devices",
    "Задержка": "Latency",
    "Буфер": "Buffer",
    "Надёжная": "Reliable",
    "Низкая": "Low",
    "Авто": "Auto",
    "Авто · WASAPI": "Auto · WASAPI",
    "♫ Тест": "♫ Test",
    "Лог звука": "Audio log",
    "Проверка звука": "Sound check",
    "Shared: по умолчанию · Exclusive: устройство занято только vGUITAR": "Shared: default · Exclusive: the device is reserved for vGUITAR",
    "Тренажёр гитарного грифа, гамм и аккордов": "Guitar fretboard, scales and chords trainer",
    "Версия": "Version",
    "Разработчик": "Developer",
    "О программе": "About",
    "Краткая справка": "Quick help",
    "GitHub · Исходный код проекта": "GitHub · Project source code",
    "Ряды": "Rows",
    "Круг": "Circle",
    "Расположение нот-ответов. Для режима «Назвать ноту».": "Answer layout for Note Naming mode.",
    "Гамма": "Scale",
    "Вид": "View",
    "Позиция": "Position",
    "Тип": "Type",
    "Форма": "Shape",
    "Аккорд": "Chord",
    "Обращение": "Inversion",
    "Подписи": "Labels",
    "Аппликатуры": "Fingerings",
    "Участок ладов": "Fret range",
    "Весь звукоряд": "Full fretboard",
    "Мажор": "Major",
    "Натуральный минор": "Natural minor",
    "Минорная пентатоника": "Minor pentatonic",
    "Мажорная пентатоника": "Major pentatonic",
    "Блюзовая": "Blues",
    "Дорийский": "Dorian",
    "Фригийский": "Phrygian",
    "Мажорная гамма": "Major scale",
    "Минорная гамма": "Minor scale",
    "Трезвучие": "Triad",
    "Минор": "Minor",
    "Уменьшённый": "Diminished",
    "Основной вид": "Root position",
    "1-е обращение": "1st inversion",
    "2-е обращение": "2nd inversion",
    "Ноты": "Notes",
    "Ступени": "Degrees",
    "Пальцы": "Fingers",
    "Свой строй": "Custom tuning",
    "Настройки: строй, звук и оформление грифа.": "Tuning, audio, and fretboard appearance settings.",
    "История занятий и экспорт результатов.": "Session history and result export.",
    "О программе, помощь и ссылки.": "About, help, and links.",
    "Нажми струну и лад перед тестом или при повторении, чтобы услышать звук.": "Click a string and fret to hear the note before or during a study session.",
    "Отметь отдельные струны, например только пятую.": "Select individual strings, for example only the fifth.",
    "Счётчик: 6-я, затем 5-я и так далее. Для одной струны — «Выбор…».": "Count strings starting from the 6th; use Choose for individual strings.",
    "Диапазон 0–N, включая открытую струну.": "Fret range 0–N, including open strings.",
    "Число заданий в одном тесте.": "Number of questions per quiz.",
    "Сколько секунд показывать ноты до теста.": "How many seconds to show notes before the quiz.",
    "Начать повторение с таймером; ноты уже видны в подготовке.": "Start timed study; notes are already visible in preparation.",
    "Начальное звучание автоматическое; ещё 3 повтора на каждый вопрос.": "The first note plays automatically; three additional replays are available.",
    "Результат сохранён в локальной истории": "Result saved to local history",
    "Параметры изменены": "Settings updated",
    "Режим изменён": "Mode changed",
    "Гамма или аппликатура изменена": "Scale or fingering updated",
    "Аккорд или форма изменены": "Chord or shape updated",
    "Аккордовая аппликатура изменена": "Chord fingering updated",
    "Выбранные струны изменены": "String selection updated",
    "Строй изменён. Изучи обновлённые ноты перед тестом.": "Tuning changed. Study the updated notes before the quiz.",
    "Карта открыта. Изучи ноты перед тестом.": "Fretboard ready. Study the notes before the quiz.",
    "Нажимай ноты, чтобы услышать их.": "Click notes to hear them.",
    "Повторение ▶": "Study ▶",
    "Начать тест →": "Start quiz →",
    "Итог →": "Results →",
    "Дальше →": "Next →",
    "Прервать": "Abort",
    "Повторить": "Try again",
    "Без ошибок!": "No mistakes!",
    "Ошибки": "Mistakes",
    "Результат": "Result",
    "Итог": "Results",
    "Точность": "Accuracy",
    "Среднее": "Average",
    "Медиана": "Median",
    "Область": "Range",
    "Дата UTC": "Date UTC",
    "История тестов": "Quiz history",
    "Запусков": "Sessions",
    "Повреждено": "Corrupted",
    "Выбери хотя бы один запуск.": "Select at least one session.",
    "Export Selected Runs for LLM": "Export selected runs for LLM",
    "Копирует выбранные запуски, включая время каждого ответа, в буфер обмена.": "Copies selected sessions, including each answer time, to clipboard.",
    "Скопировать JSON-отчёт теста в буфер обмена.": "Copy the quiz JSON report to clipboard.",
    "НАЙДИ НОТУ": "FIND THE NOTE",
    "НА СЛУХ · НАЙДИ ВЫСОТУ НА ГРИФЕ": "EAR TRAINING · FIND THE PITCH",
    "Слушать ещё": "Replay",
    "открытая": "open",
    "Правильно": "Correct",
    "Верно": "Correct",
    "Повторение": "Study",
    "весь гриф": "full fretboard",
    "участок": "range",
    "Найди на струне": "Find on string",
    "Ступень": "Degree",
    "струна": "string",
    "струне": "string",
    "Локальные папки недоступны": "Local folders unavailable",
    "Не удалось сохранить настройки": "Could not save settings",
    "Не удалось сохранить строй": "Could not save tuning",
    "Не удалось сохранить результат": "Could not save result",
    "Сохранение результата": "Saving result",
    "Экспорт": "Export",
    "Буфер обмена": "Clipboard",
    "Прервать тест": "Abort quiz",
    "Текущий тест не будет сохранён. Прервать?": "The current quiz will not be saved. Abort?",
    "Тест прерван": "Quiz aborted",
    "Упражнение недоступно": "Exercise unavailable",
    "Позиция недоступна": "Position unavailable",
    "Форма недоступна": "Shape unavailable",
    "CAGED недоступен": "CAGED unavailable",
    "3 ноты на каждой струне": "3 notes per string",
    "2 ноты на каждой струне": "2 notes per string",
    "Блюзовая ♭5 — фиолетовая": "Blue note ♭5 is purple",
    "корни — янтарные": "roots are amber",
    "Power chords: корень и квинта; трезвучия: три обращения. Пальцы — подсказка.": "Power chords use roots and fifths; triads have three inversions. Finger labels are suggestions.",
    "CAGED: пять семей форм; минорная гамма показывает ♭3, ♭6, ♭7.": "CAGED has five shape families; the minor scale marks ♭3, ♭6, ♭7.",
    "Тест": "Test",
    "Скопировано! Вставь Ctrl+V в чат.": "Copied! Paste it into your chat.",
    "Готов к повторению?": "Ready to study?",
    "Выбери область и запусти повторение.": "Choose a fretboard area to study.",
    "точно": "correct",
    "среднее": "average",
    "медиана": "median",
    "нет": "none",
    "Запусков:": "Sessions:",
    "Правильно:": "Correct:",
    "Как пользоваться": "How to use",
    "Плеер сообщил об ошибке. Нажми «Лог звука» и пришли его в чат.": "Audio output reported an error. Copy the Audio log and share it for troubleshooting.",
    "Если звук не слышен, проверь микшер Windows и устройство вывода, затем пришли «Лог звука».": "If you hear nothing, check Windows volume mixer and the output device, then copy the Audio log.",
    "какая нота?": "which note?",
    "Корень": "Root",
    "Большая терция": "Major third",
    "Квинта": "Fifth",
    "позиции": "positions",
    "ладу": "fret",
    "Выбрано запусков": "Selected sessions",
    "Справка и о программе": "Help and About",
    "подготовка": "preparation",
    "с": "s",
}
_EN_TO_RU = {english: russian for russian, english in TEXT.items()}


def set_language(language: str) -> None:
    global _LANGUAGE
    _LANGUAGE = language if language in ("ru", "en") else "ru"


def get_language() -> str:
    return _LANGUAGE


def tr(value: str, language: str | None = None) -> str:
    """Translate interface strings, without changing canonical model values."""
    if not isinstance(value, str) or (language or _LANGUAGE) != "en":
        return value
    if value in TEXT:
        return TEXT[value]
    translated = value
    for russian, english in sorted(TEXT.items(), key=lambda pair: -len(pair[0])):
        if russian in translated and re.search("[А-Яа-яЁё]", russian):
            translated = re.sub(r"(?<!\w)" + re.escape(russian) + r"(?!\w)",
                                lambda _match: english, translated)
    return translated


def from_display(value: str) -> str:
    return _EN_TO_RU.get(value, value) if _LANGUAGE == "en" else value


class LocalizedVar(tk.StringVar):
    """Tcl displays translation; Python getters return stable Russian tokens."""
    def __init__(self, master=None, value=None, name=None):
        # Tk Variable.__init__ bypasses the overridden set() for initial values.
        super().__init__(master=master, value=tr(value) if value is not None else None,
                         name=name)

    def get(self) -> str:
        return from_display(super().get())

    def set(self, value: str) -> None:
        super().set(tr(value))


class LocalizedCombobox(ttk.Combobox):
    """Keep drop-down option values translated, including after configure."""
    def __init__(self, master=None, **kw):
        if "values" in kw:
            kw["values"] = [tr(str(v)) for v in kw["values"]]
        super().__init__(master, **kw)

    def configure(self, cnf=None, **kw):
        if isinstance(cnf, dict):
            cnf = dict(cnf)
            if "values" in cnf:
                cnf["values"] = [tr(str(v)) for v in cnf["values"]]
        if "values" in kw:
            kw["values"] = [tr(str(v)) for v in kw["values"]]
        return super().configure(cnf, **kw)

    config = configure

    def set(self, value):
        super().set(tr(str(value)))
