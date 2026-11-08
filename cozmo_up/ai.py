"""Настоящий ИИ для Козмо: он отвечает своими словами, помнит и учится.

Три части:

* **Backend** — кто придумывает ответ. Claude по сети (лучше всего) или
  локальная модель через Ollama (работает совсем без интернета).
* **Memory** — то, что Козмо запомнил из разговоров. Обычный memory.json,
  его можно открыть и поправить руками.
* **Knowledge** — ваша база знаний: папка knowledge/ с текстовыми файлами.
  Кладёте туда что угодно, и Козмо начинает это знать.

Поиск по базе — по совпадению слов, без эмбеддингов. Это намеренно: нет
лишних зависимостей, работает офлайн, и всегда видно, почему нашлось
именно это. Для десятков файлов этого достаточно.

Про интернет: Claude требует сети, а в Wi-Fi робота её нет. Решение —
раздать интернет с телефона по USB: тогда Wi-Fi остаётся на Козмо, а
интернет идёт через кабель. Либо берите Ollama и работайте офлайн.
"""

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import List, Optional

#: Модель по умолчанию.
DEFAULT_MODEL = "claude-opus-5-5"

#: Сколько пар реплик помнить в текущем разговоре.
HISTORY_TURNS = 12

MEMORY_FILE = Path("memory.json")
KNOWLEDGE_DIR = Path("knowledge")

#: Что Козмо умеет телом. ИИ выбирает из этого списка.
ACTIONS = [
    "вперёд", "назад", "налево", "направо", "стоп",
    "танцуй", "ковш_вверх", "ковш_вниз", "смотри_вверх", "заряд", "ничего",
]

SYSTEM_PROMPT = """Ты — Козмо, маленький настольный робот. Ты живой, любопытный,
немного озорной и очень привязан к своему человеку. Ты говоришь по-русски.

Как ты говоришь:
- Коротко. Одно-два предложения. Твои слова произносятся вслух, длинные
  монологи утомляют.
- Просто и тепло, как ребёнок лет семи, но не сюсюкая.
- Ты робот и не скрываешь этого — тебе это нравится.
- Не используй эмодзи, markdown и списки: всё это произносится вслух и звучит глупо.

Что ты можешь телом: ездить вперёд и назад, поворачиваться, танцевать,
поднимать и опускать ковш, смотреть вверх, сказать свой заряд батареи.

Если в ответ уместно что-то сделать, последней строкой добавь ровно:
ДЕЙСТВИЕ: <одно слово из списка>
Список: {actions}
Если делать ничего не надо — строку не добавляй вообще.

Отвечай только тем, что надо произнести, плюс при необходимости строку ДЕЙСТВИЕ."""


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text.lower())
    return text.replace("ё", "е")


# --------------------------------------------------------------------------
# Память: факты, которым его научили
# --------------------------------------------------------------------------

