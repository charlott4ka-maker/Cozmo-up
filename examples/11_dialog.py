#!/usr/bin/env python
"""Шаг 11. Разговор: ты спрашиваешь — Козмо отвечает.

Слушает МИКРОФОН КОМПЬЮТЕРА (микрофоны самого робота в протоколе
недоступны — туда можно только отправлять звук), распознаёт русскую речь
офлайн через Vosk и отвечает заранее озвученными фразами.

ПЕРЕД ПЕРВЫМ ЗАПУСКОМ, при интернете:
    python scripts/make_voice.py            # озвучка фраз
    python examples/11_dialog.py --setup    # скачать модель распознавания

Потом подключайтесь к Wi-Fi робота — дальше интернет не нужен.

Что понимает: привет, вперёд, назад, налево, направо, стоп, танцуй,
как дела, кто ты, что умеешь, сколько заряд, подними/опусти ковш, пока.
Полный список — в dialog.ru.json, правьте под себя.
"""

import argparse
import sys
from pathlib import Path

import pycozmo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.brain import Brain  # noqa: E402
from cozmo_up.ears import Listener, list_microphones  # noqa: E402
from cozmo_up.screen import render_text  # noqa: E402
from cozmo_up.speech import Voice  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--setup", action="store_true",
                        help="скачать модель распознавания и выйти (нужен интернет)")
    parser.add_argument("--microphones", action="store_true",
                        help="показать список микрофонов и выйти")
    parser.add_argument("--device", type=int, default=None,
                        help="номер микрофона (см. --microphones)")
    parser.add_argument("--free-speech", action="store_true",
                        help="не ограничивать словарь командами "
                             "(точность ниже, зато слышит любые слова)")
    args = parser.parse_args()

    if args.microphones:
        list_microphones()
        return 0

    voice = Voice()
    if not voice.keys():
        print("Нет озвученных фраз. Выполните: python scripts/make_voice.py")
        return 1

    brain = Brain(voice)

    if args.setup:
        print("Скачиваю модель распознавания русской речи (~45 МБ)...")
        Listener(words=brain.vocabulary())
        print("Готово. Теперь можно подключаться к Wi-Fi робота.")
        return 0

    print("Загружаю распознавание речи...")
    words = None if args.free_speech else brain.vocabulary()
    listener = Listener(words=words, device=args.device)

    print("Подключаюсь к роботу...")
    with pycozmo.connect() as cli:
        cli.set_volume(50000)
        cli.set_head_angle(0.0)

        voice.say_and_show(cli, "slushayu")
        print("\nГовори! «пока» — закончить, Ctrl+C — прервать.\n")

        with listener:
            while brain.running:
                cli.display_image(render_text("слушаю..."))
                text = listener.listen(timeout=30.0)

                if not text:
                    continue

                rule = brain.match(text)
                mark = "→" if rule else "?"
                print(f"  {mark} услышал: «{text}»")

                brain.handle(cli, text)

        cli.stop_all_motors()
        cli.set_backpack_lights_off()
        cli.clear_screen()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
