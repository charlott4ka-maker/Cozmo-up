#!/usr/bin/env python
"""Шаг 4. Камера: получить кадры с робота и сохранить в out/.

Кадры приходят асинхронно, поэтому подписываемся на событие
EvtNewRawCameraImage и складываем изображения в файлы.
"""

import os
import time

import pycozmo

OUT_DIR = "out"
FRAMES_TO_SAVE = 5

saved = 0


def on_camera_image(cli, image) -> None:
    """Обработчик нового кадра. image — это PIL.Image."""
    global saved
    del cli
    if saved >= FRAMES_TO_SAVE:
        return
    path = os.path.join(OUT_DIR, f"frame_{saved:03d}.png")
    image.save(path)
    print(f"  сохранён {path}  ({image.size[0]}x{image.size[1]}, {image.mode})")
    saved += 1


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)

    with pycozmo.connect() as cli:
        cli.add_handler(pycozmo.event.EvtNewRawCameraImage, on_camera_image)

        # Поднять голову, чтобы камера смотрела вперёд, а не в стол.
        cli.set_head_angle(0.0)
        time.sleep(1.0)

        # color=True — цветные кадры (нужна прошивка с поддержкой цвета).
        cli.enable_camera(enable=True, color=False)

        print(f"Жду {FRAMES_TO_SAVE} кадров...")
        timeout = time.time() + 20.0
        while saved < FRAMES_TO_SAVE and time.time() < timeout:
            time.sleep(0.2)

        cli.enable_camera(enable=False)

    if saved == 0:
        print("Кадры не пришли. Проверьте прошивку и Wi-Fi-соединение.")
        return 1

    print(f"Готово: {saved} кадр(ов) в {OUT_DIR}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
