#!/usr/bin/env python
"""Шаг 14. Живое видео с камеры в окне на компьютере.

В окне показывается то, что видит Козмо, и там же можно им рулить.
Найденные ArUco-маркеры обводятся прямо в кадре.

  стрелки / WASD   ехать
  пробел           стоп
  t / g            голова вверх / вниз
  p                сохранить кадр в out/
  m                обводить маркеры вкл/выкл
  q или Esc        выход

Клавиши ловит ОКНО OpenCV — оно должно быть активно, не терминал.
"""

import sys
import time
from pathlib import Path

import pycozmo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.vision import MarkerDetector, to_cv  # noqa: E402

SPEED, TURN = 80.0, 60.0
WINDOW = "Cozmo"
ZOOM = 2                      # камера 320x240 — мелковато, увеличиваем


def main() -> int:
    import cv2

    latest = {"image": None}

    def on_image(cli, image):
        del cli
        latest["image"] = image

    detector = MarkerDetector()
    show_markers = True
    saved = 0

    print(__doc__)

    with pycozmo.connect() as cli:
        cli.add_handler(pycozmo.event.EvtNewRawCameraImage, on_image)
        cli.set_head_angle(0.0)
        time.sleep(0.5)
        cli.enable_camera(enable=True, color=False)

        print("Жду первый кадр...")
        waited = time.time() + 15.0
        while latest["image"] is None and time.time() < waited:
            time.sleep(0.1)
        if latest["image"] is None:
            print("Кадры не идут. Проверьте связь и прошивку.")
            return 1

        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        moving_until = 0.0

        while True:
            image = latest["image"]
            frame = detector.draw(image) if show_markers else to_cv(image)

            if show_markers:
                for marker in detector.find(image):
                    cv2.putText(frame, f"id {marker.id}",
                                (int(marker.cx) - 20, int(marker.cy) - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            big = cv2.resize(frame, None, fx=ZOOM, fy=ZOOM,
                             interpolation=cv2.INTER_NEAREST)
            cv2.imshow(WINDOW, big)

            key = cv2.waitKey(30) & 0xFF
            now = time.time()

            # Стрелки в OpenCV приходят своими кодами, WASD надёжнее.
            if key in (ord("w"), 82):
                cli.drive_wheels(SPEED, SPEED); moving_until = now + 0.35
            elif key in (ord("s"), 84):
                cli.drive_wheels(-SPEED, -SPEED); moving_until = now + 0.35
            elif key in (ord("a"), 81):
                cli.drive_wheels(-TURN, TURN); moving_until = now + 0.35
            elif key in (ord("d"), 83):
                cli.drive_wheels(TURN, -TURN); moving_until = now + 0.35
            elif key == ord(" "):
                cli.stop_all_motors(); moving_until = 0.0
            elif key == ord("t"):
                cli.set_head_angle(pycozmo.robot.MAX_HEAD_ANGLE.radians)
            elif key == ord("g"):
                cli.set_head_angle(pycozmo.robot.MIN_HEAD_ANGLE.radians)
            elif key == ord("m"):
                show_markers = not show_markers
            elif key == ord("p"):
                Path("out").mkdir(exist_ok=True)
                path = Path("out") / f"frame_{saved:03d}.png"
                image.save(path)
                saved += 1
                print(f"  снято: {path}")
            elif key in (ord("q"), 27):
                break

            if moving_until and now > moving_until:
                cli.stop_all_motors(); moving_until = 0.0

        cv2.destroyAllWindows()
        cli.stop_all_motors()
        cli.enable_camera(enable=False)

    print(f"\nГотово. Снимков: {saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
