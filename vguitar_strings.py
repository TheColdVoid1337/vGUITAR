"""Individual physical guitar-string selection. Rows run 1 (thin) to 6 (thick)."""
STRING_NUMBERS = (6, 5, 4, 3, 2, 1)


def strings_from_count(count: int) -> tuple[int, ...]:
    """Legacy contiguous low-string selection for counter values 1..6."""
    if isinstance(count, bool) or not isinstance(count, int):
        count = 2
    return STRING_NUMBERS[:max(1, min(6, count))]


def normalize_selected_strings(value: object, count: int = 2) -> tuple[int, ...]:
    """Sort valid selected strings, falling back to count for old settings."""
    if (isinstance(value, (tuple, list)) and value
            and all(isinstance(n, int) and not isinstance(n, bool)
                    and 1 <= n <= 6 for n in value)):
        return tuple(sorted(set(value), reverse=True))
    return strings_from_count(count)


def rows_for_strings(strings: tuple[int, ...]) -> tuple[int, ...]:
    """Physical string 5 maps to Tk row 4, 6 maps to row 5."""
    return tuple(sorted(number - 1 for number in strings))