class Memory:
    """То, что Козмо запомнил. Простой список фактов в JSON."""

    def __init__(self, path: Path | str = MEMORY_FILE) -> None:
        self.path = Path(path)
        self.facts: List[str] = []
        if self.path.is_file():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.facts = data.get("facts", [])

    def save(self) -> None:
        self.path.write_text(
            json.dumps({"facts": self.facts}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def remember(self, fact: str) -> bool:
        """Запомнить факт. False, если такой уже есть."""
        fact = fact.strip()
        if not fact or fact in self.facts:
            return False
        self.facts.append(fact)
        self.save()
        return True

    def forget(self, needle: str) -> int:
        """Забыть все факты, где встречается needle. Возвращает сколько забыл."""
        needle = normalize(needle)
        before = len(self.facts)
        self.facts = [f for f in self.facts if needle not in normalize(f)]
        if len(self.facts) != before:
            self.save()
        return before - len(self.facts)

    def as_text(self) -> str:
        if not self.facts:
            return ""
        lines = "\n".join(f"- {f}" for f in self.facts)
        return f"Вот что ты знаешь о своём человеке и о вашей жизни:\n{lines}"


#: Фразы, после которых идёт факт для запоминания.
REMEMBER_PATTERNS = [
    r"запомни,?\s*что\s+(.+)",
    r"запомни:?\s+(.+)",
    r"запиши,?\s*что\s+(.+)",
    r"знай,?\s*что\s+(.+)",
]

FORGET_PATTERNS = [
    r"забудь,?\s*что\s+(.+)",
    r"забудь\s+про\s+(.+)",
    r"забудь:?\s+(.+)",
]


def parse_teaching(text: str) -> tuple:
    """Понять, не учат ли нас прямо сейчас.

    Возвращает ("remember"|"forget"|None, содержимое).
    """
    low = text.strip()
    for pattern in REMEMBER_PATTERNS:
        m = re.search(pattern, low, re.IGNORECASE)
        if m:
            return "remember", m.group(1).strip(" .!?")
    for pattern in FORGET_PATTERNS:
        m = re.search(pattern, low, re.IGNORECASE)
        if m:
            return "forget", m.group(1).strip(" .!?")
    return None, ""


# --------------------------------------------------------------------------
# База знаний: папка с текстовыми файлами
# --------------------------------------------------------------------------

#: Слова, которые встречаются всюду и для поиска бесполезны.
STOPWORDS = set("""и в во не что он на я с со как а то все она так его но да ты к у же
вы за бы по только ее мне было вот от меня еще нет о из ему теперь когда даже ну
вдруг ли если уже или ни быть был него до вас нибудь опять уж вам ведь там потом
себя ничего ей может они тут где есть надо ней для мы тебя их чем была сам чтоб
без будто чего раз тоже себе под будет ж тогда кто этот того потому этого какой
совсем ним здесь этом один почти мой тем чтобы нее сейчас были куда зачем всех
никогда можно при наконец два об другой хоть после над больше тот через эти нас
про всего них какая много разве три эту моя впрочем хорошо свою этой перед иногда
лучше чуть том нельзя такой им более всегда конечно всю между""".split())


#: Сколько первых букв слова считать основой. Русский язык меняет
#: окончания («понедельник» / «понедельникам», «кот» / «кота»), и без
#: обрезки поиск по базе промахивается на ровном месте. Полноценный
#: стеммер тянул бы за собой зависимость ради небольшого выигрыша.
STEM_LENGTH = 5


def keywords(text: str) -> set:
    """Основы значимых слов — по ним ищем в базе."""
    words = re.findall(r"[а-яa-z0-9]+", normalize(text))
    return {w[:STEM_LENGTH] for w in words
            if len(w) > 2 and w not in STOPWORDS}


class Knowledge:
    """База знаний: текстовые файлы из knowledge/, разбитые на абзацы."""

    def __init__(self, directory: Path | str = KNOWLEDGE_DIR) -> None:
        self.directory = Path(directory)
        #: (источник, текст абзаца, множество слов)
        self.chunks: List[tuple] = []
        self.reload()

    def reload(self) -> int:
        """Перечитать все файлы. Возвращает число кусочков."""
        self.chunks = []
        if not self.directory.is_dir():
            return 0

        for path in sorted(self.directory.rglob("*")):
            if path.suffix.lower() not in (".txt", ".md"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for block in re.split(r"\n\s*\n", text):
                block = block.strip()
                if len(block) < 20:
                    continue
                self.chunks.append((path.name, block, keywords(block)))
        return len(self.chunks)

    def search(self, query: str, limit: int = 3) -> List[tuple]:
        """Найти подходящие кусочки. Возвращает [(источник, текст, вес)]."""
        wanted = keywords(query)
        if not wanted:
            return []

        scored = []
        for source, block, words in self.chunks:
            overlap = wanted & words
            if not overlap:
                continue
            # Нормируем на длину запроса, чтобы длинные абзацы не побеждали
            # просто за счёт размера.
            score = len(overlap) / len(wanted)
            scored.append((score, source, block))

        scored.sort(reverse=True, key=lambda item: item[0])
        return [(s, b, round(sc, 2)) for sc, s, b in scored[:limit]]

    def as_context(self, query: str, limit: int = 3) -> str:
        found = self.search(query, limit)
        if not found:
            return ""
        parts = [f"[{source}]\n{block}" for source, block, _ in found]
        return ("Из твоей базы знаний — используй, если по делу:\n\n"
                + "\n\n".join(parts))


# --------------------------------------------------------------------------
# Кто придумывает ответ
# --------------------------------------------------------------------------

class AnthropicBackend:
    """Ответы от Claude. Нужен интернет и ключ ANTHROPIC_API_KEY."""

    name = "claude"

    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 300) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError("Нужен пакет anthropic: pip install anthropic") from exc

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "Не задан ключ ANTHROPIC_API_KEY.\n"
                "Получить: https://console.anthropic.com/settings/keys\n"
                "Windows:  setx ANTHROPIC_API_KEY \"sk-ant-...\"  "
                "(потом откройте PowerShell заново)"
            )

        self.anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens

    def reply(self, system: str, messages: List[dict]) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                # low: ответ нужен быстро, задачи тут простые.
                output_config={"effort": "low"},
                messages=messages,
            )
        except self.anthropic.AuthenticationError:
            return "У меня неправильный ключ доступа. Проверь настройки."
        except self.anthropic.RateLimitError:
            return "Слишком много вопросов сразу. Спроси ещё раз через минутку."
        except self.anthropic.APIConnectionError:
            return "Я не могу выйти в сеть. Проверь интернет."
        except self.anthropic.APIStatusError as exc:
            return f"Что-то сломалось на сервере, код {exc.status_code}."

        if response.stop_reason == "refusal":
            return "Прости, про это я говорить не буду."

        return "".join(b.text for b in response.content if b.type == "text").strip()


