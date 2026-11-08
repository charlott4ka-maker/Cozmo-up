#!/usr/bin/env python
"""Козмо — приложение для ноутбука.

Подключение, заряд, камера, управление, речь и самопроверка в одном окне.

Запуск:
    python app.py
или на Windows просто двойным щелчком по «Козмо.bat».

Подключается по Wi-Fi: компьютер должен быть в сети Cozmo_XXXXXX.
Bluetooth не используется — pycozmo его не поддерживает, и камеру через
него всё равно не прокачать.
"""

import queue
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cozmo_up.worker import RobotWorker  # noqa: E402

SPEED, TURN = 80.0, 60.0

#: Рожицы на кнопках: подпись -> класс из pycozmo.expressions
FACES = [
    ("радость", "Happiness"), ("удивление", "Surprise"), ("злость", "Anger"),
    ("грусть", "Sadness"), ("восторг", "Excitement"), ("сон", "Asleep"),
]

COLORS = {
    "bg": "#1e1f26", "panel": "#282a36", "text": "#f0f0f0",
    "dim": "#9aa0b0", "ok": "#50d890", "warn": "#f5c451", "bad": "#f05a5a",
    "accent": "#6c8cff",
}


class CozmoApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Козмо")
        self.geometry("1060x780")
        self.minsize(900, 620)
        self.configure(bg=COLORS["bg"])

        self.worker = RobotWorker()
        self.worker.start()

        self.connected = False
        self.photo = None            # ссылку надо держать, иначе картинка исчезнет
        self.detector = None
        self.shots = 0

        self._build_styles()
        self._build_ui()
        self._bind_keys()

        self.closing = False
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(50, self.pump)
        self.after(100, self.refresh_camera)

    # ---------------------------------------------------------------- стиль

    def _build_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=COLORS["panel"], foreground=COLORS["text"],
                        fieldbackground=COLORS["bg"], borderwidth=0)
        style.configure("TFrame", background=COLORS["panel"])
        style.configure("Bg.TFrame", background=COLORS["bg"])
        style.configure("TLabel", background=COLORS["panel"], foreground=COLORS["text"])
        style.configure("Dim.TLabel", foreground=COLORS["dim"])
        style.configure("Head.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", padding=6)
        style.configure("TNotebook", background=COLORS["bg"])
        style.configure("TNotebook.Tab", padding=(14, 7))
        style.configure("Battery.Horizontal.TProgressbar",
                        troughcolor=COLORS["bg"], background=COLORS["ok"])

    # ------------------------------------------------------------- интерфейс

    def _build_ui(self) -> None:
        top = ttk.Frame(self, style="Bg.TFrame", padding=(12, 10))
        top.pack(fill="x")

        self.btn_connect = ttk.Button(top, text="Подключиться",
                                      command=self.toggle_connection)
        self.btn_connect.pack(side="left")

        self.lamp = tk.Canvas(top, width=14, height=14, highlightthickness=0,
                              bg=COLORS["bg"])
        self.lamp.pack(side="left", padx=(14, 6))
        self.lamp_dot = self.lamp.create_oval(2, 2, 12, 12, fill=COLORS["bad"],
                                              outline="")

        self.lbl_status = ttk.Label(top, text="не подключён", style="Dim.TLabel")
        self.lbl_status.configure(background=COLORS["bg"])
        self.lbl_status.pack(side="left")

        ttk.Label(top, text="172.31.1.1:5551  •  Wi-Fi Cozmo_XXXXXX",
                  style="Dim.TLabel", background=COLORS["bg"]).pack(side="right")

        # Журнал пакуем ДО основной области: pack раздаёт место в порядке
        # вызовов, и иначе растягивающийся body не оставляет журналу ничего.
        self._build_log()

        body = ttk.Frame(self, style="Bg.TFrame", padding=(12, 0))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(0, weight=1)

        self._build_camera(body)
        self._build_right(body)

    def _build_camera(self, parent) -> None:
        box = ttk.Frame(parent, padding=10)
        box.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))

        ttk.Label(box, text="Камера", style="Head.TLabel").pack(anchor="w")

        self.canvas = tk.Canvas(box, width=384, height=288, bg="#101119",
                                highlightthickness=0)
        self.canvas.pack(pady=8)
        self.canvas_text = self.canvas.create_text(
            192, 144, text="камера выключена", fill=COLORS["dim"],
            font=("Segoe UI", 10))

        row = ttk.Frame(box)
        row.pack(fill="x")
        self.var_camera = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="включить", variable=self.var_camera,
                        command=self.toggle_camera).pack(side="left")
        self.var_markers = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="маркеры", variable=self.var_markers,
                        command=self.toggle_markers).pack(side="left", padx=8)
        ttk.Button(row, text="Снимок", command=self.snapshot).pack(side="right")

        self.lbl_frames = ttk.Label(box, text="", style="Dim.TLabel")
        self.lbl_frames.pack(anchor="w", pady=(6, 0))

    def _build_right(self, parent) -> None:
        right = ttk.Frame(parent, style="Bg.TFrame")
        right.grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self._build_state(right)

        tabs = ttk.Notebook(right)
        tabs.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self._build_tab_control(tabs)
        self._build_tab_speech(tabs)
        self._build_tab_test(tabs)

    def _build_state(self, parent) -> None:
        box = ttk.Frame(parent, padding=10)
        box.grid(row=0, column=0, sticky="ew")
        box.columnconfigure(1, weight=1)

        ttk.Label(box, text="Состояние", style="Head.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Label(box, text="Батарея").grid(row=1, column=0, sticky="w")
        self.bar = ttk.Progressbar(box, style="Battery.Horizontal.TProgressbar",
                                   maximum=100, length=180)
        self.bar.grid(row=1, column=1, sticky="ew", padx=8)
        self.lbl_battery = ttk.Label(box, text="—", width=14)
        self.lbl_battery.grid(row=1, column=2, sticky="e")

        self.fields = {}
        rows = [("firmware", "Прошивка"), ("serial", "Серийный номер"),
                ("head_deg", "Голова"), ("lift_mm", "Ковш")]
        for i, (key, label) in enumerate(rows, start=2):
            ttk.Label(box, text=label, style="Dim.TLabel").grid(
                row=i, column=0, sticky="w", pady=1)
            value = ttk.Label(box, text="—")
            value.grid(row=i, column=1, columnspan=2, sticky="w", padx=8)
            self.fields[key] = value

        flags = ttk.Frame(box)
        flags.grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self.flags = {}
        for key, label in [("on_charger", "на базе"), ("charging", "заряжается"),
                           ("picked_up", "подняли"), ("cliff", "обрыв"),
                           ("moving", "едет")]:
            chip = tk.Label(flags, text=label, bg=COLORS["bg"], fg=COLORS["dim"],
                            padx=8, pady=3, font=("Segoe UI", 8))
            chip.pack(side="left", padx=(0, 5))
            self.flags[key] = chip

    def _build_tab_control(self, tabs) -> None:
        tab = ttk.Frame(tabs, padding=12)
        tabs.add(tab, text="Управление")

        pad = ttk.Frame(tab)
        pad.pack()
        mk = lambda t, l, r: ttk.Button(  # noqa: E731
            pad, text=t, width=5, command=lambda: self.drive(l, r))
        mk("↑", SPEED, SPEED).grid(row=0, column=1, pady=2)
        mk("←", -TURN, TURN).grid(row=1, column=0, padx=2)
        ttk.Button(pad, text="■", width=5, command=self.stop).grid(row=1, column=1)
        mk("→", TURN, -TURN).grid(row=1, column=2, padx=2)
        mk("↓", -SPEED, -SPEED).grid(row=2, column=1, pady=2)

        ttk.Label(tab, text="клавиши: стрелки или WASD, пробел — стоп",
                  style="Dim.TLabel").pack(pady=(8, 12))

        self._slider(tab, "Голова", -25, 44, 0, lambda v: self.worker.send(
            "head", degrees=float(v)))
        self._slider(tab, "Ковш", 32, 92, 32, lambda v: self.worker.send(
            "lift", mm=float(v)))

        ttk.Label(tab, text="Рожицы").pack(anchor="w", pady=(12, 4))
        faces = ttk.Frame(tab)
        faces.pack(anchor="w")
        for i, (label, name) in enumerate(FACES):
            ttk.Button(faces, text=label, width=10,
                       command=lambda n=name: self.worker.send("face", name=n)
                       ).grid(row=i // 3, column=i % 3, padx=2, pady=2)

        ttk.Label(tab, text="Лампочки").pack(anchor="w", pady=(12, 4))
        lights = ttk.Frame(tab)
        lights.pack(anchor="w")
        for label, name in [("красный", "red"), ("зелёный", "green"),
                            ("синий", "blue"), ("белый", "white"), ("выкл", "off")]:
            ttk.Button(lights, text=label, width=9,
                       command=lambda n=name: self.worker.send("lights", color=n)
                       ).pack(side="left", padx=2)

        self.var_headlight = tk.BooleanVar(value=False)
        ttk.Checkbutton(tab, text="фонарик над камерой", variable=self.var_headlight,
                        command=lambda: self.worker.send(
                            "headlight", on=self.var_headlight.get())
                        ).pack(anchor="w", pady=(10, 0))

    def _slider(self, parent, label, lo, hi, start, callback) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=8).pack(side="left")
        scale = ttk.Scale(row, from_=lo, to=hi, value=start, command=callback)
        scale.pack(side="left", fill="x", expand=True, padx=6)

    def _build_tab_speech(self, tabs) -> None:
        tab = ttk.Frame(tabs, padding=12)
        tabs.add(tab, text="Речь и экран")

        ttk.Label(tab, text="Сказать голосом").pack(anchor="w")
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(4, 2))
        self.entry_say = ttk.Entry(row)
        self.entry_say.pack(side="left", fill="x", expand=True)
        self.entry_say.bind("<Return>", lambda e: self.say())
        ttk.Button(row, text="Сказать", command=self.say).pack(side="left", padx=(6, 0))

        opts = ttk.Frame(tab)
        opts.pack(fill="x", pady=(2, 12))
        ttk.Label(opts, text="голос", style="Dim.TLabel").pack(side="left")
        self.var_preset = tk.StringVar(value="kozmo")
        ttk.Combobox(opts, textvariable=self.var_preset, width=10, state="readonly",
                     values=["kozmo", "malchik", "malysh", "vzroslyj", "devushka"]
                     ).pack(side="left", padx=6)
        ttk.Label(opts, text="движок", style="Dim.TLabel").pack(side="left")
        self.var_engine = tk.StringVar(value="edge")
        ttk.Combobox(opts, textvariable=self.var_engine, width=8, state="readonly",
                     values=["edge", "espeak", "system"]).pack(side="left", padx=6)
        ttk.Label(opts, text="(edge — нужен интернет)", style="Dim.TLabel").pack(
            side="left")

        ttk.Label(tab, text="Написать на экране робота").pack(anchor="w")
        row2 = ttk.Frame(tab)
        row2.pack(fill="x", pady=4)
        self.entry_screen = ttk.Entry(row2)
        self.entry_screen.pack(side="left", fill="x", expand=True)
        self.entry_screen.bind("<Return>", lambda e: self.show_text())
        ttk.Button(row2, text="Показать", command=self.show_text).pack(
            side="left", padx=(6, 0))

        ttk.Label(tab, text="Громкость").pack(anchor="w", pady=(12, 0))
        self.var_volume = tk.IntVar(value=50000)
        ttk.Scale(tab, from_=0, to=65535, variable=self.var_volume,
                  command=lambda v: self.worker.send("volume", level=float(v))
                  ).pack(fill="x", pady=4)

        ttk.Label(tab, text="Заготовленные фразы — из phrases.ru.json",
                  style="Dim.TLabel").pack(anchor="w", pady=(12, 4))
        self.phrases_box = ttk.Frame(tab)
        self.phrases_box.pack(fill="x")
        self._load_phrase_buttons()

    def _load_phrase_buttons(self) -> None:
        from cozmo_up.speech import Voice

        keys = Voice().keys()[:12]
        if not keys:
            ttk.Label(self.phrases_box,
                      text="нет озвучки — запустите scripts/make_voice.py",
                      style="Dim.TLabel").pack(anchor="w")
            return
        for i, key in enumerate(keys):
            ttk.Button(self.phrases_box, text=key, width=14,
                       command=lambda k=key: self.worker.send("play_phrase", key=k)
                       ).grid(row=i // 4, column=i % 4, padx=2, pady=2)

    def _build_tab_test(self, tabs) -> None:
        tab = ttk.Frame(tabs, padding=12)
        tabs.add(tab, text="Проверка")

        ttk.Label(tab, text="Прогонит робота по всем системам и покажет, "
                            "что работает.", style="Dim.TLabel",
                  wraplength=420).pack(anchor="w")

        self.btn_test = ttk.Button(tab, text="Запустить самопроверку",
                                   command=self.run_selftest)
        self.btn_test.pack(anchor="w", pady=10)

        self.test_list = tk.Listbox(tab, height=11, bg=COLORS["bg"],
                                    fg=COLORS["text"], highlightthickness=0,
                                    borderwidth=0, font=("Consolas", 9),
                                    selectbackground=COLORS["accent"])
        self.test_list.pack(fill="both", expand=True)

    def _build_log(self) -> None:
        box = ttk.Frame(self, style="Bg.TFrame", padding=(12, 0, 12, 12))
        box.pack(side="bottom", fill="x")
        ttk.Label(box, text="Журнал", style="Dim.TLabel",
                  background=COLORS["bg"]).pack(anchor="w", pady=(0, 4))
        self.log_box = tk.Text(box, height=6, bg=COLORS["panel"], fg=COLORS["dim"],
                               highlightthickness=0, borderwidth=0, wrap="word",
                               font=("Consolas", 9))
        self.log_box.pack(fill="x")
        self.log_box.configure(state="disabled")

    def _bind_keys(self) -> None:
        moves = {
            "<Up>": (SPEED, SPEED), "w": (SPEED, SPEED),
            "<Down>": (-SPEED, -SPEED), "s": (-SPEED, -SPEED),
            "<Left>": (-TURN, TURN), "a": (-TURN, TURN),
            "<Right>": (TURN, -TURN), "d": (TURN, -TURN),
        }
        for key, (left, right) in moves.items():
            seq = key if key.startswith("<") else f"<KeyPress-{key}>"
            self.bind(seq, lambda e, l=left, r=right: self.drive(l, r))
        self.bind("<space>", lambda e: self.stop())

    # ------------------------------------------------------------- действия

    def toggle_connection(self) -> None:
        self.worker.send("disconnect" if self.connected else "connect")

    def drive(self, left: float, right: float) -> None:
        self.worker.send("drive", left=left, right=right)

    def stop(self) -> None:
        self.worker.send("stop")

    def toggle_camera(self) -> None:
        self.worker.send("camera", enable=self.var_camera.get())

    def toggle_markers(self) -> None:
        if self.var_markers.get() and self.detector is None:
            try:
                from cozmo_up.vision import MarkerDetector

                self.detector = MarkerDetector()
            except Exception as exc:  # noqa: BLE001
                self.var_markers.set(False)
                messagebox.showerror("Маркеры",
                                     f"Не удалось включить распознавание:\n{exc}")

    def snapshot(self) -> None:
        frame = self.worker.frame
        if frame is None:
            messagebox.showinfo("Снимок", "Кадра пока нет — включите камеру.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png", initialfile=f"cozmo_{self.shots:03d}.png",
            filetypes=[("PNG", "*.png")])
        if not path:
            return
        frame.save(path)
        self.shots += 1
        self.log(f"снимок сохранён: {path}")

    def say(self) -> None:
        text = self.entry_say.get().strip()
        if text:
            self.worker.send("say", text=text, engine=self.var_engine.get(),
                             preset=self.var_preset.get())

    def show_text(self) -> None:
        text = self.entry_screen.get().strip()
        if text:
            self.worker.send("show_text", text=text)

    def run_selftest(self) -> None:
        if not self.connected:
            messagebox.showinfo("Проверка", "Сначала подключитесь к роботу.")
            return
        self.btn_test.configure(state="disabled")
        self.worker.send("selftest")

    # -------------------------------------------------------------- отрисовка

    def log(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def set_status(self, status: str) -> None:
        colour, label = {
            "online": (COLORS["ok"], "подключён"),
            "connecting": (COLORS["warn"], "подключаюсь..."),
            "offline": (COLORS["bad"], "не подключён"),
        }.get(status, (COLORS["bad"], status))
        self.lamp.itemconfigure(self.lamp_dot, fill=colour)
        self.lbl_status.configure(text=label)
        self.connected = status == "online"
        self.btn_connect.configure(
            text="Отключиться" if self.connected else "Подключиться")

    def apply_state(self, state: dict) -> None:
        volts = state.get("battery") or 0.0
        # 3.5 В — почти разряжен, 4.1 — полный.
        percent = max(0, min(100, (volts - 3.5) / 0.6 * 100))
        self.bar["value"] = percent
        self.lbl_battery.configure(text=f"{volts:.2f} В · {percent:.0f}%")
        style = ttk.Style(self)
        style.configure("Battery.Horizontal.TProgressbar",
                        background=COLORS["ok"] if percent > 40
                        else COLORS["warn"] if percent > 15 else COLORS["bad"])

        serial = state.get("serial")
        self.fields["firmware"].configure(text=str(state.get("firmware") or "—"))
        self.fields["serial"].configure(
            text=f"0x{serial:08x}" if serial else "—")
        self.fields["head_deg"].configure(text=f"{state.get('head_deg', 0):.1f}°")
        self.fields["lift_mm"].configure(text=f"{state.get('lift_mm', 0):.0f} мм")

        for key, chip in self.flags.items():
            on = bool(state.get(key))
            chip.configure(fg=COLORS["text"] if on else COLORS["dim"],
                           bg=COLORS["accent"] if on else COLORS["bg"])

        self.lbl_frames.configure(text=f"кадров получено: {state.get('frames', 0)}")

    def refresh_camera(self) -> None:
        """Перерисовать кадр. Отдельным таймером, ~12 кадров в секунду."""
        frame = self.worker.frame
        if frame is not None and self.var_camera.get():
            try:
                self._draw_frame(frame)
            except Exception:  # noqa: BLE001
                pass
        self.after(80, self.refresh_camera)

    def _draw_frame(self, frame) -> None:
        from PIL import Image, ImageTk

        if self.var_markers.get() and self.detector is not None:
            import numpy as np

            drawn = self.detector.draw(frame)
            image = Image.fromarray(drawn[:, :, ::-1].astype(np.uint8))
        else:
            image = frame.convert("RGB")

        image = image.resize((384, 288), Image.NEAREST)
        self.photo = ImageTk.PhotoImage(image)
        self.canvas.delete("frame")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo, tags="frame")
        self.canvas.tag_lower("frame")
        self.canvas.itemconfigure(self.canvas_text, text="")

    def pump(self) -> None:
        """Забрать события из фонового потока. Крутится в главном потоке."""
        try:
            while True:
                event = self.worker.events.get_nowait()

                if event.kind == "status":
                    self.set_status(event.value)
                elif event.kind == "state":
                    self.apply_state(event.value)
                elif event.kind == "log":
                    self.log(event.value)
                elif event.kind == "error":
                    self.log("ОШИБКА: " + event.value.replace("\n", " "))
                    if not self.closing:
                        messagebox.showerror("Козмо", event.value)
                elif event.kind == "test_start":
                    self.test_list.delete(0, "end")
                elif event.kind == "test":
                    name, ok, note = event.value
                    mark = "OK  " if ok else "НЕТ "
                    self.test_list.insert("end", f"{mark}{name}"
                                                 + (f"  — {note}" if note else ""))
                    self.test_list.see("end")
                elif event.kind == "test_done":
                    passed, total = event.value
                    self.test_list.insert("end", "")
                    self.test_list.insert("end", f"Итого: {passed} из {total}")
                    self.btn_test.configure(state="normal")
                    self.var_camera.set(True)
        except queue.Empty:
            pass
        self.after(50, self.pump)

    def on_close(self) -> None:
        self.closing = True
        self.worker.shutdown()
        self.after(150, self.destroy)


def main() -> int:
    app = CozmoApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
