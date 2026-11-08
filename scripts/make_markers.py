#!/usr/bin/env python
"""Сделать лист с маркерами, которые Козмо умеет видеть.

    python scripts/make_markers.py

Создаёт markers/markers.png — распечатайте на обычном принтере, вырежьте
и расставьте. Робот будет их узнавать камерой (examples/16_markers.py).

Важно: белое поле вокруг чёрного квадрата обязательно, без него маркер
не распознаётся. Скрипт его добавляет сам.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cozmo_up.vision import generate_marker  # noqa: E402

OUT_DIR = Path("markers")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ids", type=int, nargs="+", default=[0, 1, 2, 3, 4, 5],
                        help="номера маркеров (по умолчанию 0-5)")
    parser.add_argument("--size", type=int, default=400,
                        help="размер маркера в пикселях")
    parser.add_argument("--columns", type=int, default=3)
    args = parser.parse_args()

    import cv2
    import numpy as np

    OUT_DIR.mkdir(exist_ok=True)

    pad = args.size // 4          # белое поле — без него не распознаётся
    cell = args.size + 2 * pad
    label_h = 60
    cols = args.columns
    rows = (len(args.ids) + cols - 1) // cols

    sheet = np.full((rows * (cell + label_h), cols * cell), 255, dtype=np.uint8)

    for n, marker_id in enumerate(args.ids):
        img = generate_marker(marker_id, args.size)
        padded = cv2.copyMakeBorder(img, pad, pad, pad, pad,
                                    cv2.BORDER_CONSTANT, value=255)
        r, c = divmod(n, cols)
        y, x = r * (cell + label_h), c * cell
        sheet[y:y + cell, x:x + cell] = padded
        cv2.putText(sheet, f"id {marker_id}", (x + pad, y + cell + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, 0, 3)

        single = OUT_DIR / f"marker_{marker_id}.png"
        cv2.imwrite(str(single), padded)

    out = OUT_DIR / "markers.png"
    cv2.imwrite(str(out), sheet)

    print(f"Готово: {out}")
    print(f"Отдельные маркеры: {OUT_DIR}/marker_N.png")
    print()
    print("Распечатайте, вырежьте по белому полю (оно обязательно!)")
    print("и расставьте. Чем крупнее напечатан маркер, тем дальше")
    print("Козмо его увидит — его камера всего 320x240.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