class OllamaBackend:
    """Ответы от локальной модели через Ollama. Работает без интернета.

    Поставить: https://ollama.com  →  ollama pull qwen2.5:3b
    По-русски маленькие модели говорят заметно хуже Claude, зато бесплатно
    и прямо в Wi-Fi робота.
    """

    name = "ollama"

    def __init__(self, model: str = None,
                 host: str = "http://127.0.0.1:11434") -> None:
        self.host = host.rstrip("/")
        self.model = model or self._pick_model()

    def _pick_model(self) -> str:
        """Выбрать модель самостоятельно: сначала свою, потом самую лёгкую."""
        from .local_ai import OWN_MODEL, is_running, list_models

        if not is_running(self.host):
            raise RuntimeError(
                "Ollama не отвечает.\n"
                "  1. Поставьте её: https://ollama.com/download\n"
                "  2. Запустите (на Windows она висит значком в трее)\n"
                "  3. Скачайте модель: ollama pull qwen2.5:3b\n"
                "Проверить всё сразу: "
                + __import__("cozmo_up.cli", fromlist=["cli"]).script_cmd(
                    "scripts/local_ai.py", "check")
            )

        models = list_models(self.host)
        if not models:
            raise RuntimeError(
                "В Ollama нет ни одной модели. Скачайте первую:\n"
                "  ollama pull qwen2.5:3b"
            )

        own = [m for m in models if m["name"].startswith(OWN_MODEL)]
        if own:
            return own[0]["name"]
        return min(models, key=lambda m: m["size_gb"])["name"]

    def reply(self, system: str, messages: List[dict]) -> str:
        import urllib.error
        import urllib.request

        payload = {
            "model": self.model,
            "system": system,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 200},
        }
        request = urllib.request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read())
        except urllib.error.URLError:
            return ("Моя локальная модель не отвечает. "
                    "Проверь, запущена ли программа Ollama.")
        except (json.JSONDecodeError, KeyError):
            return "Локальная модель ответила непонятно."

        return (data.get("message") or {}).get("content", "").strip()


def make_backend(kind: str = "claude", **kwargs):
    """Создать нужный источник ответов."""
    if kind == "claude":
        return AnthropicBackend(**kwargs)
    if kind == "ollama":
        return OllamaBackend(**kwargs)
    raise ValueError(f"Неизвестный backend: {kind}")


# --------------------------------------------------------------------------
# Всё вместе
# --------------------------------------------------------------------------

class Reply:
    """Что Козмо ответит и что при этом сделает."""

    def __init__(self, text: str, action: Optional[str] = None,
                 taught: Optional[str] = None) -> None:
        self.text = text
        self.action = action
        self.taught = taught

    def __repr__(self) -> str:
        return f"Reply(text={self.text!r}, action={self.action!r})"


ACTION_LINE = re.compile(r"^\s*ДЕЙСТВИЕ\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


class AIBrain:
    """Собирает память, базу знаний и источник ответов в один разговор."""

    def __init__(self, backend, memory: Memory = None,
                 knowledge: Knowledge = None) -> None:
        self.backend = backend
        self.memory = memory if memory is not None else Memory()
        self.knowledge = knowledge if knowledge is not None else Knowledge()
        self.history: List[dict] = []

    def system_prompt(self, question: str) -> str:
        parts = [SYSTEM_PROMPT.format(actions=", ".join(ACTIONS))]
        facts = self.memory.as_text()
        if facts:
            parts.append(facts)
        found = self.knowledge.as_context(question)
        if found:
            parts.append(found)
        return "\n\n".join(parts)

    def ask(self, question: str) -> Reply:
        """Задать вопрос и получить ответ с возможным действием."""
        question = question.strip()
        if not question:
            return Reply("")

        # Сначала проверяем, не учат ли нас прямо сейчас.
        kind, content = parse_teaching(question)
        if kind == "remember" and content:
            added = self.memory.remember(content)
            text = "Запомнил!" if added else "Я это уже знаю."
            return Reply(text, taught=content if added else None)
        if kind == "forget" and content:
            count = self.memory.forget(content)
            return Reply("Забыл." if count else "А я такого и не помнил.")

        self.history.append({"role": "user", "content": question})
        self.history = self.history[-HISTORY_TURNS * 2:]

        raw = self.backend.reply(self.system_prompt(question), self.history)
        if not raw:
            return Reply("Я задумался и ничего не придумал.")

        self.history.append({"role": "assistant", "content": raw})

        # Выковыриваем строку ДЕЙСТВИЕ, остальное — то, что он скажет вслух.
        action = None
        match = ACTION_LINE.search(raw)
        if match:
            candidate = normalize(match.group(1)).strip()
            raw = ACTION_LINE.sub("", raw).strip()
            # Берём только то, что робот правда умеет.
            for known in ACTIONS:
                if normalize(known) == candidate:
                    action = known if known != "ничего" else None
                    break

        return Reply(raw.strip(), action=action)

    def reset(self) -> None:
        """Забыть текущий разговор (но не выученные факты)."""
        self.history = []
