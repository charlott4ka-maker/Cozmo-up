#!/usr/bin/env python
"""Шаг 9. Робот говорит по-русски.

Родного русского синтеза у Cozmo нет (в ассетах только английский,
французский, немецкий и японский голоса Acapela). Поэтому фразы
озвучиваются заранее на компьютере и проигрываются как WAV.

ПЕРЕД ЗАПУСКОМ, при интернете:
    python scripts/make_voice.py

Потом подключитесь к Wi-Fi робота и запускайте этот пример.
"""

import sys
import time
from pathlib import Path

import pycozmo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.screen import to_screen  # noqa: E402
from cozmo_up.speech import Voice  # noqa: E402


def main() -> int:
    voice = Voice()
    keys = voice.keys()

    if not keys:
        print("Нет озвученных фраз в voices/.")
        print("Сначала выполните (при интернете): python scripts/make_voice.py")
        return 1

    print(f"Найдено фраз: {len(keys)}")

    with pycozmo.connect() as cli:
        # Громкость: 0-65535. По умолчанию тихо.
        cli.set_volume(50000)
        time.sleep(0.3)

        for key in keys:
            text = voice.text(key) or key
            print(f"  «{text}»")
            # say_and_show покажет текст на экране и проиграет звук.
            voice.say_and_show(cli, key)
            time.sleep(0.4)

        # Звук вместе с мимикой.
        cli.display_image(to_screen(pycozmo.expressions.Happiness().render()))
        voice.say(cli, "ura" if voice.has("ura") else keys[0])
        time.sleep(0.5)

        cli.clear_screen()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
