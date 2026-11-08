#!/usr/bin/env python
"""Локальный ИИ для Козмо: свой, на вашем компьютере, без интернета.

    python scripts/local_ai.py check     # что установлено и что потянет машина
    python scripts/local_ai.py test      # сравнить ваши модели на русском
    python scripts/local_ai.py build     # собрать СВОЮ модель «kozmo»
    python scripts/local_ai.py chat      # поговорить без робота

Сначала поставьте Ollama: https://ollama.com/download
Потом скачайте какую-нибудь модель, например:

    ollama pull qwen2.5:3b        ~2 ГБ, минимум для разговора
    ollama pull qwen2.5:7b        ~4.7 ГБ, заметно умнее
    ollama pull llama3.1:8b       ~4.7 ГБ

Какая из них лучше говорит по-русски на ВАШЕМ железе — покажет `test`:
он задаёт всем одинаковые вопросы и печатает ответы рядом со временем.
Верить чужим рейтингам тут бессмысленно, качество сильно зависит от
машины и от того, что вы спрашиваете.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.ai import ACTIONS, SYSTEM_PROMPT, Memory  # noqa: E402
from cozmo_up.cli import script_cmd  # noqa: E402
from cozmo_up.local_ai import (  # noqa: E402
    DEFAULT_HOST, OWN_MODEL, ask_model, create_model, free_memory_gb,
    is_running, list_models, make_modelfile, size_advice,
)

#: Вопросы для сравнения моделей. Простые, но показательные:
#: грамматика, факты, счёт, следование формату и честность.
TEST_QUESTIONS = [
    "Привет! Как тебя зовут?",
    "Расскажи в двух предложениях, что ты умеешь.",
    "Сколько будет семнадцать плюс двадцать пять?",
    "Поезжай вперёд.",
    "Какая столица Австралии?",
]


def need_ollama(host: str) -> bool:
    if is_running(host):
        return True
    print("Ollama не отвечает.\n")
    print("  1. Поставьте её: https://ollama.com/download")
    print("  2. Запустите (на Windows она висит значком в трее)")
    print(f"  3. Проверьте, что адрес верный: {host}")
    return False


def cmd_check(args) -> int:
    print(f"Папка: {Path.cwd()}\n")
    print("=== Железо ===")
    free = free_memory_gb()
    print(" ", size_advice(free))
    print()

    print("=== Ollama ===")
    if not need_ollama(args.host):
        return 1
    print(f"  работает на {args.host}")
    print()

    models = list_models(args.host)
    if not models:
        print("Моделей пока нет. Скачайте первую:\n")
        if free is not None and free < 6:
            print("  ollama pull qwen2.5:3b      (~2 ГБ, под вашу память)")
        else:
            print("  ollama pull qwen2.5:7b      (~4.7 ГБ)")
            print("  ollama pull qwen2.5:3b      (~2 ГБ, если первая тормозит)")
        return 0

    print(f"=== Скачанные модели ({len(models)}) ===")
    for m in models:
        own = "  <- ваша собственная" if m["name"].startswith(OWN_MODEL) else ""
        print(f"  {m['name']:30} {m['size_gb']:5} ГБ  {m['parameter_size']:>6}{own}")
    print()
    print("Сравнить их на русском:   " + script_cmd("scripts/local_ai.py", "test"))
    print("Собрать свою модель:      " + script_cmd("scripts/local_ai.py", "build"))
    return 0


def cmd_test(args) -> int:
    if not need_ollama(args.host):
        return 1

    models = [m["name"] for m in list_models(args.host)]
    if args.model:
        models = [m for m in models if m in args.model]
    if not models:
        print("Нет моделей для сравнения. Скачайте: ollama pull qwen2.5:3b")
        return 1

    system = SYSTEM_PROMPT.format(actions=", ".join(ACTIONS))

    print(f"Сравниваю {len(models)} модел(и) на {len(TEST_QUESTIONS)} вопросах.")
    print("Первый ответ каждой модели медленный — она грузится в память.\n")

    totals = {}
    for model in models:
        print("=" * 70)
        print(f"  {model}")
        print("=" * 70)
        spent = 0.0
        failed = False
        for question in TEST_QUESTIONS:
            answer, elapsed = ask_model(model, system, question, host=args.host)
            spent += elapsed
            if answer is None:
                print(f"  ! не ответила за {elapsed:.0f} с — модель слишком "
                      "тяжёлая для этой машины")
                failed = True
                break
            print(f"\n  ты:    {question}")
            print(f"  он:    {answer}")
            print(f"         ({elapsed:.1f} с)")
        if not failed:
            totals[model] = spent / len(TEST_QUESTIONS)
        print()

    if totals:
        print("=" * 70)
        print("Среднее время ответа:")
        for model, avg in sorted(totals.items(), key=lambda kv: kv[1]):
            verdict = ("живой разговор" if avg < 3 else
                       "терпимо" if avg < 8 else "слишком медленно")
            print(f"  {model:30} {avg:5.1f} с   {verdict}")
        print()
        print("Качество оцените сами по ответам выше — цифры про скорость,")
        print("а не про ум. Выбранную модель запускайте так:")
        best = min(totals, key=totals.get)
        print("  " + script_cmd("examples/18_ai.py", "--backend", "ollama",
                                 "--model", best))
    return 0


def cmd_build(args) -> int:
    """Собрать свою модель: характер и выученные факты внутри самой модели."""
    if not need_ollama(args.host):
        return 1

    available = [m["name"] for m in list_models(args.host)]
    if not available:
        print("Сначала скачайте базовую модель: ollama pull qwen2.5:3b")
        return 1

    base = args.base
    if base is None:
        # Берём самую маленькую из скачанных — она точно запустится.
        models = sorted(list_models(args.host), key=lambda m: m["size_gb"])
        base = models[0]["name"]
        print(f"Базовая модель не указана, беру самую лёгкую: {base}")
    elif base not in available:
        print(f"Модели {base} нет. Есть: {', '.join(available)}")
        return 1

    memory = Memory()
    system = SYSTEM_PROMPT.format(actions=", ".join(ACTIONS))
    facts = memory.as_text()
    if facts:
        system += "\n\n" + facts

    modelfile = make_modelfile(base, system)

    print(f"\nСобираю модель «{args.name}» на основе {base}")
    print(f"Фактов из памяти вшито: {len(memory.facts)}")
    print()
    print("--- Modelfile ---")
    print(modelfile)
    print("-----------------")

    if args.dry_run:
        print("\n(--dry-run: ничего не создано)")
        return 0

    if not create_model(args.name, modelfile, host=args.host):
        print("Не получилось создать модель.")
        return 1

    print(f"\nГотово. Модель «{args.name}» теперь в списке ollama list.")
    print("Запускать так:")
    print("  " + script_cmd("examples/18_ai.py", "--backend", "ollama",
                            "--model", args.name))
    print()
    print("Пересобирайте её снова, когда научите Козмо новым фактам —")
    print("тогда они окажутся внутри самой модели, а не подставятся сбоку.")
    return 0


def cmd_chat(args) -> int:
    """Поговорить с локальной моделью без робота."""
    if not need_ollama(args.host):
        return 1

    models = [m["name"] for m in list_models(args.host)]
    model = args.model[0] if args.model else (
        OWN_MODEL if any(m.startswith(OWN_MODEL) for m in models)
        else (models[0] if models else None))
    if not model:
        print("Нет ни одной модели.")
        return 1

    system = SYSTEM_PROMPT.format(actions=", ".join(ACTIONS))
    print(f"Говорю с {model}. «выход» — закончить.\n")
    while True:
        try:
            question = input("ты > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in ("выход", "quit", "exit", ""):
            break
        answer, elapsed = ask_model(model, system, question, host=args.host)
        print(f"Козмо > {answer or '(не ответил)'}   [{elapsed:.1f} с]\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=DEFAULT_HOST, help="адрес Ollama")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("check", help="что установлено и что потянет машина")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("test", help="сравнить модели на русском")
    p.add_argument("--model", nargs="+", help="только эти модели")
    p.set_defaults(func=cmd_test)

    p = sub.add_parser("build", help="собрать свою модель kozmo")
    p.add_argument("--base", help="на основе какой модели")
    p.add_argument("--name", default=OWN_MODEL, help="как назвать свою")
    p.add_argument("--dry-run", action="store_true",
                   help="только показать Modelfile, ничего не создавать")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("chat", help="поговорить без робота")
    p.add_argument("--model", nargs=1, help="какая модель")
    p.set_defaults(func=cmd_chat)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
