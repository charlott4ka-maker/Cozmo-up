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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.speech import COZMO_RATE, convert, duration  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PHRASES_FILE = ROOT / "phrases.ru.json"
VOICE_DIR = ROOT / "voices"

#: Русские голоса Microsoft Edge.
EDGE_VOICES = ["ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"]

#: Готовые настройки голоса. Выбираются флагом --preset.
#: pitch в герцах, rate в процентах к обычной скорости.
#: espeak_pitch — 0..99 (по умолчанию 50), espeak_speed — слов в минуту.
PRESETS = {
    "malchik": {
        "description": "мальчишеский: мужской голос, поднятый по тону",
        "voice": "ru-RU-DmitryNeural",
        "pitch": "+45Hz",
        "rate": "+10%",
        "espeak_pitch": 75,
        "espeak_speed": 165,
    },
    "kozmo": {
        "description": "как настоящий Козмо: высокий, быстрый, мультяшный",
        "voice": "ru-RU-DmitryNeural",
        "pitch": "+80Hz",
        "rate": "+22%",
        "espeak_pitch": 90,
        "espeak_speed": 185,
    },
    "malysh": {
        "description": "совсем малыш: очень высокий и быстрый",
        "voice": "ru-RU-SvetlanaNeural",
        "pitch": "+100Hz",
        "rate": "+25%",
        "espeak_pitch": 99,
        "espeak_speed": 190,
    },
    "devushka": {
        "description": "обычный женский голос (как было)",
        "voice": "ru-RU-SvetlanaNeural",
        "pitch": "+0Hz",
        "rate": "+0%",
        "espeak_pitch": 50,
        "espeak_speed": 150,
    },
    "vzroslyj": {
        "description": "обычный мужской голос",
        "voice": "ru-RU-DmitryNeural",
        "pitch": "+0Hz",
        "rate": "+0%",
        "espeak_pitch": 40,
        "espeak_speed": 150,
    },
}

DEFAULT_PRESET = "malchik"


def synth_edge(text: str, out_mp3: Path, voice: str,
               pitch: str = "+0Hz", rate: str = "+0%") -> None:
    """Озвучить через edge-tts (нужен интернет).

    pitch задаётся в герцах ("+45Hz"), rate — в процентах ("+10%").
    Плюс обязателен, иначе edge-tts ругнётся на формат.
    """
    import asyncio

    import edge_tts

    async def run() -> None:
        communicate = edge_tts.Communicate(text, voice, pitch=pitch, rate=rate)
        await communicate.save(str(out_mp3))

    asyncio.run(run())


def list_edge_voices() -> int:
    """Показать все русские голоса, доступные в edge-tts."""
    import asyncio

    import edge_tts

    async def run() -> list:
        return await edge_tts.list_voices()

    try:
        voices = asyncio.run(run())
    except Exception as exc:  # noqa: BLE001
        print(f"Не удалось получить список голосов: {exc}")
        print("Нужен интернет — возможно, вы в Wi-Fi робота.")
        return 1

    russian = sorted((v for v in voices if v["Locale"].startswith("ru")),
                     key=lambda v: v["ShortName"])
    if not russian:
        print("Русские голоса не найдены.")
        return 1

    print("Русские голоса edge-tts:\n")
    for v in russian:
        gender = {"Male": "мужской", "Female": "женский"}.get(v["Gender"], v["Gender"])
        print(f"  {v['ShortName']:28} {gender}")
    print("\nИспользовать:  --voice ru-RU-DmitryNeural")
    return 0


def synth_espeak(text: str, out_wav: Path, speed: int = 150,
                 pitch: int = 50) -> None:
    """Озвучить через espeak-ng (офлайн). pitch 0..99, speed — слов в минуту."""
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not binary:
        raise RuntimeError(
            "espeak-ng не найден.\n"
            "  Linux:   sudo apt install espeak-ng\n"
            "  macOS:   brew install espeak-ng\n"
            "  Windows: https://github.com/espeak-ng/espeak-ng/releases"
        )
    subprocess.run(
        [binary, "-v", "ru", "-s", str(speed), "-p", str(pitch),
         "-w", str(out_wav), text],
        check=True,
    )


def synth_system(text: str, out_wav: Path) -> None:
    """Озвучить системным синтезатором через pyttsx3 (офлайн)."""
    import pyttsx3

    engine = pyttsx3.init()
    russian = [v for v in engine.getProperty("voices")
               if "ru" in (getattr(v, "languages", []) or [""])[0].__str__().lower()
               or "russian" in v.name.lower()
               or "irina" in v.name.lower()
               or "milena" in v.name.lower()
               or "yuri" in v.name.lower()]
    if russian:
        engine.setProperty("voice", russian[0].id)
    else:
        print("  ВНИМАНИЕ: русский системный голос не найден, "
              "произношение будет неправильным.")
    engine.save_to_file(text, str(out_wav))
    engine.runAndWait()


def make_one(key: str, text: str, engine: str, settings: dict, outdir: Path) -> Path:
    target = outdir / f"{key}.wav"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        if engine == "edge":
            raw = tmp_path / "raw.mp3"
            synth_edge(text, raw, settings["voice"],
                       pitch=settings["pitch"], rate=settings["rate"])
        elif engine == "espeak":
            raw = tmp_path / "raw.wav"
            synth_espeak(text, raw, speed=settings["espeak_speed"],
                         pitch=settings["espeak_pitch"])
        elif engine == "system":
            raw = tmp_path / "raw.wav"
            synth_system(text, raw)
        else:
            raise ValueError(f"Неизвестный движок: {engine}")

        if not raw.is_file() or raw.stat().st_size == 0:
            raise RuntimeError(f"Движок {engine} не создал аудио для '{text}'")

        # Приводим к формату робота: 16 бит, 22050 Гц, моно.
        convert(raw, target, rate=COZMO_RATE)

    return target


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
    if failed and args.engine == "edge":
        print("Если ошибки сетевые — вы, возможно, уже в Wi-Fi робота "
              "(там нет интернета).")
        print("Вернитесь в обычную сеть или используйте --engine espeak.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
