#!/usr/bin/env python
"""Шаг 18. Настоящий ИИ: Козмо отвечает своими словами, помнит и учится.

Он больше не ограничен заготовленными фразами. Слушает микрофон, думает
через Claude (или локальную модель), отвечает голосом и может при этом
что-то сделать телом.

ЧЕМУ ЕГО УЧИТЬ ПРЯМО В РАЗГОВОРЕ:
    «Запомни, что меня зовут Даша»     -> запишет в memory.json навсегда
    «Забудь про пиццу»                 -> забудет
КАК ДАТЬ ЕМУ СВОЮ БАЗУ:
    положите .txt или .md файлы в папку knowledge/ — он начнёт их знать

ПО УМОЛЧАНИЮ ДУМАЕТ ЛОКАЛЬНО — модель крутится на вашем компьютере через
Ollama. Ни интернета, ни ключей, ни оплаты. Настройка и выбор модели:
    python scripts/local_ai.py check

ПЕРЕД ПЕРВЫМ ЗАПУСКОМ (при обычном интернете, один раз):
    python scripts/make_voice.py            # голос
    python examples/11_dialog.py --setup    # распознавание речи
    ollama pull qwen2.5:3b                  # сама модель

ГОЛОС тоже умеет офлайн: добавьте --tts espeak, и интернет не нужен совсем.

ЕСЛИ ХОЧЕТСЯ УМНЕЕ: --backend claude работает по сети и говорит по-русски
заметно лучше, но нужен ключ ANTHROPIC_API_KEY и интернет, которого в
Wi-Fi робота нет (решается раздачей с телефона по USB).

Проверить всё без робота и без микрофона:
    python examples/18_ai.py --text
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.ai import ACTIONS, AIBrain, Knowledge, Memory, make_backend  # noqa: E402
from cozmo_up.brain import Brain  # noqa: E402
from cozmo_up.screen import render_text, to_screen  # noqa: E402
from cozmo_up.speech import LiveVoice, Voice  # noqa: E402

#: Действие ИИ -> действие, которое умеет Brain.do().
ACTION_MAP = {
    "вперёд": "forward", "назад": "back", "налево": "left", "направо": "right",
    "стоп": "stop", "танцуй": "dance", "ковш_вверх": "lift_up",
    "ковш_вниз": "lift_down", "смотри_вверх": "look_up", "заряд": "battery",
}


def build_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend", choices=["ollama", "claude"], default="ollama",
                        help="кто придумывает ответы. ollama — своя модель на "
                             "вашем компьютере (по умолчанию); claude — по сети")
    parser.add_argument("--model", default=None, help="конкретная модель")
    parser.add_argument("--tts", choices=["edge", "espeak", "system"], default="edge",
                        help="чем озвучивать ответы (espeak работает офлайн)")
    parser.add_argument("--preset", default="kozmo", help="голос, см. make_voice.py")
    parser.add_argument("--text", action="store_true",
                        help="печатать в консоль вместо робота и микрофона "
                             "— удобно проверить ИИ отдельно")
    parser.add_argument("--device", type=int, default=None, help="номер микрофона")
    parser.add_argument("--free-speech", action="store_true",
                        help="слушать любые слова, а не только знакомые "
                             "(для свободных вопросов это обычно нужно)")
    return parser.parse_args()


def make_brain(args) -> AIBrain:
    kwargs = {"model": args.model} if args.model else {}
    backend = make_backend(args.backend, **kwargs)
    brain = AIBrain(backend, memory=Memory(), knowledge=Knowledge())
    model_name = getattr(backend, "model", None)
    print(f"Мозг: {backend.name}" + (f" ({model_name})" if model_name else ""))
    print(f"Помнит фактов: {len(brain.memory.facts)}")
    print(f"База знаний: {len(brain.knowledge.chunks)} кусочков "
          f"из папки knowledge/")
    return brain


def run_text_mode(args) -> int:
    """Без робота и микрофона — просто поговорить в консоли."""
    brain = make_brain(args)
    print("\nПиши вопросы. «выход» — закончить.\n")
    while True:
        try:
            question = input("ты > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in ("выход", "quit", "exit", ""):
            break
        reply = brain.ask(question)
        print(f"Козмо > {reply.text}")
        if reply.action:
            print(f"        [сделал бы: {reply.action}]")
    return 0


def run_robot_mode(args) -> int:
    import pycozmo

    from cozmo_up.ears import Listener

    brain = make_brain(args)
    voice = LiveVoice(engine=args.tts, preset=args.preset)
    canned = Voice()
    body = Brain(canned)

    print("\nЗагружаю распознавание речи...")
    # Со свободными вопросами словарь ограничивать нельзя — иначе он
    # услышит только заранее известные слова.
    words = None if args.free_speech else None
    listener = Listener(words=words, device=args.device)

    print("Подключаюсь к роботу...")
    with pycozmo.connect() as cli:
        cli.set_volume(50000)
        cli.set_head_angle(0.0)
        time.sleep(0.5)

        voice.say_and_show(cli, "Привет! Спрашивай что хочешь.")
        print("\nГовори. «пока» — закончить, Ctrl+C — прервать.\n")

        with listener:
            while True:
                cli.display_image(render_text("слушаю..."))
                question = listener.listen(timeout=60.0)
                if not question:
                    continue

                print(f"  ты: «{question}»")

                if question.strip() in ("пока", "до свидания", "хватит"):
                    voice.say_and_show(cli, "Пока! Было здорово.")
                    break

                cli.display_image(to_screen(
                    pycozmo.expressions.Skepticism().render()))

                reply = brain.ask(question)
                print(f"  Козмо: «{reply.text}»"
                      + (f"  [{reply.action}]" if reply.action else ""))

                if reply.taught:
                    cli.display_image(to_screen(
                        pycozmo.expressions.Amazement().render()))

                voice.say(cli, reply.text)

                if reply.action:
                    body.do(cli, ACTION_MAP.get(reply.action, "stop"))

        cli.stop_all_motors()
        cli.clear_screen()

    print(f"\nЗапомнено фактов: {len(brain.memory.facts)} (в memory.json)")
    return 0


def main() -> int:
    args = build_args()
    try:
        if args.text:
            return run_text_mode(args)
        return run_robot_mode(args)
    except RuntimeError as exc:
        print(f"\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
