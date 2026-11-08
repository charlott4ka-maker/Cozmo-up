#!/usr/bin/env python
"""Шаг 8. Русский текст на экране робота.

Встроенный шрифт PIL знает только латиницу, поэтому для кириллицы нужен
TTF-шрифт. cozmo_up.screen сам найдёт подходящий в системе (DejaVu, Arial,
Segoe UI...) и проверит, что в нём реально есть русские буквы.

Если шрифт не нашёлся — укажите свой:
    COZMO_FONT=/путь/к/шрифту.ttf python examples/08_russian_screen.py
"""

import sys
import time
from pathlib import Path

import pycozmo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.screen import find_font, preview, render_text  # noqa: E402

PHRASES = [
    "ПРИВЕТ!",
    "Меня зовут\nКозмо",
    "Я говорю\nпо-русски",
    "Поехали!",
]


def main() -> int:
    # Сначала покажем всё в терминале — так видно результат даже без робота.
    print(f"Шрифт: {find_font(18).path}\n")
    for phrase in PHRASES:
        print(phrase.replace("\n", " / "))
        preview(render_text(phrase))
        print()

    with pycozmo.connect() as cli:
        for phrase in PHRASES:
            print(f"На экране: {phrase!r}")
            cli.display_image(render_text(phrase), duration=2.0)

        # Текст можно строить на лету — например, показать заряд батареи.
        cli.wait_for(pycozmo.event.EvtRobotStateUpdated, timeout=2.0)
        cli.display_image(
            render_text(f"Батарея\n{cli.battery_voltage:.2f} В"), duration=3.0
        )

        time.sleep(0.5)
        cli.clear_screen()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
