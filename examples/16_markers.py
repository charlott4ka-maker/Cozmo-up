#!/usr/bin/env python
"""Шаг 16. Козмо видит маркер и едет к нему.

Сначала напечатайте маркеры:
    python scripts/make_markers.py
Файл markers/markers.png — распечатать, вырезать (белое поле вокруг
обязательно!) и поставить перед роботом.

Про кубики честно: родные символы на гранях кубиков Anki pycozmo
распознавать не умеет — этого в библиотеке нет. ArUco-маркеры на бумаге
делают ровно то же самое и работают надёжно.

Что делает: крутится на месте, пока не увидит маркер, потом
подруливает на него и едет вперёд, пока маркер не станет крупным —
значит, подъехали.
"""

import sys
import time
from pathlib import Path

import pycozmo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.screen import render_text, to_screen  # noqa: E402
from cozmo_up.speech import Voice  # noqa: E402
from cozmo_up.vision import MarkerDetector  # noqa: E402

#: Насколько маркер должен быть по центру, чтобы ехать прямо.
CENTERED = 0.15
#: При каком размере маркера в пикселях считаем, что подъехали.
CLOSE_ENOUGH = 110
SEARCH_TURN = 45.0
DRIVE = 50.0
RUN_SECONDS = 90.0


def main() -> int:
    latest = {"image": None}

    def on_image(cli, image):
        del cli
        latest["image"] = image

    detector = MarkerDetector()
    voice = Voice()

    with pycozmo.connect() as cli:
        cli.add_handler(pycozmo.event.EvtNewRawCameraImage, on_image)
        cli.set_volume(45000)
        cli.set_head_angle(0.0)
        time.sleep(0.5)
        cli.enable_camera(enable=True, color=False)

        print("Жду кадры...")
        waited = time.time() + 15.0
        while latest["image"] is None and time.time() < waited:
            time.sleep(0.1)
        if latest["image"] is None:
            print("Кадры не идут.")
            return 1

        print("Ищу маркер. Покажите ему распечатку.\n")
        deadline = time.time() + RUN_SECONDS
        arrived = False
        last_seen = None

        while time.time() < deadline and not arrived:
            marker = detector.nearest(latest["image"])

            if marker is None:
                if last_seen is not None:
                    print("  потерял, ищу снова")
                    last_seen = None
                    cli.display_image(render_text("ищу..."))
                # Крутимся на месте короткими рывками, чтобы успевать смотреть.
                cli.drive_wheels(SEARCH_TURN, -SEARCH_TURN, duration=0.25)
                time.sleep(0.15)
                continue

            if marker.id != last_seen:
                print(f"  вижу маркер id={marker.id}")
                cli.display_image(render_text(f"маркер {marker.id}"))
                last_seen = marker.id

            if marker.size >= CLOSE_ENOUGH:
                cli.stop_all_motors()
                arrived = True
                break

            if abs(marker.offset) > CENTERED:
                # Подруливаем: знак offset говорит, в какую сторону ушла цель.
                turn = SEARCH_TURN * (1 if marker.offset > 0 else -1)
                cli.drive_wheels(turn, -turn, duration=0.18)
            else:
                cli.drive_wheels(DRIVE, DRIVE, duration=0.3)

            time.sleep(0.05)

        cli.stop_all_motors()

        if arrived:
            print(f"\nПриехал к маркеру id={last_seen}!")
            cli.display_image(to_screen(pycozmo.expressions.Excitement().render()))
            if voice.has("ura"):
                voice.say(cli, "ura")
        else:
            print("\nМаркер так и не нашёлся.")
            if voice.has("ne_ponyal"):
                voice.say(cli, "ne_ponyal")

        time.sleep(0.5)
        cli.enable_camera(enable=False)
        cli.clear_screen()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
