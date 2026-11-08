#!/usr/bin/env python
"""Шаг 3. Экран: эмоции и своя картинка.

pycozmo рисует лицо Cozmo у себя (процедурно) и отправляет
готовое изображение 128x64 на OLED-экран робота.
"""

from PIL import Image, ImageDraw

import pycozmo

SCREEN_SIZE = (pycozmo.procedural_face.DEFAULT_WIDTH,
               pycozmo.procedural_face.DEFAULT_HEIGHT)


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
        # .render() возвращает PIL.Image 128x64, режим "1" (монохром).
        image = expression().render()
        # duration: pycozmo сам подождёт и очистит экран.
        cli.display_image(image, duration=1.5)


def show_custom_text(cli, text: str) -> None:
    """Нарисовать свой текст на экране робота."""
    image = Image.new("1", SCREEN_SIZE, color=0)
    draw = ImageDraw.Draw(image)
    draw.text((8, 24), text, fill=1)
    cli.display_image(image, duration=3.0)


def main() -> int:
    with pycozmo.connect() as cli:
        print("Выражения лица:")
        show_expressions(cli)

        print("Свой текст:")
        show_custom_text(cli, "PRIVET!")

        cli.clear_screen()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
