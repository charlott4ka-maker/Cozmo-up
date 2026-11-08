"""Простой диалоговый движок: распознанная фраза -> реакция робота.

Правила лежат в dialog.ru.json. Проверяются сверху вниз, срабатывает
первое правило, у которого хоть одно слово из keywords встретилось во
фразе. Это намеренно просто и предсказуемо — легко читать и легко менять.
"""

import json
import time
from pathlib import Path
from typing import Optional

from . import screen
from .ears import for_vocabulary, normalize

DEFAULT_RULES = Path("dialog.ru.json")


class Brain:
    """Разбирает фразы и выполняет действия на роботе."""

    def __init__(self, voice, rules_path: Path | str = DEFAULT_RULES) -> None:
        self.voice = voice
        data = json.loads(Path(rules_path).read_text(encoding="utf-8"))
        self.rules = data["rules"]
        self.fallback = data.get("fallback", {})
        self.running = True

    def vocabulary(self) -> list:
        """Все слова, которые мы вообще ожидаем услышать."""
        words = set()
        for rule in self.rules:
            for phrase in rule["keywords"]:
                # ё сохраняем: в словаре модели слова записаны с ней.
                words.update(for_vocabulary(phrase).split())
        return sorted(words)

    def match(self, text: str) -> Optional[dict]:
        """Найти подходящее правило. None, если ничего не подошло."""
        text = normalize(text)
        if not text:
            return None
        for rule in self.rules:
            for phrase in rule["keywords"]:
                if normalize(phrase) in text:
                    return rule
        return None

    def handle(self, cli, text: str) -> dict:
        """Отреагировать на фразу. Возвращает сработавшее правило."""
        rule = self.match(text) or self.fallback

        face = rule.get("face")
        if face:
            import pycozmo

            expression = getattr(pycozmo.expressions, face, None)
            if expression:
                cli.display_image(screen.to_screen(expression().render()))

        say = rule.get("say")
        if say and self.voice.has(say):
            self.voice.say(cli, say)

        action = rule.get("action")
        if action:
            self.do(cli, action)

        return rule

    def do(self, cli, action: str) -> None:
        """Выполнить действие телом робота."""
        import pycozmo

        if action == "forward":
            cli.drive_wheels(50.0, 50.0, duration=1.5)
        elif action == "back":
            cli.drive_wheels(-50.0, -50.0, duration=1.5)
        elif action == "left":
            cli.drive_wheels(-40.0, 40.0, duration=0.9)
        elif action == "right":
            cli.drive_wheels(40.0, -40.0, duration=0.9)
        elif action == "stop":
            cli.stop_all_motors()
        elif action == "lift_up":
            cli.set_lift_height(pycozmo.robot.MAX_LIFT_HEIGHT.mm)
            time.sleep(1.0)
        elif action == "lift_down":
            cli.set_lift_height(pycozmo.robot.MIN_LIFT_HEIGHT.mm)
            time.sleep(1.0)
        elif action == "look_up":
            cli.set_head_angle(pycozmo.robot.MAX_HEAD_ANGLE.radians)
            time.sleep(1.0)
        elif action == "dance":
            for _ in range(2):
                cli.drive_wheels(60.0, -60.0, duration=0.4)
                cli.drive_wheels(-60.0, 60.0, duration=0.4)
            cli.stop_all_motors()
        elif action == "battery":
            cli.wait_for(pycozmo.event.EvtRobotStateUpdated, timeout=2.0)
            volts = cli.battery_voltage
            cli.display_image(screen.render_text(f"Батарея\n{volts:.2f} В"))
            key = "zaryadka" if volts < 3.6 else "gotov"
            if self.voice.has(key):
                self.voice.say(cli, key)
            time.sleep(1.5)
        elif action == "quit":
            self.running = False
