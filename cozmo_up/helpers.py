"""Небольшие обёртки над pycozmo, чтобы примеры были короче.

pycozmo общается с роботом напрямую по Wi-Fi (UDP на 172.31.1.1:5551)
и заменяет собой мобильное приложение Cozmo.
"""

from contextlib import contextmanager
from typing import Iterator

import pycozmo

# Адрес, на котором Cozmo слушает, когда он сам раздаёт Wi-Fi.
ROBOT_ADDR = pycozmo.conn.ROBOT_ADDR


@contextmanager
def connect(**kwargs) -> Iterator["pycozmo.client.Client"]:
    """Подключиться к Cozmo и гарантированно отключиться на выходе.

    Пример:
        with connect() as cli:
            cli.drive_wheels(50.0, 50.0, duration=1.0)
    """
    with pycozmo.connect(**kwargs) as cli:
        yield cli


def robot_info(cli: "pycozmo.client.Client") -> dict:
    """Собрать то, что робот сообщил о себе после подключения."""
    return {
        "firmware_version": cli.robot_fw_sig["version"] if cli.robot_fw_sig else None,
        "serial_number": cli.serial_number,
        "serial_number_head": cli.serial_number_head,
        "body_hw_version": cli.body_hw_version,
        "body_color": cli.body_color,
        "battery_voltage": round(cli.battery_voltage, 2),
        "head_angle_deg": round(cli.head_angle.degrees, 1),
        "lift_height_mm": round(cli.lift_position.height.mm, 1),
    }
