"""Работа с экраном Cozmo, включая русский текст.

ВАЖНО про размер. Физический экран робота — 128x64, но пакет DisplayImage,
которым pycozmo его обновляет, несёт картинку **128x32** (робот растягивает
строки по вертикали). Поэтому `cli.display_image()` принимает ровно
128x32 в режиме "1". Всё, что рисуем, прогоняем через `to_screen()`.

Процедурные лица (`pycozmo.expressions.*.render()`) отдают 128x64 — их тоже
надо прогонять через `to_screen()`, иначе будет
ValueError: Invalid image dimensions.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

#: Размер картинки, которую принимает DisplayImage.
SCREEN_SIZE = (128, 32)

#: Где искать шрифт с кириллицей. Можно переопределить переменной
#: окружения COZMO_FONT (путь к .ttf).
_FONT_CANDIDATES: List[str] = [
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    # macOS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    # Windows
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/tahomabd.ttf",
]

_font_cache: dict = {}


def _has_cyrillic(font: ImageFont.FreeTypeFont) -> bool:
    """Проверить, что в шрифте реально есть кириллица.

    Если глифов нет, все отсутствующие символы рисуются одним и тем же
    .notdef-прямоугольником — значит 'Я' и 'Ж' отрисуются одинаково.
    """
    def bitmap(ch: str) -> bytes:
        img = Image.new("1", (48, 48), 0)
        ImageDraw.Draw(img).text((4, 4), ch, font=font, fill=1)
        return img.tobytes()

    try:
        # 'Я' и 'Ж' выглядят по-разному. Если кириллицы в шрифте нет,
        # оба символа нарисуются одним и тем же .notdef-прямоугольником.
        return bitmap("Я") != bitmap("Ж")
    except Exception:  # noqa: BLE001
        return False


def find_font(size: int = 18) -> ImageFont.FreeTypeFont:
    """Найти шрифт с кириллицей нужного размера.

    Порядок: переменная COZMO_FONT → известные системные пути.
    Если ничего не нашлось — понятная ошибка с подсказкой.
    """
    if size in _font_cache:
        return _font_cache[size]

    candidates = []
    env_font = os.environ.get("COZMO_FONT")
    if env_font:
        candidates.append(env_font)
    candidates.extend(_FONT_CANDIDATES)

    for path in candidates:
        if not Path(path).is_file():
            continue
        try:
            font = ImageFont.truetype(path, size)
        except OSError:
            continue
        if _has_cyrillic(font):
            _font_cache[size] = font
            return font

    raise RuntimeError(
        "Не найден шрифт с кириллицей.\n"
        f"Проверены пути: {', '.join(candidates)}\n"
        "Укажите свой .ttf через переменную окружения COZMO_FONT, например:\n"
        "  COZMO_FONT=/путь/к/DejaVuSans-Bold.ttf python examples/08_russian_screen.py"
    )


def to_screen(image: Image.Image) -> Image.Image:
    """Привести любую картинку к формату, который принимает робот.

    Нужен именно 128x32 в монохромном режиме "1".
    """
    if image.size != SCREEN_SIZE:
        image = image.resize(SCREEN_SIZE)
    if image.mode != "1":
        image = image.convert("1")
    return image


def render_text(
    text: str,
    font_size: Optional[int] = None,
    align: str = "center",
) -> Image.Image:
    """Нарисовать русский текст и вернуть картинку 128x32 для робота.

    Если размер не задан, подбирается автоматически так, чтобы текст влез.
    Поддерживается перенос строк через \\n.
    """
    lines = text.split("\n")

    sizes = [font_size] if font_size else [22, 20, 18, 16, 14, 12, 10, 8]
    image = Image.new("1", SCREEN_SIZE, 0)
    draw = ImageDraw.Draw(image)

    for size in sizes:
        font = find_font(size)
        boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
        widths = [b[2] - b[0] for b in boxes]
        line_h = max(b[3] - b[1] for b in boxes)
        total_h = line_h * len(lines) + 2 * (len(lines) - 1)
        if max(widths) <= SCREEN_SIZE[0] - 2 and total_h <= SCREEN_SIZE[1] - 2:
            break
    else:
        font = find_font(sizes[-1])
        boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
        widths = [b[2] - b[0] for b in boxes]
        line_h = max(b[3] - b[1] for b in boxes)
        total_h = line_h * len(lines) + 2 * (len(lines) - 1)

    y = (SCREEN_SIZE[1] - total_h) // 2
    for line, box, width in zip(lines, boxes, widths):
        if align == "left":
            x = 1
        elif align == "right":
            x = SCREEN_SIZE[0] - width - 1
        else:
            x = (SCREEN_SIZE[0] - width) // 2
        draw.text((x - box[0], y - box[1]), line, font=font, fill=1)
        y += line_h + 2

    return image


def preview(image: Image.Image, file=sys.stdout) -> None:
    """Напечатать картинку в терминал ASCII-символами — удобно для отладки."""
    image = to_screen(image)
    px = image.load()
    for y in range(SCREEN_SIZE[1]):
        print("".join("#" if px[x, y] else "." for x in range(SCREEN_SIZE[0])), file=file)
