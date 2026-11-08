"""Мелочи для командной строки.

Главное здесь — python_cmd(). Голое слово `python` на Windows часто
перехватывается заглушкой Microsoft Store («Python was not found»),
а в проекте питон живёт в .venv. Поэтому все подсказки печатаем с тем
интерпретатором, который прямо сейчас выполняет код.
"""

import os
import sys
from pathlib import Path


def python_cmd() -> str:
    """Как вызвать этот же питон из текущей папки."""
    exe = Path(sys.executable)
    try:
        relative = exe.relative_to(Path.cwd())
    except ValueError:
        return str(exe)
    return (f".\\{relative}" if os.name == "nt" else f"./{relative}")


def script_cmd(script: str, *args: str) -> str:
    """Готовая строка команды: интерпретатор, скрипт и аргументы."""
    separator = "\\" if os.name == "nt" else "/"
    script = script.replace("/", separator)
    return " ".join([python_cmd(), script, *args])
