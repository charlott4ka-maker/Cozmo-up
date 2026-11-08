"""Синтез русской речи в формат, который принимает Козмо.

Общий модуль: им пользуются и scripts/make_voice.py (заготовить фразы
заранее), и cozmo_up.speech.LiveVoice (озвучить ответ ИИ прямо сейчас).

Движки:
  edge   — голоса Microsoft Edge, лучшее качество, нужен интернет
  espeak — espeak-ng, офлайн, роботизированно (Козмо идёт)
  system — системный синтез через pyttsx3, офлайн
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

#: Русские голоса Microsoft Edge.
EDGE_VOICES = ["ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"]

#: Готовые настройки голоса. pitch в герцах, rate в процентах.
#: espeak_pitch — 0..99, espeak_speed — слов в минуту.
PRESETS = {
    "malchik": {
        "description": "мальчишеский: мужской голос, поднятый по тону",
        "voice": "ru-RU-DmitryNeural", "pitch": "+45Hz", "rate": "+10%",
        "espeak_pitch": 75, "espeak_speed": 165,
    },
    "kozmo": {
        "description": "как настоящий Козмо: высокий, быстрый, мультяшный",
        "voice": "ru-RU-DmitryNeural", "pitch": "+80Hz", "rate": "+22%",
        "espeak_pitch": 90, "espeak_speed": 185,
    },
    "malysh": {
        "description": "совсем малыш: очень высокий и быстрый",
        "voice": "ru-RU-SvetlanaNeural", "pitch": "+100Hz", "rate": "+25%",
        "espeak_pitch": 99, "espeak_speed": 190,
    },
    "devushka": {
        "description": "обычный женский голос",
        "voice": "ru-RU-SvetlanaNeural", "pitch": "+0Hz", "rate": "+0%",
        "espeak_pitch": 50, "espeak_speed": 150,
    },
    "vzroslyj": {
        "description": "обычный мужской голос",
        "voice": "ru-RU-DmitryNeural", "pitch": "+0Hz", "rate": "+0%",
        "espeak_pitch": 40, "espeak_speed": 150,
    },
}

DEFAULT_PRESET = "malchik"


def synth_edge(text: str, out_mp3: Path, voice: str,
               pitch: str = "+0Hz", rate: str = "+0%") -> None:
    """Озвучить через edge-tts (нужен интернет).

    pitch в герцах ("+45Hz"), rate в процентах ("+10%").
    Знак обязателен, иначе edge-tts ругнётся на формат.
    """
    import asyncio

    import edge_tts

    async def run() -> None:
        await edge_tts.Communicate(text, voice, pitch=pitch, rate=rate).save(str(out_mp3))

    asyncio.run(run())


def synth_espeak(text: str, out_wav: Path, speed: int = 150, pitch: int = 50) -> None:
    """Озвучить через espeak-ng (офлайн). pitch 0..99, speed — слов в минуту."""
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not binary:
        raise RuntimeError("espeak-ng не установлен")
    subprocess.run(
        [binary, "-v", "ru", "-s", str(speed), "-p", str(pitch), "-w", str(out_wav), text],
        check=True,
    )


def synth_system(text: str, out_wav: Path) -> None:
    """Озвучить системным синтезатором через pyttsx3 (офлайн)."""
    import pyttsx3

    engine = pyttsx3.init()
    russian = [
        v for v in engine.getProperty("voices")
        if "russian" in v.name.lower() or "irina" in v.name.lower()
        or "milena" in v.name.lower() or "yuri" in v.name.lower()
    ]
    if russian:
        engine.setProperty("voice", russian[0].id)
    engine.save_to_file(text, str(out_wav))
    engine.runAndWait()


class SynthesisError(RuntimeError):
    """Движок синтеза не справился."""


def synthesize(text: str, target: Path, engine: str = "edge",
               settings: dict = None, rate_hz: int = 22050,
               fallback: bool = True, on_fallback=None) -> Path:
    """Озвучить фразу и сохранить WAV в формате робота.

    Движок edge требует интернета, которого в Wi-Fi робота нет. Чтобы
    речь не отваливалась совсем, при его отказе автоматически берётся
    офлайн-движок espeak — голос хуже, но робот продолжает говорить.
    Отключается параметром fallback=False.

    Возвращает путь к готовому файлу.
    """
    settings = settings or PRESETS[DEFAULT_PRESET]
    target = Path(target)

    try:
        return _synthesize_once(text, target, engine, settings, rate_hz)
    except Exception as exc:  # noqa: BLE001
        first = exc
        if not fallback or engine == "espeak":
            raise SynthesisError(f"{engine}: {short_reason(exc)}") from exc

    if on_fallback is not None:
        on_fallback(engine, "espeak")

    try:
        return _synthesize_once(text, target, "espeak", settings, rate_hz)
    except Exception as exc:  # noqa: BLE001
        # Обе причины обязательно рядом: раньше тут была видна только
        # вторая, и настоящая поломка (почему не сработал основной
        # движок) оставалась невидимой.
        raise SynthesisError(
            f"{engine}: {short_reason(first)}; "
            f"запасной espeak: {short_reason(exc)}"
        ) from first


#: Сетевые ошибки приходят огромными трассировками — режем до сути.
_NETWORK_HINTS = (
    "getaddrinfo", "Name or service", "Temporary failure", "nodename",
    "ConnectionError", "Cannot connect", "timed out", "TimeoutError",
    "SSL", "certificate", "Proxy", "proxy", "Forbidden", "refused",
    "NoSuchNode", "Unable to connect",
)


def short_reason(exc: Exception) -> str:
    """Короткая человеческая причина вместо простыни трассировки."""
    text = str(exc).strip().replace("\n", " ")
    name = type(exc).__name__

    if any(hint in text or hint in name for hint in _NETWORK_HINTS):
        return "нет связи с сервером синтеза (интернет?)"
    if not text:
        return name
    return text[:120]


def _synthesize_once(text: str, target: Path, engine: str,
                     settings: dict, rate_hz: int) -> Path:
    """Один заход одним движком, без подстраховки."""
    from .speech import convert

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
            raise RuntimeError(f"Движок {engine} не создал аудио для «{text}»")

        convert(raw, target, rate=rate_hz)

    return target


def list_edge_voices() -> int:
    """Показать все русские голоса, доступные в edge-tts."""
    import asyncio

    import edge_tts

    try:
        voices = asyncio.run(edge_tts.list_voices())
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
