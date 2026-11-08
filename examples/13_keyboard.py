#!/usr/bin/env python
"""Шаг 13. Руление с клавиатуры.

Стрелки или WASD — ехать, пробел — стоп. Робот едет, пока клавиша
нажата, и останавливается сам, если её отпустили.

Поставьте Козмо на ровный стол (не на базу).

  стрелки / WASD   ехать
  пробел           стоп
  r / f            ковш вверх / вниз
  t / g            голова вверх / вниз
  1..5             рожицы
  p                сфотографировать в out/
  q                выход
"""

import sys
import time
from pathlib import Path

import pycozmo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.keys import DOWN, LEFT, RIGHT, UP, KeyReader  # noqa: E402
from cozmo_up.screen import render_text, to_screen  # noqa: E402

SPEED = 80.0
TURN = 60.0

#: Сколько робот едет после нажатия, если новых нажатий нет.
COAST = 0.35

FACES = {
    "1": "Happiness", "2": "Surprise", "3": "Anger",
    "4": "Sadness", "5": "Excitement",
}

MOVES = {
    UP: (SPEED, SPEED), "w": (SPEED, SPEED),
    DOWN: (-SPEED, -SPEED), "s": (-SPEED, -SPEED),
    LEFT: (-TURN, TURN), "a": (-TURN, TURN),
    RIGHT: (TURN, -TURN), "d": (TURN, -TURN),
}


def main() -> int:
    print(__doc__)
    saved = 0
    last_image = {"img": None}

    def on_image(cli, image):
        del cli
        last_image["img"] = image

    with pycozmo.connect() as cli:
        cli.add_handler(pycozmo.event.EvtNewRawCameraImage, on_image)
        cli.set_head_angle(0.0)
        cli.enable_camera(enable=True, color=False)
        cli.display_image(render_text("рули!"))
        time.sleep(0.5)

        moving_until = 0.0

        with KeyReader() as keys:
            while True:
                key = keys.get(timeout=0.05)
                now = time.time()

                if key in MOVES:
                    left, right = MOVES[key]
                    cli.drive_wheels(left, right)
                    moving_until = now + COAST
                    continue

                if key == " " or key == "esc":
                    cli.stop_all_motors()
                    moving_until = 0.0
                elif key == "q":
                    break
                elif key == "r":
                    cli.set_lift_height(pycozmo.robot.MAX_LIFT_HEIGHT.mm)
                elif key == "f":
                    cli.set_lift_height(pycozmo.robot.MIN_LIFT_HEIGHT.mm)
                elif key == "t":
                    cli.set_head_angle(pycozmo.robot.MAX_HEAD_ANGLE.radians)
                elif key == "g":
                    cli.set_head_angle(pycozmo.robot.MIN_HEAD_ANGLE.radians)
                elif key in FACES:
                    face = getattr(pycozmo.expressions, FACES[key])
                    cli.display_image(to_screen(face().render()))
                elif key == "p":
                    image = last_image["img"]
                    if image is None:
                        print("  кадра ещё нет, подождите секунду")
                    else:
                        Path("out").mkdir(exist_ok=True)
                        path = Path("out") / f"snap_{saved:03d}.png"
                        image.save(path)
                        saved += 1
                        print(f"  снято: {path}")

                # Клавишу отпустили — сами тормозим.
                if moving_until and now > moving_until:
                    cli.stop_all_motors()
                    moving_until = 0.0

        cli.stop_all_motors()
        cli.enable_camera(enable=False)
        cli.clear_screen()

    print(f"\nГотово. Снимков сделано: {saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
