#!/usr/bin/env python
"""Шаг 12. Кнопка на спине, поглаживание и кубик.

Экран Козмо НЕ сенсорный — нажатия он не ловит. Зато есть:

  * кнопка на спине (железо v1.5 и новее);
  * сенсор поглаживания под ней — то, чем он чувствует, что его гладят;
  * кубик, который сам считает тапы, так что двойной тап есть из коробки.

Что делает этот пример:
  одно нажатие   -> здоровается
  двойное        -> танцует
  поглаживание   -> довольная рожица
  тап по кубику  -> реагирует на число тапов
  три нажатия подряд -> выход

Внизу всё время печатается сырое значение сенсора касания — по нему
подбирается порог, если поглаживание срабатывает слишком легко или никак.
"""

import sys
import time
from pathlib import Path

import pycozmo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.brain import Brain  # noqa: E402
from cozmo_up.buttons import Buttons  # noqa: E402
from cozmo_up.screen import render_text, to_screen  # noqa: E402
from cozmo_up.speech import Voice  # noqa: E402

RUN_SECONDS = 120.0


def main() -> int:
    voice = Voice()
    brain = Brain(voice)

    with pycozmo.connect() as cli:
        cli.set_volume(50000)
        cli.set_head_angle(0.0)
        time.sleep(0.5)

        cli.display_image(render_text("жми кнопку\nна спине"))
        print("Жму-жму! Три нажатия подряд — выход.")
        print("(если кнопки нет — у вас железо до v1.5, пробуйте гладить и кубик)\n")

        presses_in_a_row = 0
        deadline = time.time() + RUN_SECONDS

        with Buttons(cli) as buttons:
            while time.time() < deadline:
                event = buttons.get(timeout=2.0)

                if event is None:
                    # Ничего не нажали — показываем, что чувствует сенсор.
                    print(f"\r  сенсор касания: {buttons.last_touch_raw:5}", end="")
                    presses_in_a_row = 0
                    continue

                print(f"\r  событие: {event.kind} {event.value or ''}")

                if event.kind == "press":
                    presses_in_a_row += 1
                    if presses_in_a_row >= 3:
                        break
                    cli.display_image(to_screen(pycozmo.expressions.Happiness().render()))
                    if voice.has("privet2"):
                        voice.say(cli, "privet2")

                elif event.kind == "double_press":
                    presses_in_a_row = 0
                    cli.display_image(to_screen(pycozmo.expressions.Excitement().render()))
                    if voice.has("tancuyu"):
                        voice.say(cli, "tancuyu")
                    brain.do(cli, "dance")

                elif event.kind == "pet":
                    presses_in_a_row = 0
                    cli.display_image(to_screen(pycozmo.expressions.Happiness().render()))
                    cli.set_all_backpack_lights(pycozmo.lights.green_light)
                    if voice.has("lyublyu_tebya"):
                        voice.say(cli, "lyublyu_tebya")
                    cli.set_backpack_lights_off()

                elif event.kind == "cube_tap":
                    presses_in_a_row = 0
                    taps = event.value or 1
                    cli.display_image(render_text(f"тапов: {taps}"))
                    key = "ura" if taps >= 2 else "da"
                    if voice.has(key):
                        voice.say(cli, key)

        if voice.has("poka"):
            voice.say_and_show(cli, "poka")
        time.sleep(0.5)
        cli.set_backpack_lights_off()
        cli.clear_screen()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
