"""Физический ввод: кнопка на спине, поглаживание, тапы по кубику.

Экран Козмо НЕ сенсорный — это обычный OLED 128x32, нажатия он не ловит.
Зато «клацать» есть чем:

* **кнопка на спине** — пакет ButtonPressed (нужно железо v1.5 и новее);
* **сенсор поглаживания** — поле backpack_touch_sensor_raw, приходит в
  каждом RobotState; это то, чем Козмо чувствует, что его гладят;
* **кубик** — пакет ObjectTapped, причём он сам считает число тапов,
  так что двойной тап по кубику достаётся бесплатно.

События складываются в очередь, а не вызывают колбэки напрямую: обработчики
pycozmo выполняются в её сетевом потоке, и долгое действие прямо в них
подвесило бы связь с роботом.
"""

import queue
import threading
import time
from typing import Iterator, NamedTuple, Optional

#: Насколько быстро должно прийти второе нажатие, чтобы считаться двойным.
DOUBLE_PRESS_WINDOW = 0.45

#: На сколько сырое значение сенсора должно превысить фон, чтобы это
#: считалось поглаживанием. Значение зависит от экземпляра робота —
#: посмотрите реальные числа в examples/12_buttons.py и подстройте.
PET_THRESHOLD = 20


class Event(NamedTuple):
    """Что произошло: kind — press / double_press / pet / cube_tap."""
    kind: str
    value: object = None


class Buttons:
    """Собирает события физического ввода в очередь.

    Пример:
        with Buttons(cli) as buttons:
            for event in buttons.events(timeout=30.0):
                if event.kind == "double_press":
                    ...
    """

    def __init__(
        self,
        cli,
        double_press_window: float = DOUBLE_PRESS_WINDOW,
        pet_threshold: int = PET_THRESHOLD,
    ) -> None:
        self.cli = cli
        self.double_press_window = double_press_window
        self.pet_threshold = pet_threshold

        self._queue: queue.Queue = queue.Queue()
        self._handlers: list = []
        self._single_timer: Optional[threading.Timer] = None
        self._last_press = 0.0

        # Фон сенсора касания: подстраивается сам по первым измерениям.
        self._touch_baseline: Optional[float] = None
        self._touch_samples = 0
        self._petting = False

        self.last_touch_raw = 0

    # --- подключение и отключение ---

    def __enter__(self) -> "Buttons":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def start(self) -> None:
        import pycozmo.protocol_encoder as pe

        self._handlers = [
            (pe.ButtonPressed, self.cli.add_handler(pe.ButtonPressed, self._on_button)),
            (pe.RobotState, self.cli.add_handler(pe.RobotState, self._on_state)),
            (pe.ObjectTapped, self.cli.add_handler(pe.ObjectTapped, self._on_tap)),
        ]

    def stop(self) -> None:
        for event_type, handler in self._handlers:
            self.cli.del_handler(event_type, handler)
        self._handlers = []
        if self._single_timer is not None:
            self._single_timer.cancel()
            self._single_timer = None

    # --- обработчики пакетов (выполняются в сетевом потоке pycozmo) ---

    def _on_button(self, cli, pkt) -> None:
        del cli
        if not pkt.pressed:          # интересует только нажатие, не отпускание
            return

        now = time.time()
        if now - self._last_press <= self.double_press_window:
            # Второе нажатие успело: отменяем отложенное одиночное.
            if self._single_timer is not None:
                self._single_timer.cancel()
                self._single_timer = None
            self._last_press = 0.0
            self._queue.put(Event("double_press"))
            return

        self._last_press = now
        # Одиночное объявляем не сразу: вдруг сейчас придёт второе.
        self._single_timer = threading.Timer(
            self.double_press_window, lambda: self._queue.put(Event("press"))
        )
        self._single_timer.daemon = True
        self._single_timer.start()

    def _on_state(self, cli, pkt) -> None:
        del cli
        raw = pkt.backpack_touch_sensor_raw
        self.last_touch_raw = raw

        # Первые полсекунды просто смотрим, какой у сенсора покой.
        if self._touch_samples < 15:
            self._touch_samples += 1
            self._touch_baseline = (
                raw if self._touch_baseline is None
                else (self._touch_baseline * 0.8 + raw * 0.2)
            )
            return

        petting = raw > self._touch_baseline + self.pet_threshold
        if petting and not self._petting:
            self._queue.put(Event("pet", raw))
        self._petting = petting

    def _on_tap(self, cli, pkt) -> None:
        del cli
        self._queue.put(Event("cube_tap", pkt.num_taps))

    # --- чтение событий ---

    def get(self, timeout: Optional[float] = None) -> Optional[Event]:
        """Дождаться одного события. None, если вышло время."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def events(self, timeout: Optional[float] = None) -> Iterator[Event]:
        """Идти по событиям, пока они приходят."""
        while True:
            event = self.get(timeout=timeout)
            if event is None:
                return
            yield event
