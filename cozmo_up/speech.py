"""Русская речь для Cozmo.

Родной синтез речи Cozmo русский НЕ поддерживает: в ассетах лежат всего
четыре голоса Acapela — английский, французский, немецкий и японский
(`cozmo_resources/tts/Voices/`). Вдобавок синтез выполнялся в приложении
на телефоне, а pycozmo его вообще не реализует.

Поэтому русский делаем так: заранее генерируем WAV-файлы на компьютере
(`scripts/make_voice.py`) и проигрываем их на роботе через `cli.play_audio()`.

Формат, который принимает робот: WAV, 16 бит, 22050 Гц или 48000 Гц.
`convert()` приводит к нему любой входной файл (mp3, ogg, flac, wav).

Про баг в pycozmo 0.8.0: её u-law кодировщик переполняется на громких
сэмплах (всё, что тише -31612, даёт байт 256) и роняет play_audio с
`ValueError: byte must be in range(0, 256)`. Обычный синтез речи легко
в это попадает. Импорт этого модуля ставит патч `patch_pycozmo_audio()`,
а `convert()` дополнительно ограничивает амплитуду на всякий случай.
"""

import json
import struct
import wave
from pathlib import Path
from typing import Dict, Optional

#: Ниже этого значения u-law кодировщик pycozmo 0.8.0 переполняется.
_SAFE_MIN_SAMPLE = -31612
_SAFE_MAX_SAMPLE = 32767


def patch_pycozmo_audio() -> bool:
    """Починить переполнение в u-law кодировщике pycozmo.

    Формулу не меняем (робот ждёт именно её вариант), только ограничиваем
    результат байтом. Возвращает True, если патч применён.
    """
    import pycozmo.audio as audio

    if getattr(audio, "_cozmo_up_patched", False):
        return False

    original = audio.u_law_encoding

    def safe_u_law_encoding(sample: int) -> int:
        return min(original(sample), 255)

    audio.u_law_encoding = safe_u_law_encoding
    audio._cozmo_up_patched = True

    # bytes_to_cozmo берёт функцию из глобалей модуля, так что подмены
    # имени достаточно — отдельно её патчить не нужно.
    return True


try:
    patch_pycozmo_audio()
except ImportError:  # pycozmo ещё не установлен — не мешаем импорту
    pass

#: Частота дискретизации, которую мы используем. Робот принимает ещё 48000.
COZMO_RATE = 22050

#: Каталог со сгенерированными фразами по умолчанию.
DEFAULT_VOICE_DIR = Path("voices")


def convert(src: str | Path, dst: str | Path, rate: int = COZMO_RATE) -> Path:
    """Привести любой аудиофайл к формату, который понимает Cozmo.

    Требуется пакет `miniaudio` (ставится через pip, системный ffmpeg НЕ нужен).
    """
    try:
        import miniaudio
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Нужен пакет miniaudio: pip install miniaudio"
        ) from exc

    if rate not in (22050, 48000):
        raise ValueError(f"Робот принимает только 22050 или 48000 Гц, передано {rate}")

    decoded = miniaudio.decode_file(
        str(src),
        output_format=miniaudio.SampleFormat.SIGNED16,
        nchannels=1,
        sample_rate=rate,
    )

    # Ограничиваем амплитуду, чтобы не ловить переполнение в кодировщике.
    samples = list(decoded.samples)
    clipped = 0
    for i, value in enumerate(samples):
        if value < _SAFE_MIN_SAMPLE:
            samples[i] = _SAFE_MIN_SAMPLE
            clipped += 1
        elif value > _SAFE_MAX_SAMPLE:
            samples[i] = _SAFE_MAX_SAMPLE
            clipped += 1

    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return dst


class Voice:
    """Набор заранее озвученных русских фраз.

    Пример:
        voice = Voice()                    # читает voices/
        voice.say(cli, "privet")           # проиграет voices/privet.wav
    """

    def __init__(self, directory: str | Path = DEFAULT_VOICE_DIR) -> None:
        self.directory = Path(directory)
        self.texts: Dict[str, str] = {}

        index = self.directory / "index.json"
        if index.is_file():
            self.texts = json.loads(index.read_text(encoding="utf-8"))

    def path(self, key: str) -> Path:
        return self.directory / f"{key}.wav"

    def has(self, key: str) -> bool:
        return self.path(key).is_file()

    def keys(self) -> list:
        return sorted(p.stem for p in self.directory.glob("*.wav"))

    def text(self, key: str) -> Optional[str]:
        """Текст фразы — удобно показать его на экране вместе со звуком."""
        return self.texts.get(key)

    def say(self, cli, key: str) -> None:
        """Проиграть фразу на роботе.

        Блокирует до конца проигрывания, потому что робот отвалится,
        если перестать с ним общаться дольше 5 секунд.
        """
        path = self.path(key)
        if not path.is_file():
            raise FileNotFoundError(
                f"Нет файла {path}. Сгенерируйте фразы: python scripts/make_voice.py"
            )
        cli.play_audio(str(path))

    def say_and_show(self, cli, key: str) -> None:
        """Проиграть фразу и одновременно показать её текст на экране."""
        from . import screen

        text = self.text(key)
        if text:
            cli.display_image(screen.render_text(text))
        self.say(cli, key)


def duration(path: str | Path) -> float:
    """Длительность WAV-файла в секундах."""
    with wave.open(str(path), "r") as w:
        return w.getnframes() / w.getframerate()


class LiveVoice:
    """Озвучка на лету: для ответов ИИ, которых заранее нет.

    Синтезирует фразу при первом появлении и кладёт в кэш, так что
    повторы произносятся мгновенно.

    Движок edge требует интернета. В Wi-Fi робота его нет, поэтому
    раздайте интернет с телефона по USB — либо берите engine="espeak",
    он работает офлайн.
    """

    def __init__(self, engine: str = "edge", preset: str = None,
                 cache_dir: str | Path = "voices/cache") -> None:
        from . import tts

        self.engine = engine
        self.settings = tts.PRESETS[preset or tts.DEFAULT_PRESET]
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._tts = tts

    def path_for(self, text: str) -> Path:
        import hashlib

        digest = hashlib.sha1(text.strip().lower().encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / f"{digest}.wav"

    def prepare(self, text: str) -> Path:
        """Получить WAV для фразы, синтезировав при необходимости."""
        target = self.path_for(text)
        if not target.is_file():
            self._tts.synthesize(text, target, engine=self.engine,
                                 settings=self.settings, rate_hz=COZMO_RATE)
        return target

    def say(self, cli, text: str) -> None:
        """Произнести фразу на роботе."""
        text = text.strip()
        if not text:
            return
        cli.play_audio(str(self.prepare(text)))

    def say_and_show(self, cli, text: str) -> None:
        """Произнести и показать текст на экране."""
        from . import screen

        text = text.strip()
        if not text:
            return
        cli.display_image(screen.render_text(text[:40]))
        self.say(cli, text)
