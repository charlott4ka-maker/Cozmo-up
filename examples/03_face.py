#!/usr/bin/env python
"""Шаг 3. Экран: эмоции и своя картинка.

pycozmo рисует лицо Cozmo у себя (процедурно) и отправляет
готовое изображение 128x64 на OLED-экран робота.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

import pycozmo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.screen import SCREEN_SIZE, to_screen  # noqa: E402


def show_expressions(cli) -> None:
    """Проиграть несколько готовых выражений лица."""
    for expression in (
        pycozmo.expressions.Happiness,
        pycozmo.expressions.Surprise,
        pycozmo.expressions.Anger,
        pycozmo.expressions.Sadness,
        pycozmo.expressions.Neutral,
    ):
        print(f"  {expression.__name__}")
        # ВАЖНО: .render() отдаёт 128x64, а display_image принимает ровно
        # 128x32 — иначе ValueError. to_screen() приводит к нужному виду.
        image = to_screen(expression().render())
        # duration: pycozmo сам подождёт и очистит экран.
        cli.display_image(image, duration=1.5)


def show_custom_text(cli, text: str) -> None:
    """Нарисовать свой текст на экране робота."""
    image = Image.new("1", SCREEN_SIZE, color=0)
    draw = ImageDraw.Draw(image)
    draw.text((8, 10), text, fill=1)
    cli.display_image(image, duration=3.0)


def main() -> int:
    with pycozmo.connect() as cli:
        print("Выражения лица:")
        show_expressions(cli)

        print("Свой текст:")
        # Латиницей — встроенным шрифтом PIL. Для русского см.
        # examples/08_russian_screen.py
        show_custom_text(cli, "PRIVET!")

        cli.clear_screen()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
