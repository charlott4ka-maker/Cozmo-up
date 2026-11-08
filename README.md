# Cozmo-up

Перепрограммирование робота **Anki Cozmo** на Python — свои движения, лица,
реакции и логика вместо родного приложения.

У вас есть Wi-Fi-имя робота и пароль — это ровно то, что нужно для **прямого**
управления через библиотеку [pycozmo](https://github.com/zayfod/pycozmo):
телефон и приложение Cozmo при этом **не нужны вообще**.

---

## Два способа программировать Cozmo

| | **pycozmo** (этот проект) | Официальный Cozmo SDK |
|---|---|---|
| Что нужно | только компьютер + Wi-Fi робота | компьютер **и** телефон с приложением Cozmo, соединённые USB-кабелем |
| Как работает | заменяет приложение: сам говорит с роботом по UDP | ваш код → приложение на телефоне → робот |
| Статус | сообщество, последний релиз 0.8.0 (ноябрь 2020), работает | приложения Anki убраны из сторов, Digital Dream Labs закрылась |
| Распознавание кубиков, лиц, TTS | **нет** (не реализовано) | есть |
| Моторы, экран, камера, лампочки, анимации | есть | есть |

Поскольку приложение Cozmo сейчас почти невозможно легально поставить на
современный телефон, **pycozmo — практичный путь**. Его ограничение: нет
встроенного распознавания кубиков/лиц и синтеза речи. Движение, экран, камера,
звук, лампочки и все родные анимации — доступны.

---

## Что нужно подготовить

**Железо**
- Cozmo с зарядной базой (зарядите заранее — работает ~1–1.5 часа)
- Компьютер с Wi-Fi (Windows / macOS / Linux)

**Софт**
- **Python 3.10, 3.11 или 3.12.** Это важно: на Python **3.13+ pycozmo не
  запускается** — из стандартной библиотеки удалили модуль `chunk`, и падает
  с ошибкой `ModuleNotFoundError: No module named 'chunk'`.
  Проверено: 3.12 — работает, 3.13 — нет.
- git

---

## Установка

```bash
git clone https://github.com/charlott4ka-maker/Cozmo-up.git
cd Cozmo-up
bash scripts/setup.sh
```

Скрипт сам найдёт подходящий Python, создаст `.venv`, поставит зависимости и
скачает ассеты Cozmo (анимации, звуки, лица) в `~/.pycozmo/assets`.

Если хочется вручную:

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pycozmo_resources.py download      # ~80 МБ ассетов, нужен интернет
```

> **Сделайте установку до того, как подключитесь к Wi-Fi робота.** Пока
> компьютер в сети Cozmo, интернета нет — скачать пакеты и ассеты не получится.

---

## Подключение к роботу

1. Поставьте Cozmo на зарядную базу — он проснётся.
2. **Поднимите и опустите ковш (lift)** — на экране робота появится его
   Wi-Fi-пароль (PSK). Имя сети вида `Cozmo_XXXXXX`.
3. В настройках Wi-Fi компьютера подключитесь к этой сети с этим паролем.
   Cozmo сам раздаёт Wi-Fi и выдаёт адреса из `172.31.1.0/24`; сам робот —
   `172.31.1.1`, порт `5551` (UDP).
4. Проверьте связь:

```bash
source .venv/bin/activate
python examples/01_connect.py
```

Должны увидеть версию прошивки, серийный номер, напряжение батареи и мигнувшую
зелёную лампочку на спине.

> Приложение Cozmo на телефоне в этот момент должно быть **закрыто** — робот
> держит только одно соединение.

---

## Примеры

Запускать из корня репозитория с активированным `.venv`:

```bash
python examples/01_connect.py            # проверка связи, информация о роботе
python examples/02_drive.py              # колёса, голова, ковш
python examples/03_face.py               # эмоции и свой текст на экране
python examples/04_camera.py             # кадры с камеры → out/*.png
python examples/05_lights_and_sound.py   # лампочки, фонарик, громкость
python examples/06_animations.py         # список и запуск родных анимаций
python examples/07_react.py              # своя логика: реакция на обрыв и подъём
```

Для `02`, `07` снимите робота с базы и поставьте на ровную поверхность.

**`examples/07_react.py` — главный пример.** Он показывает приём, на котором
строится всё своё поведение: подписка на события датчиков
(`cli.add_handler(...)`) и реакция на них. Отсюда и начинайте писать своё.

---

## Как это устроено

```
cozmo_up/helpers.py   обёртки: connect(), robot_info()
examples/             пронумерованные примеры от простого к сложному
scripts/setup.sh      установка окружения
requirements.txt      pycozmo 0.8.0 + Pillow
```

pycozmo подключается к роботу по UDP (вариант протокола selective-repeat ARQ) и
играет роль «движка»: процедурно рисует лицо у себя на компьютере и отправляет
на OLED-экран робота готовую картинку 128×64, читает `.bin`-файлы анимаций
(FlatBuffers) из ассетов и шлёт роботу кадры движений, лица и звука.

Робот ждёт ping-пакеты: если их нет **дольше 5 секунд — соединение
разрывается**. Поэтому долгие блокирующие операции в своём коде лучше не
делать, а связь держать через `pycozmo.connect()`, который сам всё обслуживает.

### Основное API

```python
import pycozmo

with pycozmo.connect() as cli:
    cli.drive_wheels(50.0, 50.0, duration=1.0)      # мм/с, макс. ~200
    cli.set_head_angle(0.0)                         # радианы, от -25° до +44.5°
    cli.set_lift_height(92.0)                       # мм, от 32 до 92
    cli.display_image(pycozmo.expressions.Happiness().render(), duration=2.0)
    cli.set_all_backpack_lights(pycozmo.lights.green_light)
    cli.set_head_light(True)                        # фонарик над камерой
    cli.enable_camera(enable=True, color=False)
    cli.load_anims(); cli.play_anim("anim_greeting_happy_01")
    cli.go_to_pose(...)                             # езда в точку
    cli.stop_all_motors()
```

Полезные события для `cli.add_handler(event, handler)`:
`EvtNewRawCameraImage`, `EvtCliffDetectedChange`, `EvtRobotPickedUpChange`,
`EvtRobotFallingChange`, `EvtRobotOnChargerChange`, `EvtRobotStateUpdated`,
`EvtAnimationCompleted`.

---

## Если что-то не работает

**`ModuleNotFoundError: No module named 'chunk'`**
У вас Python 3.13+. Поставьте 3.12 и пересоздайте `.venv`.

**Скрипт висит на «Connecting...» / таймаут**
- Компьютер не в сети `Cozmo_XXXXXX` (проверьте: `ping 172.31.1.1`).
- Windows/macOS мог сам переключиться на сеть с интернетом — зафиксируйте
  подключение к сети робота.
- Приложение Cozmo на телефоне подключено к роботу — закройте его.
- Робот заснул: поставьте на базу, подождите, снимите.

**`Factory/recovery firmware detected`**
На роботе заводская прошивка — часть функций не работает. Нужно обновление
прошивки (pycozmo умеет OTA-обновление, но делайте это осознанно: неудачная
прошивка «окирпичивает» робота).

**`Old firmware detected`**
pycozmo рассчитан на последнюю прошивку Cozmo. Часть пакетов
version-specific, что-то может работать иначе. Чаще всего это не мешает.

**Камера не отдаёт кадры**
Поднимите голову (`cli.set_head_angle(0.0)`), включите камеру и дайте 2–3
секунды. Цветной режим (`color=True`) требует поддержки в прошивке.

**VPN / корпоративная сеть**
Отключите VPN — он перехватывает трафик к `172.31.1.1`.

---

## Полезные ссылки

- [pycozmo на GitHub](https://github.com/zayfod/pycozmo)
- [Документация pycozmo](https://pycozmo.readthedocs.io/en/latest/)
- [Описание протокола Cozmo](https://pycozmo.readthedocs.io/en/latest/external/protocol.html)
- [Список функций и что поддержано](https://github.com/zayfod/pycozmo/blob/master/docs/functions.md)
- [pycozmo на PyPI](https://pypi.org/project/pycozmo/)

pycozmo — неофициальный проект, не связанный с Anki и Digital Dream Labs.
