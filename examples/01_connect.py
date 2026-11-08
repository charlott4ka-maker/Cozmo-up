#!/usr/bin/env python
"""Шаг 1. Проверка связи с роботом.

Запускать, когда компьютер УЖЕ подключён к Wi-Fi сети Cozmo_XXXXXX.
Скрипт подключается, печатает прошивку/серийник/заряд и мигает лампочкой.
"""

import sys
from pathlib import Path

import pycozmo

# Чтобы пример работал из любого каталога.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up import robot_info  # noqa: E402


def main() -> int:
    print("Подключаюсь к Cozmo на 172.31.1.1:5551 ...")
    with pycozmo.connect() as cli:
        print("\n=== Робот на связи ===")
        for key, value in robot_info(cli).items():
            print(f"  {key:20} {value}")

        # Напряжение батареи: ~3.9 В — полная, ниже 3.6 В — пора на базу.
        if cli.battery_voltage < 3.6:
            print("\n  ВНИМАНИЕ: батарея разряжена, поставьте на базу.")

        print("\nМигаю лампочкой на спине...")
        cli.set_all_backpack_lights(pycozmo.lights.green_light)
        cli.wait_for(pycozmo.event.EvtRobotStateUpdated, timeout=2.0)
        cli.set_all_backpack_lights(pycozmo.lights.off_light)

    print("Готово.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
