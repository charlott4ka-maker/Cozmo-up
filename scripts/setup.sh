#!/usr/bin/env bash
# Установка окружения для программирования Cozmo.
# Запуск: bash scripts/setup.sh
set -euo pipefail

cd "$(dirname "$0")/.."

# pycozmo 0.8.0 несовместим с Python 3.13+, поэтому ищем 3.12/3.11/3.10.
PY=""
for candidate in python3.12 python3.11 python3.10; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done

if [ -z "$PY" ]; then
    echo "ОШИБКА: нужен Python 3.10, 3.11 или 3.12." >&2
    echo "На Python 3.13+ pycozmo падает с 'No module named chunk'." >&2
    echo "Windows: скачайте python.org/downloads/release/python-3129/" >&2
    echo "macOS:   brew install python@3.12" >&2
    echo "Linux:   sudo apt install python3.12 python3.12-venv" >&2
    exit 1
fi

echo "==> Использую $PY ($($PY --version))"
$PY -m venv .venv
echo "==> Устанавливаю зависимости"
./.venv/bin/pip install --upgrade pip -q
./.venv/bin/pip install -r requirements.txt

echo "==> Скачиваю ассеты Cozmo (анимации, звуки, лица) в ~/.pycozmo"
./.venv/bin/pycozmo_resources.py download

cat <<'MSG'

Готово. Дальше:

  1. Поставьте Cozmo на зарядную базу (он проснётся).
  2. Поднимите и опустите ковш (lift) — на экране покажется Wi-Fi-пароль.
  3. Подключите компьютер к Wi-Fi сети Cozmo_XXXXXX этим паролем.
  4. Активируйте окружение и проверьте связь:

       source .venv/bin/activate      # Windows: .venv\Scripts\activate
       python examples/01_connect.py

MSG
