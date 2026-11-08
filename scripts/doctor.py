#!/usr/bin/env python
"""Проверка готовности к работе с Cozmo.

Запускать ПОСЛЕ подключения компьютера к Wi-Fi сети робота:

    python scripts/doctor.py

Проверяет версию Python, установку pycozmo, наличие ассетов
и то, что компьютер действительно в сети робота.
"""

import os
import socket
import sys
from pathlib import Path

ROBOT_IP = "172.31.1.1"
ROBOT_PORT = 5551
ROBOT_SUBNET = "172.31.1."

OK = "[ OK ]"
FAIL = "[FAIL]"
WARN = "[WARN]"


def check_python() -> bool:
    major, minor = sys.version_info[:2]
    version = f"{major}.{minor}.{sys.version_info[2]}"
    if major == 3 and 10 <= minor <= 12:
        print(f"{OK}  Python {version}")
        return True
    if major == 3 and minor >= 13:
        print(f"{FAIL} Python {version} — слишком новый.")
        print("       pycozmo 0.8.0 не работает на 3.13+ (удалён модуль 'chunk').")
        print("       Поставьте Python 3.12 и пересоздайте .venv.")
        return False
    print(f"{FAIL} Python {version} — слишком старый, нужен 3.10+.")
    return False


def check_pycozmo() -> bool:
    try:
        import pycozmo
    except ImportError:
        print(f"{FAIL} pycozmo не установлен. Выполните: bash scripts/setup.sh")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"{FAIL} pycozmo не импортируется: {exc}")
        return False
    print(f"{OK}  pycozmo {pycozmo.__version__}")
    return True


def check_assets() -> bool:
    assets = Path.home() / ".pycozmo" / "assets"
    if not assets.is_dir() or not any(assets.iterdir()):
        print(f"{WARN} Ассеты не скачаны ({assets}).")
        print("       Анимации и звуки не будут работать.")
        print("       Подключитесь к интернету и выполните: pycozmo_resources.py download")
        return False
    count = sum(1 for _ in assets.rglob("*") if _.is_file())
    print(f"{OK}  Ассеты на месте: {assets} ({count} файлов)")
    return True


def check_network() -> bool:
    """Определить, в сети ли робота, по локальному адресу маршрута к нему."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # UDP connect не шлёт пакетов, но заставляет ОС выбрать маршрут.
        sock.connect((ROBOT_IP, ROBOT_PORT))
        local_ip = sock.getsockname()[0]
    except OSError as exc:
        print(f"{FAIL} Нет маршрута к {ROBOT_IP}: {exc}")
        print("       Подключите компьютер к Wi-Fi сети Cozmo_XXXXXX.")
        return False
    finally:
        sock.close()

    if local_ip.startswith(ROBOT_SUBNET):
        print(f"{OK}  Компьютер в сети робота (локальный адрес {local_ip})")
        return True

    print(f"{FAIL} Компьютер НЕ в сети робота (локальный адрес {local_ip}).")
    print(f"       Ожидался адрес вида {ROBOT_SUBNET}x.")
    print("       Подключитесь к Wi-Fi сети Cozmo_XXXXXX паролем с экрана робота")
    print("       (поднимите и опустите ковш, чтобы его увидеть).")
    return False


def check_vpn() -> None:
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        if os.environ.get(var) or os.environ.get(var.lower()):
            print(f"{WARN} Задана переменная {var} — прокси может мешать связи с роботом.")


def main() -> int:
    print("Проверка окружения для Cozmo\n")

    results = [
        check_python(),
        check_pycozmo(),
    ]
    check_assets()  # не блокирует подключение
    results.append(check_network())
    check_vpn()

    print()
    if all(results):
        print("Всё готово. Запускайте: python examples/01_connect.py")
        return 0

    print("Есть проблемы — см. сообщения выше.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
