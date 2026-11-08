"""Работа с локальным ИИ через Ollama: какие модели есть, своя модель, сравнение.

Ollama — программа, которая крутит языковые модели прямо на вашем
компьютере. Никакого интернета, никаких ключей, никакой оплаты за слова.
Модель живёт у вас на диске, и это правда ваш ИИ.

Главное ограничение — железо. Модель целиком грузится в память, и чем
она больше, тем умнее и медленнее. Без видеокарты всё считает процессор,
и это терпимо для маленьких моделей и мучительно для больших.
"""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional

DEFAULT_HOST = "http://127.0.0.1:11434"

#: Имя своей модели, которую собирает make_model.
OWN_MODEL = "kozmo"

#: Ориентир по размеру модели. Числа — сколько свободной памяти
#: нужно, чтобы она не начала задыхаться.
SIZE_GUIDE = [
    (3, "модели на 1-2 млрд параметров (:1b, :2b) — быстро, но глуповато"),
    (6, "модели на 3-4 млрд (:3b, :4b) — разумный минимум для разговора"),
    (10, "модели на 7-9 млрд (:7b, :8b, :9b) — заметно умнее"),
    (999, "модели на 12 млрд и больше — если есть видеокарта"),
]


def ollama_request(path: str, payload: dict = None, host: str = DEFAULT_HOST,
                   timeout: float = 120.0) -> Optional[dict]:
    """Запрос к Ollama. None, если он не отвечает."""
    url = f"{host.rstrip('/')}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError:
        return None


def is_running(host: str = DEFAULT_HOST) -> bool:
    """Запущена ли Ollama."""
    return ollama_request("/api/tags", host=host) is not None


def list_models(host: str = DEFAULT_HOST) -> List[dict]:
    """Какие модели уже скачаны. [{name, size_gb, parameter_size}]"""
    data = ollama_request("/api/tags", host=host)
    if not data:
        return []
    models = []
    for item in data.get("models", []):
        details = item.get("details") or {}
        models.append({
            "name": item.get("name", "?"),
            "size_gb": round(item.get("size", 0) / 1e9, 1),
            "parameter_size": details.get("parameter_size", "?"),
        })
    return sorted(models, key=lambda m: m["name"])


def free_memory_gb() -> Optional[float]:
    """Сколько оперативной памяти свободно. None, если не удалось узнать."""
    try:
        import shutil  # noqa: F401  (проверяем наличие stdlib)
    except ImportError:
        return None

    # Windows
    try:
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return round(status.ullAvailPhys / 1e9, 1)
    except (AttributeError, OSError):
        pass

    # Linux
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return round(int(line.split()[1]) * 1024 / 1e9, 1)

    # macOS
    try:
        import subprocess

        out = subprocess.run(["sysctl", "-n", "hw.memsize"],
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            # Свободную на macOS быстро не узнать — берём половину общей.
            return round(int(out.stdout.strip()) / 1e9 / 2, 1)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass

    return None


def size_advice(free_gb: Optional[float]) -> str:
    """Что посоветовать по памяти."""
    if free_gb is None:
        return "Не удалось определить объём свободной памяти."
    for limit, text in SIZE_GUIDE:
        if free_gb < limit:
            return f"Свободно {free_gb} ГБ — вам подойдут {text}."
    return f"Свободно {free_gb} ГБ — подойдёт почти всё."


def make_modelfile(base: str, system: str, temperature: float = 0.7,
                   num_predict: int = 200) -> str:
    """Собрать Modelfile — рецепт своей модели поверх базовой."""
    escaped = system.replace('"""', '\\"\\"\\"')
    return (
        f"FROM {base}\n\n"
        f'SYSTEM """{escaped}"""\n\n'
        f"PARAMETER temperature {temperature}\n"
        f"PARAMETER num_predict {num_predict}\n"
        # Козмо отвечает коротко — длинный контекст ему не нужен,
        # а памяти он ест заметно.
        f"PARAMETER num_ctx 4096\n"
    )


def create_model(name: str, modelfile: str, host: str = DEFAULT_HOST) -> bool:
    """Создать свою модель в Ollama из рецепта."""
    result = ollama_request("/api/create",
                            {"model": name, "modelfile": modelfile, "stream": False},
                            host=host, timeout=600.0)
    return result is not None


def ask_model(model: str, system: str, question: str,
              host: str = DEFAULT_HOST, timeout: float = 180.0) -> tuple:
    """Спросить модель. Возвращает (ответ, секунд). Ответ None при ошибке."""
    start = time.time()
    data = ollama_request(
        "/api/chat",
        {"model": model, "system": system, "stream": False,
         "messages": [{"role": "user", "content": question}],
         "options": {"temperature": 0.7, "num_predict": 200}},
        host=host, timeout=timeout,
    )
    elapsed = time.time() - start
    if not data:
        return None, elapsed
    return (data.get("message") or {}).get("content", "").strip(), elapsed
