#!/usr/bin/env python
"""Шаг 2. Движение: колёса, голова, ковш.

Поставьте Cozmo на ровный стол (НЕ на базу) и уберите препятствия.
"""

import time

import pycozmo


def main() -> int:
    with pycozmo.connect() as cli:
        # Колёса: скорость в мм/с для каждого, макс. ~ 200 мм/с.
        print("Вперёд")
        cli.drive_wheels(lwheel_speed=50.0, rwheel_speed=50.0, duration=1.5)

        print("Поворот на месте")
        cli.drive_wheels(lwheel_speed=50.0, rwheel_speed=-50.0, duration=1.0)

        print("Назад")
        cli.drive_wheels(lwheel_speed=-50.0, rwheel_speed=-50.0, duration=1.5)

        cli.stop_all_motors()

        # Голова: угол в радианах, диапазон от -25° до +44.5°.
        print("Голова вверх / вниз")
        cli.set_head_angle(pycozmo.robot.MAX_HEAD_ANGLE.radians)
        time.sleep(1.5)
        cli.set_head_angle(pycozmo.robot.MIN_HEAD_ANGLE.radians)
        time.sleep(1.5)

        # Ковш: высота в мм, от 32 до 92.
        print("Ковш вверх / вниз")
        cli.set_lift_height(pycozmo.robot.MAX_LIFT_HEIGHT.mm)
        time.sleep(1.5)
        cli.set_lift_height(pycozmo.robot.MIN_LIFT_HEIGHT.mm)
        time.sleep(1.5)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
