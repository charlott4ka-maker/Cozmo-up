"""Чтение клавиш без Enter — для руления роботом с клавиатуры.

Работает и на Windows (msvcrt), и на macOS/Linux (termios). Стрелки
приходят как "up" / "down" / "left" / "right", обычные клавиши — как
один символ в нижнем регистре.
"""

import sys
from typing import Optional

IS_WINDOWS = sys.platform == "win32"

#: Как называются стрелки, чтобы код примеров не зависел от платформы.
UP, DOWN, LEFT, RIGHT = "up", "down", "left", "right"


class KeyReader:
    """Читает нажатия клавиш по одной, не дожидаясь Enter.

    Пример:
        with KeyReader() as keys:
            while True:
                key = keys.get(timeout=0.1)
                if key == "q":
                    break
    """

    def __init__(self) -> None:
        self._fd = None
        self._saved = None

    def __enter__(self) -> "KeyReader":
        if not IS_WINDOWS:
            import termios
            import tty

            self._fd = sys.stdin.fileno()
            self._saved = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        return self

    def __exit__(self, *exc) -> None:
        if not IS_WINDOWS and self._saved is not None:
            import termios

            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved)
            self._saved = None

    def get(self, timeout: float = 0.1) -> Optional[str]:
        """Вернуть нажатую клавишу или None, если за timeout ничего не нажали."""
        if IS_WINDOWS:
            return self._get_windows(timeout)
        return self._get_posix(timeout)

    # --- Windows ---

    def _get_windows(self, timeout: float) -> Optional[str]:
        import msvcrt
        import time

        deadline = time.time() + timeout
        while time.time() < deadline:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                # Стрелки приходят двумя байтами: префикс 0x00 или 0xE0.
                if ch in (b"\x00", b"\xe0"):
                    code = msvcrt.getch()
                    return {
                        b"H": UP, b"P": DOWN, b"K": LEFT, b"M": RIGHT,
                    }.get(code)
                try:
                    return ch.decode("utf-8", "ignore").lower() or None
                except Exception:  # noqa: BLE001
                    return None
            time.sleep(0.01)
        return None

    # --- macOS / Linux ---

    def _get_posix(self, timeout: float) -> Optional[str]:
        # Читаем через os.read по дескриптору, а НЕ через sys.stdin.read():
        # sys.stdin буферизован, и select() не видит уже вычитанные в буфер
        # байты — escape-последовательность стрелки при этом разъезжается
        # и вместо "up" приходит "esc", потом "[", потом "a".
        import os
        import select

        fd = self._fd if self._fd is not None else sys.stdin.fileno()

        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            return None

        ch = os.read(fd, 1)
        if ch != b"\x1b":                     # не escape — обычная клавиша
            return ch.decode("utf-8", "ignore").lower() or None

        # Стрелка: ESC [ A/B/C/D
        ready, _, _ = select.select([fd], [], [], 0.05)
        if not ready:
            return "esc"
        rest = os.read(fd, 2).decode("utf-8", "ignore")
        return {
            "[A": UP, "[B": DOWN, "[C": RIGHT, "[D": LEFT,
        }.get(rest)
