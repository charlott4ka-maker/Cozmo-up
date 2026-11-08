#!/usr/bin/env python
"""Шаг 6. Готовые анимации Cozmo.

Анимации лежат в ассетах, скачанных командой `pycozmo_resources.py download`
(каталог ~/.pycozmo/assets). pycozmo воспроизводит их off-board:
читает .bin-файлы FlatBuffers и шлёт роботу кадры движений, лица и звука.
"""

import time

import pycozmo


def main() -> int:
    with pycozmo.connect() as cli:
        print("Загружаю анимации из ассетов...")
        cli.load_anims()

        names = sorted(cli.get_anim_names())
        print(f"Доступно анимаций: {len(names)}")
        print("Первые 20:")
        for name in names[:20]:
            print(f"  {name}")

        # Хорошая демонстрационная анимация — поиск по подстроке,
        # чтобы не зависеть от конкретного имени в вашей версии ассетов.
        candidates = [n for n in names if "GreetAfterLongTime" in n] or names[:1]
        if not candidates:
            print("Анимации не найдены.")
            return 1

        name = candidates[0]
        print(f"\nИграю: {name}")
        cli.play_anim(name)
        cli.wait_for(pycozmo.event.EvtAnimationCompleted, timeout=20.0)
        time.sleep(0.5)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
