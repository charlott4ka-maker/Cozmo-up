"""Распознавание русской речи для Cozmo.

Важно про железо: **микрофоны самого Козмо недоступны**. В протоколе есть
только пакет `OutputAudio` — звук идёт на робота, но не с него. Так что
слушаем микрофон компьютера.

Движок — Vosk: он работает полностью офлайн. Это принципиально, потому что
во время работы с роботом компьютер сидит в его Wi-Fi, где интернета нет,
и любое облачное распознавание там просто не ответит.

Модель (~45 МБ) скачивается один раз при первом запуске — делать это надо
на обычном Wi-Fi.

Сильно помогает ограничение словаря: если передать список слов, которые мы
вообще ожидаем услышать, Vosk выбирает из них, а не из всего русского языка,
и точность резко растёт.
"""

import json
import queue
import unicodedata
from typing import Iterable, Optional

#: Vosk хочет 16 кГц, моно, 16 бит.
SAMPLE_RATE = 16000

#: Слова, которых НЕТ в маленькой русской модели. Проверено: «козмо»
#: отсутствует, поэтому как обращение оно не годится — берите «робот».
UNKNOWN_WORDS = {"козмо", "cozmo"}


def normalize(text: str) -> str:
    """Привести текст к виду для СРАВНЕНИЯ: нижний регистр, е вместо ё.

    Только для сопоставления с правилами. Для словаря распознавания
    это применять нельзя — см. for_vocabulary().
    """
    text = unicodedata.normalize("NFC", text.strip().lower())
    return text.replace("ё", "е")


def for_vocabulary(text: str) -> str:
    """Привести слово к виду для СЛОВАРЯ Vosk: регистр вниз, но ё сохранить.

    В русской модели Vosk слова записаны с ё: «вперёд» в словаре есть,
    а «вперед» — нет, и такое слово молча выбрасывается из грамматики
    вместе с возможностью его услышать.
    """
    return unicodedata.normalize("NFC", text.strip().lower())


class Listener:
    """Слушает микрофон и возвращает распознанные фразы.

    Пример:
        with Listener(words=["вперед", "стоп"]) as ears:
            text = ears.listen(timeout=5.0)
    """

    def __init__(
        self,
        words: Optional[Iterable[str]] = None,
        model_path: Optional[str] = None,
        device=None,
        block_size: int = 4000,
    ) -> None:
        try:
            from vosk import KaldiRecognizer, Model, SetLogLevel
        except ImportError as exc:
            raise RuntimeError(
                "Нужен пакет vosk: pip install vosk sounddevice"
            ) from exc

        SetLogLevel(-1)

        if model_path:
            model = Model(model_path)
        else:
            # Скачает модель при первом запуске — нужен интернет.
            model = Model(lang="ru")

        if words:
            clean = sorted({for_vocabulary(w) for w in words} - UNKNOWN_WORDS)
            grammar = json.dumps([" ".join(clean), "[unk]"], ensure_ascii=False)
            self.recognizer = KaldiRecognizer(model, SAMPLE_RATE, grammar)
        else:
            self.recognizer = KaldiRecognizer(model, SAMPLE_RATE)

        self.device = device
        self.block_size = block_size
        self._queue: queue.Queue = queue.Queue()
        self._stream = None

    def __enter__(self) -> "Listener":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def start(self) -> None:
        try:
            import sounddevice
        except ImportError as exc:
            raise RuntimeError(
                "Нужен пакет sounddevice: pip install sounddevice"
            ) from exc

        def callback(indata, frames, time_info, status):
            del frames, time_info, status
            self._queue.put(bytes(indata))

        self._stream = sounddevice.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=self.block_size,
            device=self.device,
            dtype="int16",
            channels=1,
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def listen(self, timeout: Optional[float] = None) -> str:
        """Дождаться законченной фразы. Пустая строка — ничего не распознано."""
        import time

        deadline = None if timeout is None else time.time() + timeout

        while True:
            if deadline is not None:
                left = deadline - time.time()
                if left <= 0:
                    return ""
            else:
                left = None

            try:
                data = self._queue.get(timeout=left)
            except queue.Empty:
                return ""

            if self.recognizer.AcceptWaveform(data):
                text = json.loads(self.recognizer.Result()).get("text", "")
                if text.strip():
                    return normalize(text)

    def feed(self, pcm: bytes) -> str:
        """Скормить готовый звук вместо микрофона — удобно для тестов."""
        self.recognizer.AcceptWaveform(pcm)
        return normalize(json.loads(self.recognizer.FinalResult()).get("text", ""))


def list_microphones() -> None:
    """Напечатать доступные микрофоны с их номерами."""
    import sounddevice

    print("Доступные устройства записи:\n")
    for i, dev in enumerate(sounddevice.query_devices()):
        if dev["max_input_channels"] > 0:
            default = " (по умолчанию)" if i == sounddevice.default.device[0] else ""
            print(f"  {i:2}  {dev['name']}{default}")
    print("\nВыбрать другой:  Listener(device=НОМЕР)")
