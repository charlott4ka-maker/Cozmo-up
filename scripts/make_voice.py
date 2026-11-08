#!/usr/bin/env python
"""Сгенерировать русские фразы для Cozmo.

Читает phrases.ru.json и складывает готовые WAV-файлы в voices/
в формате, который принимает робот (16 бит, 22050 Гц, моно).

ЗАПУСКАТЬ ПРИ ИНТЕРНЕТЕ, до подключения к Wi-Fi робота
(в сети Cozmo интернета нет).

Движки:
  edge   — голоса Microsoft Edge: лучшее качество русского, нужен интернет.
           pip install edge-tts miniaudio
  espeak — espeak-ng: работает офлайн, звучит роботизированно
           (для Козмо это, впрочем, даже в тему).
           Linux: sudo apt install espeak-ng
           macOS: brew install espeak-ng
           Windows: https://github.com/espeak-ng/espeak-ng/releases
  system — системный синтез (SAPI5 на Windows, NSSpeech на macOS).
           pip install pyttsx3 ; нужен установленный русский голос.

Голос выбирается пресетом --preset:
  malchik  — мальчишеский (по умолчанию)
  kozmo    — как настоящий Козмо: высокий, быстрый, мультяшный
  malysh   — совсем малыш
  vzroslyj — обычный мужской
  devushka — обычный женский

Примеры:
  python scripts/make_voice.py --force
  python scripts/make_voice.py --preset kozmo --force
  python scripts/make_voice.py --list-presets
  python scripts/make_voice.py --list-voices
  python scripts/make_voice.py --pitch +60Hz --rate +15%% --force
  python scripts/make_voice.py --text "Привет мир" --key privet
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.cli import script_cmd  # noqa: E402
from cozmo_up.speech import COZMO_RATE, duration  # noqa: E402
from cozmo_up.tts import (  # noqa: E402
    DEFAULT_PRESET, EDGE_VOICES, PRESETS, list_edge_voices, synthesize,
)

ROOT = Path(__file__).resolve().parent.parent
PHRASES_FILE = ROOT / "phrases.ru.json"
VOICE_DIR = ROOT / "voices"

def make_one(key: str, text: str, engine: str, settings: dict, outdir: Path) -> Path:
    """Озвучить одну фразу и положить в outdir/<key>.wav."""
    return synthesize(text, outdir / f"{key}.wav", engine=engine,
                      settings=settings, rate_hz=COZMO_RATE)


def diagnose() -> int:
    """Проверить по шагам, что мешает озвучке."""
    import shutil
    import socket
    import tempfile

    from cozmo_up.tts import PRESETS, short_reason, synthesize

    print("Проверяю озвучку")
    print(f"Папка: {Path.cwd()}\n")
    problems = []

    # 1. Интернет вообще
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=4).close()
        print("[ OK ]  интернет есть")
        online = True
    except OSError:
        print("[FAIL]  интернета нет")
        print("        вы не в Wi-Fi робота? там интернета не бывает")
        problems.append("интернет")
        online = False

    # 2. Движок edge
    if online:
        tmp = Path(tempfile.mkdtemp()) / "edge.wav"
        try:
            synthesize("проверка", tmp, engine="edge",
                       settings=PRESETS[DEFAULT_PRESET], fallback=False)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL]  edge не работает: {short_reason(exc)}")
            problems.append("edge")
        else:
            print("[ OK ]  edge работает — голос будет хороший")
    else:
        print("[ -- ]  edge пропущен, он требует интернета")

    # 3. Движок espeak
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not binary:
        print("[FAIL]  espeak-ng не установлен")
        print("        Windows: https://github.com/espeak-ng/espeak-ng/releases")
        print("                 скачайте espeak-ng-X.Y.msi и установите,")
        print("                 потом ЗАКРОЙТЕ и откройте PowerShell заново")
        print("        macOS:   brew install espeak-ng")
        print("        Linux:   sudo apt install espeak-ng")
        problems.append("espeak")
    else:
        tmp = Path(tempfile.mkdtemp()) / "espeak.wav"
        try:
            synthesize("проверка", tmp, engine="espeak",
                       settings=PRESETS[DEFAULT_PRESET], fallback=False)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL]  espeak найден ({binary}), но не работает: "
                  f"{short_reason(exc)}")
            problems.append("espeak")
        else:
            print(f"[ OK ]  espeak работает ({binary}) — голос роботичный, "
                  "зато офлайн")

    print()
    if "edge" not in problems and "интернет" not in problems:
        if "espeak" in problems:
            print("Озвучка работает, пока есть интернет. Запускайте:")
        else:
            print("Всё хорошо. Запускайте:")
        print("  " + script_cmd("scripts/make_voice.py",
                                "--preset", "kozmo", "--force"))
        if "espeak" in problems:
            print()
            print("Но в Wi-Fi робота интернета нет, и там голос работать не будет.")
            print("Поставьте espeak-ng по ссылке выше — он озвучивает офлайн,")
            print("и речь перестанет зависеть от сети совсем.")
    elif "espeak" not in problems:
        print("Интернета нет, но espeak работает. Запускайте офлайн:")
        print("  " + script_cmd("scripts/make_voice.py", "--engine", "espeak",
                                "--preset", "kozmo", "--force"))
    else:
        print("Озвучить пока нечем. Нужно либо вернуть интернет,")
        print("либо поставить espeak-ng по ссылке выше.")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", choices=["edge", "espeak", "system"], default="edge",
                        help="движок синтеза (по умолчанию edge)")
    parser.add_argument("--preset", choices=sorted(PRESETS), default=DEFAULT_PRESET,
                        help="готовая настройка голоса (по умолчанию "
                             f"{DEFAULT_PRESET}: {PRESETS[DEFAULT_PRESET]['description']})")
    parser.add_argument("--voice", default=None,
                        help=f"переопределить голос edge-tts, например {' или '.join(EDGE_VOICES)}")
    parser.add_argument("--pitch", default=None,
                        help="переопределить высоту тона, например +60Hz или -20Hz")
    parser.add_argument("--rate", default=None,
                        help="переопределить скорость речи, например +15%% или -10%%")
    parser.add_argument("--list-voices", action="store_true",
                        help="показать все русские голоса edge-tts и выйти")
    parser.add_argument("--list-presets", action="store_true",
                        help="показать готовые настройки голоса и выйти")
    parser.add_argument("--diagnose", action="store_true",
                        help="проверить, что мешает озвучке, и выйти")
    parser.add_argument("--phrases", type=Path, default=PHRASES_FILE,
                        help="JSON с фразами {ключ: текст}")
    parser.add_argument("--outdir", type=Path, default=VOICE_DIR,
                        help="куда класть WAV-файлы")
    parser.add_argument("--text", help="озвучить одну фразу вместо файла")
    parser.add_argument("--key", help="ключ (имя файла) для --text")
    parser.add_argument("--force", action="store_true",
                        help="перегенерировать уже существующие файлы")
    args = parser.parse_args()

    if args.list_presets:
        print("Готовые настройки голоса (--preset):\n")
        for name, cfg in PRESETS.items():
            mark = " (по умолчанию)" if name == DEFAULT_PRESET else ""
            print(f"  {name:10} {cfg['description']}{mark}")
            print(f"             edge: {cfg['voice']}, тон {cfg['pitch']}, "
                  f"скорость {cfg['rate']}")
        return 0

    if args.list_voices:
        return list_edge_voices()

    if args.diagnose:
        return diagnose()

    # Пресет + возможные переопределения отдельными флагами.
    settings = dict(PRESETS[args.preset])
    if args.voice:
        settings["voice"] = args.voice
    if args.pitch:
        settings["pitch"] = args.pitch
    if args.rate:
        settings["rate"] = args.rate

    if args.text:
        if not args.key:
            parser.error("с --text нужно указать --key")
        phrases = {args.key: args.text}
    else:
        if not args.phrases.is_file():
            print(f"Нет файла с фразами: {args.phrases}")
            return 1
        phrases = json.loads(args.phrases.read_text(encoding="utf-8"))

    args.outdir.mkdir(parents=True, exist_ok=True)

    print(f"Движок: {args.engine}, пресет: {args.preset} "
          f"({PRESETS[args.preset]['description']})")
    if args.engine == "edge":
        print(f"Голос: {settings['voice']}, тон {settings['pitch']}, "
              f"скорость {settings['rate']}")
    else:
        print(f"Тон: {settings['espeak_pitch']}/99, "
              f"скорость: {settings['espeak_speed']} слов/мин")
    print(f"Фраз: {len(phrases)}  ->  {args.outdir}/\n")

    made, skipped, failed = 0, 0, 0
    for key, text in phrases.items():
        target = args.outdir / f"{key}.wav"
        if target.is_file() and not args.force:
            print(f"  = {key:14} уже есть (--force чтобы перезаписать)")
            skipped += 1
            continue
        try:
            make_one(key, text, args.engine, settings, args.outdir)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {key:14} ОШИБКА: {exc}")
            failed += 1
            continue
        print(f"  + {key:14} {duration(target):4.1f} с  «{text}»")
        made += 1

    # index.json — чтобы Voice.text() могла показать фразу на экране.
    index_path = args.outdir / "index.json"
    index = {}
    if index_path.is_file():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    index.update(phrases)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2),
                          encoding="utf-8")

    print(f"\nГотово: создано {made}, пропущено {skipped}, ошибок {failed}")

    if failed:
        print()
        print("Ни одна фраза не озвучилась. Что делать:")
        print()
        if args.engine == "edge":
            print("  Движок edge работает по интернету. Проверьте:")
            print("    • вы не в Wi-Fi робота? там интернета нет")
            print("    • интернет вообще есть? откройте любой сайт")
            print()
        print("  Запасной движок espeak работает офлайн, но его надо поставить:")
        print("    Windows: https://github.com/espeak-ng/espeak-ng/releases")
        print("             скачайте espeak-ng-X.Y.msi, установите,")
        print("             потом ЗАКРОЙТЕ и откройте PowerShell заново")
        print("    macOS:   brew install espeak-ng")
        print("    Linux:   sudo apt install espeak-ng")
        print()
        print("  Проверить, что именно не так:")
        print("    " + script_cmd("scripts/make_voice.py", "--diagnose"))

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
