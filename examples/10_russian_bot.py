#!/usr/bin/env python
"""Шаг 10. Русскоязычный Козмо целиком.

Собирает всё вместе: робот ездит, говорит по-русски, пишет на экране
русский текст и реагирует на датчики.

ПЕРЕД ЗАПУСКОМ, при интернете:
    python scripts/make_voice.py

Поставьте робота на ровный стол (не на базу).
"""

import sys
import time
from pathlib import Path

import pycozmo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.screen import render_text, to_screen  # noqa: E402
from cozmo_up.speech import Voice  # noqa: E402

RUN_SECONDS = 30.0

state = {"cliff": False, "picked_up": False}


def on_cliff(cli, detected: bool) -> None:
    del cli
    state["cliff"] = detected


def on_picked_up(cli, picked_up: bool) -> None:
    del cli
    state["picked_up"] = picked_up


def main() -> int:
    voice = Voice()
    if not voice.keys():
        print("Нет озвученных фраз. Выполните: python scripts/make_voice.py")
        return 1

    with pycozmo.connect() as cli:
        cli.add_handler(pycozmo.event.EvtCliffDetectedChange, on_cliff)
        cli.add_handler(pycozmo.event.EvtRobotPickedUpChange, on_picked_up)

        cli.set_volume(50000)
        cli.set_head_angle(0.0)
        time.sleep(1.0)

        voice.say_and_show(cli, "privet")
        time.sleep(0.5)
        voice.say_and_show(cli, "poehali")

        print(f"Катаюсь {RUN_SECONDS:.0f} секунд. "
              "Поднесите к краю стола или поднимите робота.")

        deadline = time.time() + RUN_SECONDS
        driving = False
        last_mode = None

        while time.time() < deadline:
            if state["picked_up"]:
                mode = "picked_up"
            elif state["cliff"]:
                mode = "cliff"
            else:
                mode = "drive"

            # Говорим только при СМЕНЕ состояния, иначе будет каша.
            if mode != last_mode:
                if mode == "picked_up":
                    if driving:
                        cli.stop_all_motors()
                        driving = False
                    cli.set_all_backpack_lights(pycozmo.lights.red_light)
                    cli.display_image(to_screen(pycozmo.expressions.Fear().render()))
                    voice.say(cli, "podnyali")
                    cli.display_image(render_text(voice.text("podnyali") or ""))

                elif mode == "cliff":
                    if driving:
                        cli.stop_all_motors()
                        driving = False
                    cli.set_all_backpack_lights(pycozmo.lights.red_light)
                    cli.display_image(to_screen(pycozmo.expressions.Surprise().render()))
                    voice.say(cli, "obryv")
                    cli.drive_wheels(-40.0, -40.0, duration=0.8)

                else:
                    cli.set_all_backpack_lights(pycozmo.lights.green_light)
                    cli.display_image(to_screen(pycozmo.expressions.Happiness().render()))

                last_mode = mode

            if mode == "drive" and not driving:
                cli.drive_wheels(40.0, 40.0)
                driving = True

            time.sleep(0.2)

        cli.stop_all_motors()
        voice.say_and_show(cli, "poka")
        time.sleep(0.5)
        cli.set_backpack_lights_off()
        cli.clear_screen()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
