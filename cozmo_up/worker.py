"""Фоновый поток, который держит связь с роботом.

Зачем отдельный поток. Tkinter можно трогать только из главного потока,
а pycozmo вызывает свои обработчики из собственного сетевого потока.
Если перемешать, интерфейс начнёт зависать и падать в случайных местах.

Поэтому: приложение кладёт команды в очередь, поток их выполняет и
складывает события обратно в другую очередь. Интерфейс её опрашивает
таймером и только рисует.

Ещё одна причина: робот рвёт связь, если 5 секунд ничего не приходит.
pycozmo шлёт ping из своего потока сама, но долгая операция (например,
самопроверка) не должна выполняться в обработчике интерфейса.
"""

import queue
import threading
import time
from typing import Any, Callable, NamedTuple, Optional

#: Сколько робот едет после команды, если новых не поступает.
DRIVE_COAST = 0.4


class Event(NamedTuple):
    """Что поток сообщает интерфейсу."""
    kind: str          # status / state / camera / log / error / done
    value: Any = None


class RobotWorker(threading.Thread):
    """Владеет подключением к Козмо. Общение — только через очереди."""

    daemon = True

    def __init__(self) -> None:
        super().__init__(name="cozmo-worker")
        self.commands: queue.Queue = queue.Queue()
        self.events: queue.Queue = queue.Queue()

        self.cli = None
        self.connected = False
        self._running = True
        self._stop_driving_at = 0.0
        self._last_state_push = 0.0

        #: Последний кадр с камеры. Интерфейс забирает его сам.
        self.frame = None
        self.frame_counter = 0

    # --- то, что зовёт интерфейс ---

    def send(self, command: str, **kwargs) -> None:
        """Поставить команду в очередь.

        Параметр называется command, а не name: у команды face есть
        собственный аргумент name, и совпадение имён ломало вызов.
        """
        self.commands.put((command, kwargs))

    def shutdown(self) -> None:
        self._running = False
        self.send("disconnect")

    # --- внутреннее ---

    def emit(self, kind: str, value: Any = None) -> None:
        self.events.put(Event(kind, value))

    def log(self, text: str) -> None:
        self.emit("log", text)

    def run(self) -> None:
        while self._running:
            try:
                command, kwargs = self.commands.get(timeout=0.1)
            except queue.Empty:
                self._tick()
                continue

            handler: Optional[Callable] = getattr(self, f"do_{command}", None)
            if handler is None:
                self.log(f"неизвестная команда: {command}")
                continue
            try:
                handler(**kwargs)
            except Exception as exc:  # noqa: BLE001
                # Поток не должен умирать от ошибки одной команды.
                self.emit("error", f"{command}: {exc}")

        self._disconnect_quietly()

    def _tick(self) -> None:
        """Регулярные дела: автостоп и отправка состояния в интерфейс."""
        now = time.time()

        if self._stop_driving_at and now > self._stop_driving_at:
            self._stop_driving_at = 0.0
            if self.connected:
                try:
                    self.cli.stop_all_motors()
                except Exception:  # noqa: BLE001
                    pass

        if self.connected and now - self._last_state_push > 0.4:
            self._last_state_push = now
            self.emit("state", self.snapshot())

    def snapshot(self) -> dict:
        """Текущее состояние робота одним куском."""
        import pycozmo

        cli = self.cli
        if cli is None:
            return {}

        status = cli.robot_status
        flag = pycozmo.robot.RobotStatusFlag
        return {
            "battery": cli.battery_voltage,
            "firmware": (cli.robot_fw_sig or {}).get("version"),
            "serial": cli.serial_number,
            "hw_version": cli.body_hw_version,
            "head_deg": cli.head_angle.degrees,
            "lift_mm": cli.lift_position.height.mm,
            "on_charger": bool(status & flag.IS_ON_CHARGER),
            "charging": bool(status & flag.IS_CHARGING),
            "picked_up": bool(status & flag.IS_PICKED_UP),
            "cliff": bool(status & flag.CLIFF_DETECTED),
            "moving": bool(status & flag.IS_MOVING),
            "frames": self.frame_counter,
        }

    def _disconnect_quietly(self) -> None:
        if self.cli is None:
            return
        try:
            self.cli.disconnect()
            self.cli.stop()
        except Exception:  # noqa: BLE001
            pass
        self.cli = None
        self.connected = False

    # --- команды ---

    def do_connect(self) -> None:
        import pycozmo
        from pycozmo import exception

        if self.connected:
            return

        self.emit("status", "connecting")
        self.log("Подключаюсь к 172.31.1.1:5551 ...")

        cli = pycozmo.client.Client()
        try:
            cli.start()
            cli.connect()
            cli.wait_for_robot(timeout=8.0)
        except exception.ConnectionTimeout:
            try:
                cli.stop()
            except Exception:  # noqa: BLE001
                pass
            self.emit("status", "offline")
            self.emit("error",
                      "Робот не ответил.\n\n"
                      "• компьютер в Wi-Fi сети Cozmo_XXXXXX?\n"
                      "• робот не спит? поднимите и опустите ковш\n"
                      "• приложение Cozmo на телефоне закрыто?")
            return
        except Exception as exc:  # noqa: BLE001
            try:
                cli.stop()
            except Exception:  # noqa: BLE001
                pass
            self.emit("status", "offline")
            self.emit("error", f"Не удалось подключиться: {exc}")
            return

        cli.add_handler(pycozmo.event.EvtNewRawCameraImage, self._on_camera)
        self.cli = cli
        self.connected = True

        version = (cli.robot_fw_sig or {}).get("version")
        self.emit("status", "online")
        self.log(f"Подключился. Прошивка {version}, "
                 f"серийный номер 0x{cli.serial_number:08x}")
        self.emit("state", self.snapshot())

    def do_disconnect(self) -> None:
        if not self.connected:
            return
        self.log("Отключаюсь.")
        self._disconnect_quietly()
        self.emit("status", "offline")

    def _on_camera(self, cli, image) -> None:
        del cli
        self.frame = image
        self.frame_counter += 1

    def do_camera(self, enable: bool) -> None:
        if not self.connected:
            return
        self.cli.enable_camera(enable=enable, color=False)
        self.log("Камера включена." if enable else "Камера выключена.")
        if not enable:
            self.frame = None

    def do_drive(self, left: float, right: float) -> None:
        if not self.connected:
            return
        self.cli.drive_wheels(left, right)
        self._stop_driving_at = time.time() + DRIVE_COAST

    def do_stop(self) -> None:
        if not self.connected:
            return
        self._stop_driving_at = 0.0
        self.cli.stop_all_motors()

    def do_head(self, degrees: float) -> None:
        import math

        if not self.connected:
            return
        self.cli.set_head_angle(math.radians(degrees))

    def do_lift(self, mm: float) -> None:
        if not self.connected:
            return
        self.cli.set_lift_height(mm)

    def do_face(self, name: str) -> None:
        import pycozmo

        from . import screen

        if not self.connected:
            return
        expression = getattr(pycozmo.expressions, name, None)
        if expression is None:
            self.log(f"нет такой рожицы: {name}")
            return
        self.cli.display_image(screen.to_screen(expression().render()), duration=3.0)

    def do_show_text(self, text: str) -> None:
        from . import screen

        if not self.connected or not text.strip():
            return
        self.cli.display_image(screen.render_text(text[:40]), duration=5.0)
        self.log(f"на экране: «{text}»")

    def do_lights(self, color: str) -> None:
        import pycozmo

        if not self.connected:
            return
        light = {
            "red": pycozmo.lights.red_light,
            "green": pycozmo.lights.green_light,
            "blue": pycozmo.lights.blue_light,
            "white": pycozmo.lights.white_light,
            "off": pycozmo.lights.off_light,
        }.get(color)
        if light is None:
            return
        self.cli.set_all_backpack_lights(light)

    def do_headlight(self, on: bool) -> None:
        if not self.connected:
            return
        self.cli.set_head_light(on)

    def do_volume(self, level: int) -> None:
        if not self.connected:
            return
        self.cli.set_volume(int(level))

    def do_say(self, text: str, engine: str, preset: str) -> None:
        from .speech import LiveVoice

        if not self.connected or not text.strip():
            return
        self.log(f"говорю: «{text}»")
        try:
            voice = LiveVoice(engine=engine, preset=preset, on_note=self.log)
            voice.say(self.cli, text)
        except Exception as exc:  # noqa: BLE001
            self.emit("error", f"Не получилось озвучить: {exc}")
            return
        self.emit("done", "say")

    def do_play_phrase(self, key: str) -> None:
        from .speech import Voice

        if not self.connected:
            return
        voice = Voice()
        if not voice.has(key):
            self.log(f"фразы «{key}» нет, сгенерируйте: scripts/make_voice.py")
            return
        voice.say(self.cli, key)

    def do_selftest(self) -> None:
        """Прогнать робота по всем системам и отчитаться."""
        import pycozmo

        from . import screen

        if not self.connected:
            return

        results = []

        def step(name: str, action: Callable) -> None:
            try:
                action()
            except Exception as exc:  # noqa: BLE001
                results.append((name, False, str(exc)[:60]))
                self.emit("test", (name, False, str(exc)[:60]))
            else:
                results.append((name, True, ""))
                self.emit("test", (name, True, ""))

        self.log("Самопроверка началась.")
        self.emit("test_start", None)

        cli = self.cli

        step("Связь и прошивка", lambda: cli.wait_for(
            pycozmo.event.EvtRobotStateUpdated, timeout=3.0))

        battery = cli.battery_voltage
        ok = battery > 3.5
        results.append(("Батарея", ok, f"{battery:.2f} В"))
        self.emit("test", ("Батарея", ok,
                           f"{battery:.2f} В" + ("" if ok else " — низкая, на базу")))

        def lights_test():
            for colour in (pycozmo.lights.red_light, pycozmo.lights.green_light,
                           pycozmo.lights.blue_light):
                cli.set_all_backpack_lights(colour)
                time.sleep(0.3)
            cli.set_backpack_lights_off()
        step("Лампочки на спине", lights_test)

        step("Экран", lambda: cli.display_image(
            screen.render_text("тест"), duration=1.0))

        step("Голова", lambda: (cli.set_head_angle(0.3), time.sleep(1.0),
                                cli.set_head_angle(0.0), time.sleep(1.0)))

        step("Ковш", lambda: (cli.set_lift_height(pycozmo.robot.MAX_LIFT_HEIGHT.mm),
                              time.sleep(1.2),
                              cli.set_lift_height(pycozmo.robot.MIN_LIFT_HEIGHT.mm),
                              time.sleep(1.2)))

        on_charger = bool(cli.robot_status & pycozmo.robot.RobotStatusFlag.IS_ON_CHARGER)
        if on_charger:
            results.append(("Колёса", True, "пропущено — робот на базе"))
            self.emit("test", ("Колёса", True, "пропущено — робот на базе"))
        else:
            step("Колёса", lambda: (cli.drive_wheels(40.0, -40.0, duration=0.5),
                                    cli.drive_wheels(-40.0, 40.0, duration=0.5),
                                    cli.stop_all_motors()))

        before = self.frame_counter
        cli.enable_camera(enable=True, color=False)
        deadline = time.time() + 8.0
        while self.frame_counter == before and time.time() < deadline:
            time.sleep(0.1)
        got = self.frame_counter > before
        results.append(("Камера", got, "" if got else "кадры не пришли"))
        self.emit("test", ("Камера", got, "" if got else "кадры не пришли"))

        passed = sum(1 for _, ok, _ in results if ok)
        self.log(f"Самопроверка закончена: {passed} из {len(results)} в порядке.")
        self.emit("test_done", (passed, len(results)))
