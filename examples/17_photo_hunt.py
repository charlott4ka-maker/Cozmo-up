#!/usr/bin/env python
"""Шаг 17. Фотоохота: катается и снимает.

Едет по столу, не падая с края, и по дороге делает снимки: по таймеру и
каждый раз, когда видит маркер. Все кадры складываются в out/hunt/,
рядом пишется отчёт hunt.txt.

Поставьте на ровный стол.
"""

import random
import sys
import time
from datetime import datetime
from pathlib import Path

import pycozmo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.screen import render_text  # noqa: E402
from cozmo_up.vision import MarkerDetector  # noqa: E402

RUN_SECONDS = 90.0
SHOT_EVERY = 4.0          # снимок по таймеру, секунд
SPEED, TURN = 45.0, 55.0
OUT = Path("out/hunt")

state = {"cliff": False, "picked_up": False}


def on_cliff(cli, detected):
    del cli
    state["cliff"] = detected


def on_picked_up(cli, picked_up):
    del cli
    state["picked_up"] = picked_up


def main() -> int:
    latest = {"image": None}

    def on_image(cli, image):
        del cli
        latest["image"] = image

    detector = MarkerDetector()
    OUT.mkdir(parents=True, exist_ok=True)
    report = []
    shots = 0

    def shoot(reason: str) -> None:
        nonlocal shots
        image = latest["image"]
        if image is None:
            return
        stamp = datetime.now().strftime("%H%M%S")
        path = OUT / f"{shots:03d}_{reason}_{stamp}.png"
        image.save(path)
        report.append(f"{stamp}  {reason:12} {path.name}")
        print(f"  снято [{reason}] {path.name}")
        shots += 1

    with pycozmo.connect() as cli:
        cli.add_handler(pycozmo.event.EvtNewRawCameraImage, on_image)
        cli.add_handler(pycozmo.event.EvtCliffDetectedChange, on_cliff)
        cli.add_handler(pycozmo.event.EvtRobotPickedUpChange, on_picked_up)

        cli.set_head_angle(0.0)
        time.sleep(0.5)
        cli.enable_camera(enable=True, color=False)

        waited = time.time() + 15.0
        while latest["image"] is None and time.time() < waited:
            time.sleep(0.1)
        if latest["image"] is None:
            print("Кадры не идут.")
            return 1

        print(f"Охота началась, {RUN_SECONDS:.0f} секунд.\n")
        cli.display_image(render_text("фотоохота"))

        deadline = time.time() + RUN_SECONDS
        next_shot = time.time() + SHOT_EVERY
        seen_markers = set()
        driving = False

        while time.time() < deadline:
            now = time.time()

            if state["picked_up"]:
                if driving:
                    cli.stop_all_motors()
                    driving = False
                time.sleep(0.2)
                continue

            if state["cliff"]:
                cli.stop_all_motors()
                driving = False
                shoot("obryv")
                cli.drive_wheels(-SPEED, -SPEED, duration=1.0)
                turn = random.choice([-1, 1])
                cli.drive_wheels(TURN * turn, -TURN * turn,
                                 duration=random.uniform(0.6, 1.4))
                cli.stop_all_motors()
                continue

            # Увидел маркер, которого ещё не снимал — щёлкаем.
            marker = detector.nearest(latest["image"])
            if marker is not None and marker.id not in seen_markers:
                cli.stop_all_motors()
                driving = False
                seen_markers.add(marker.id)
                cli.display_image(render_text(f"маркер {marker.id}"))
                shoot(f"marker{marker.id}")
                time.sleep(0.4)

            if now >= next_shot:
                shoot("taimer")
                next_shot = now + SHOT_EVERY

            if not driving:
                cli.drive_wheels(SPEED, SPEED)
                driving = True

            time.sleep(0.1)

        cli.stop_all_motors()
        cli.enable_camera(enable=False)
        cli.clear_screen()

    path = OUT / "hunt.txt"
    path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\nСнимков: {shots}, маркеров найдено: {len(seen_markers)}")
    print(f"Всё в {OUT}/, отчёт {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
