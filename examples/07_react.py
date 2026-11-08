#!/usr/bin/env python
"""Шаг 7. Своя логика: робот реагирует на события.

Пример показывает главный приём: подписка на события датчиков
и реакция на них. Отсюда и начинается «перепрограммирование» —
вы пишете своё поведение вместо родного приложения.

Сценарий: Cozmo едет вперёд, но останавливается у обрыва (края стола),
а если его подняли — закрывает глаза от испуга.
"""

import sys
import time
from pathlib import Path

import pycozmo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.screen import to_screen  # noqa: E402

state = {"cliff": False, "picked_up": False}


def on_cliff(cli, detected: bool) -> None:
    """Сработал датчик обрыва под роботом."""
    del cli
    state["cliff"] = detected
    print(f"  обрыв: {detected}")


def on_picked_up(cli, picked_up: bool) -> None:
    """Робота подняли со стола."""
    del cli
    state["picked_up"] = picked_up
    print(f"  подняли: {picked_up}")


def main() -> int:
    with pycozmo.connect() as cli:
        cli.add_handler(pycozmo.event.EvtCliffDetectedChange, on_cliff)
        cli.add_handler(pycozmo.event.EvtRobotPickedUpChange, on_picked_up)

        cli.set_head_angle(0.0)
        time.sleep(1.0)

        print("Еду вперёд 15 секунд. Поднесите к краю стола или поднимите робота.")
        deadline = time.time() + 15.0
        driving = False

        while time.time() < deadline:
            if state["picked_up"]:
                if driving:
                    cli.stop_all_motors()
                    driving = False
                cli.display_image(to_screen(pycozmo.expressions.Fear().render()))
                cli.set_all_backpack_lights(pycozmo.lights.red_light)

            elif state["cliff"]:
                if driving:
                    cli.stop_all_motors()
                    driving = False
                cli.display_image(to_screen(pycozmo.expressions.Surprise().render()))
                cli.set_all_backpack_lights(pycozmo.lights.red_light)
                # Отъехать назад от края.
                cli.drive_wheels(-40.0, -40.0, duration=0.8)

            else:
                if not driving:
                    cli.drive_wheels(40.0, 40.0)
                    driving = True
                cli.display_image(to_screen(pycozmo.expressions.Happiness().render()))
                cli.set_all_backpack_lights(pycozmo.lights.green_light)

            time.sleep(0.2)

        cli.stop_all_motors()
        cli.set_backpack_lights_off()
        cli.clear_screen()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
