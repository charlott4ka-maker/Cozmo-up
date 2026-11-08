#!/usr/bin/env python
"""Шаг 15. Автономная езда: катается сам и не падает со стола.

Едет вперёд, на краю стола отруливает назад и поворачивает в случайную
сторону. Если его подняли — останавливается и ждёт, пока поставят.

Поставьте на ровный стол. Первые разы постойте рядом: датчик обрыва
срабатывает не мгновенно, и у самого края лучше подстраховать рукой.
"""

import random
import sys
import time
from pathlib import Path

import pycozmo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.screen import to_screen  # noqa: E402
from cozmo_up.speech import Voice  # noqa: E402

RUN_SECONDS = 120.0
SPEED = 45.0            # медленно: быстрее — и он не успевает затормозить у края
TURN = 55.0

state = {"cliff": False, "picked_up": False}


def on_cliff(cli, detected):
    del cli
    state["cliff"] = detected


def on_picked_up(cli, picked_up):
    del cli
    state["picked_up"] = picked_up


def main() -> int:
    voice = Voice()

    def say(cli, key):
        if voice.has(key):
            voice.say(cli, key)

    with pycozmo.connect() as cli:
        cli.add_handler(pycozmo.event.EvtCliffDetectedChange, on_cliff)
        cli.add_handler(pycozmo.event.EvtRobotPickedUpChange, on_picked_up)

        cli.set_volume(45000)
        cli.set_head_angle(0.0)
        time.sleep(1.0)

        say(cli, "poehali")
        print(f"Катаюсь {RUN_SECONDS:.0f} секунд. Ctrl+C — прервать.\n")

        deadline = time.time() + RUN_SECONDS
        driving = False
        was_held = False

        while time.time() < deadline:
            if state["picked_up"]:
                if driving:
                    cli.stop_all_motors()
                    driving = False
                if not was_held:
                    print("  подняли — жду")
                    cli.display_image(to_screen(pycozmo.expressions.Fear().render()))
                    cli.set_all_backpack_lights(pycozmo.lights.red_light)
                    say(cli, "podnyali")
                    was_held = True
                time.sleep(0.2)
                continue

            if was_held:
                print("  поставили — поехали дальше")
                say(cli, "opustili")
                was_held = False

            if state["cliff"]:
                print("  край стола — отруливаю")
                cli.stop_all_motors()
                driving = False
                cli.display_image(to_screen(pycozmo.expressions.Surprise().render()))
                cli.set_all_backpack_lights(pycozmo.lights.red_light)
                say(cli, "obryv")

                cli.drive_wheels(-SPEED, -SPEED, duration=1.0)      # назад
                turn = random.choice([-1, 1])                        # куда свернуть
                cli.drive_wheels(TURN * turn, -TURN * turn,
                                 duration=random.uniform(0.6, 1.4))
                cli.stop_all_motors()
                continue

            if not driving:
                cli.set_all_backpack_lights(pycozmo.lights.green_light)
                cli.display_image(to_screen(pycozmo.expressions.Happiness().render()))
                cli.drive_wheels(SPEED, SPEED)
                driving = True

            time.sleep(0.1)

        cli.stop_all_motors()
        say(cli, "poka")
        cli.set_backpack_lights_off()
        cli.clear_screen()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
