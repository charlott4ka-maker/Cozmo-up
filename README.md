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

### Windows

```powershell
git clone https://github.com/charlott4ka-maker/Cozmo-up.git
cd Cozmo-up
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

### macOS / Linux

```bash
git clone https://github.com/charlott4ka-maker/Cozmo-up.git
cd Cozmo-up
bash scripts/setup.sh
```

Скрипт сам найдёт подходящий Python, создаст `.venv`, поставит зависимости,
скачает ассеты Cozmo (анимации, звуки, лица, ~570 МБ) в `~/.pycozmo/assets`
и сгенерирует русские фразы в `voices/`.

Если хочется вручную:

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pycozmo_resources.py download      # ассеты, нужен интернет
python scripts/make_voice.py       # русские фразы, нужен интернет
```

> На Windows активировать venv не обязательно (и `Activate.ps1` часто
> блокируется политикой выполнения). Просто вызывайте интерпретатор напрямую:
> `.\.venv\Scripts\python.exe examples\01_connect.py`

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
4. Проверьте, что всё готово:

```bash
source .venv/bin/activate
python scripts/doctor.py
```

Скрипт проверит версию Python, установку pycozmo, ассеты и то, что компьютер
действительно попал в сеть робота (`172.31.1.x`).

5. Подключитесь к роботу:

```bash
python examples/01_connect.py
```

Должны увидеть версию прошивки, серийный номер, напряжение батареи и мигнувшую
зелёную лампочку на спине.

> **Телефон держите в стороне.** Робот принимает только одно соединение.
> Если у вас на телефоне сохранена сеть Cozmo с включённым автоподключением —
> выключите «Автоподключение» в настройках этой сети, иначе телефон может
> перехватить соединение. Приложение Cozmo, если оно установлено, закройте.

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
python examples/08_russian_screen.py     # русский текст на экране
python examples/09_russian_speech.py     # робот говорит по-русски
python examples/10_russian_bot.py        # всё вместе: ездит, говорит, реагирует
```

Для `02`, `07` снимите робота с базы и поставьте на ровную поверхность.

**`examples/07_react.py` — главный пример.** Он показывает приём, на котором
строится всё своё поведение: подписка на события датчиков
(`cli.add_handler(...)`) и реакция на них. Отсюда и начинайте писать своё.

---

## Русский язык

Родного русского у Cozmo нет вообще: в ассетах лежат ровно четыре голоса
Acapela — `co-USEnglish-Ryan`, `co-French-Bruno`, `co-German-Klaus`,
`co-Japanese-Sakura` (`cozmo_resources/tts/Voices/`), а локализация
приложения есть только для `en-US`, `de-DE`, `fr-FR`, `ja-JP`. Вдобавок
синтез речи выполнялся в приложении на телефоне, и pycozmo его не
реализует вовсе.

Поэтому русский делаем своими силами — и получается полноценно.

### Текст на экране

Встроенный шрифт PIL знает только латиницу. `cozmo_up.screen` находит в
системе TTF-шрифт с кириллицей (DejaVu, Arial, Segoe UI, Liberation...),
проверяет, что русские буквы в нём действительно есть, и сам подбирает
кегль под размер экрана:

```python
from cozmo_up.screen import render_text
cli.display_image(render_text("ПРИВЕТ!"), duration=2.0)
cli.display_image(render_text("Батарея\n3.92 В"), duration=2.0)
```

Если шрифт не нашёлся — укажите свой: `COZMO_FONT=/путь/к/шрифту.ttf`.

### Речь

Фразы озвучиваются заранее на компьютере и проигрываются роботу как WAV.

```bash
# При интернете, ДО подключения к Wi-Fi робота:
python scripts/make_voice.py
```

Скрипт читает `phrases.ru.json`, синтезирует каждую фразу и сохраняет в
`voices/` в формате робота (16 бит, 22050 Гц, моно). Движки:

| `--engine` | качество русского | интернет | установка |
|---|---|---|---|
| `edge` (по умолчанию) | отличное, живой голос | нужен | `pip install edge-tts miniaudio` |
| `espeak` | роботизированное (Козмо идёт) | не нужен | `apt/brew install espeak-ng` |
| `system` | зависит от ОС | не нужен | `pip install pyttsx3` + русский голос |

#### Какой голос

Выбирается пресетом `--preset`:

| Пресет | Голос |
|---|---|
| `malchik` (по умолчанию) | мальчишеский: мужской голос, поднятый по тону |
| `kozmo` | как настоящий Козмо: высокий, быстрый, мультяшный |
| `malysh` | совсем малыш: очень высокий |
| `vzroslyj` | обычный мужской |
| `devushka` | обычный женский |

```bash
python scripts/make_voice.py --preset kozmo --force
python scripts/make_voice.py --list-presets      # что есть
python scripts/make_voice.py --list-voices       # все русские голоса edge-tts
```

`--force` обязателен при смене голоса: без него уже готовые файлы
пропускаются и голос не изменится.

Можно и вручную, поверх пресета:

```bash
python scripts/make_voice.py --pitch +60Hz --rate +15% --force
python scripts/make_voice.py --voice ru-RU-DmitryNeural --force
python scripts/make_voice.py --text "Я умный робот" --key umnyj
```

Дальше в коде:

```python
from cozmo_up.speech import Voice

voice = Voice()
voice.say(cli, "privet")            # проиграть
voice.say_and_show(cli, "privet")   # проиграть и показать текст на экране
```

### Два подводных камня, на которые мы наступили

**Экран — 128x32, а не 128x64.** Физическая матрица 128x64, но пакет
`DisplayImage` несёт 128x32 (робот растягивает строки). При этом
`pycozmo.expressions.*.render()` отдаёт 128x64, и `cli.display_image()` на
нём падает с `ValueError: Invalid image dimensions`. Прогоняйте картинки
через `cozmo_up.screen.to_screen()`:

```python
cli.display_image(to_screen(pycozmo.expressions.Happiness().render()))
```

**Баг в pycozmo 0.8.0: `play_audio` падает на громком звуке.** Её u-law
кодировщик переполняется на сэмплах ниже -31612 и выдаёт байт 256 —
`ValueError: byte must be in range(0, 256)`. Обычный синтез речи в это
попадает регулярно. Импорт `cozmo_up.speech` автоматически ставит патч
(`patch_pycozmo_audio()`), а `convert()` дополнительно ограничивает
амплитуду при генерации.

---

## Как это устроено

```
cozmo_up/helpers.py   обёртки: connect(), robot_info()
cozmo_up/screen.py    экран 128x32, русский текст, поиск шрифта
cozmo_up/speech.py    русская речь, конвертация аудио, патч бага pycozmo
examples/             пронумерованные примеры от простого к сложному
scripts/setup.sh      установка окружения (macOS/Linux)
scripts/setup.ps1     установка окружения (Windows)
scripts/doctor.py     диагностика: Python, pycozmo, ассеты, сеть робота
scripts/make_voice.py генерация русских фраз в voices/
phrases.ru.json       словарь фраз {ключ: текст}
requirements.txt      pycozmo 0.8.0 + Pillow + edge-tts + miniaudio
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
    cli.display_image(to_screen(pycozmo.expressions.Happiness().render()), duration=2.0)
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

Сначала запустите `python scripts/doctor.py` — он покажет, что именно не так.
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

**Windows сам отключается от сети робота**
В сети Cozmo нет интернета, и Windows норовит вернуться на домашний Wi-Fi.
В свойствах домашней сети снимите «Подключаться автоматически», а у сети
Cozmo — поставьте.

**Windows: брандмауэр блокирует**
При первом запуске появится окно «Разрешить Python доступ к сети» —
разрешите для **частных** сетей. Если окно случайно закрыли: Параметры →
Сеть и Интернет → Брандмауэр → Разрешить работу с приложением → найдите
Python.

**Windows: `Activate.ps1 не удается загрузить, так как выполнение сценариев отключено`**
Не активируйте venv вообще — вызывайте интерпретатор напрямую:
`.\.venv\Scripts\python.exe examples\01_connect.py`

**`ValueError: Invalid image dimensions. Only 128x32 images are supported`**
Картинку надо привести к 128x32: `cozmo_up.screen.to_screen(image)`.

**`ValueError: byte must be in range(0, 256)` при play_audio**
Баг кодировщика pycozmo на громком звуке. Добавьте `import cozmo_up.speech` —
он ставит патч автоматически.

**`Не найден шрифт с кириллицей`**
Укажите свой TTF: `COZMO_FONT=/путь/к/DejaVuSans.ttf python examples/08_russian_screen.py`

**`python scripts/make_voice.py` падает с сетевой ошибкой**
Вы уже в Wi-Fi робота — там нет интернета. Вернитесь в обычную сеть
или используйте офлайн-движок: `--engine espeak`.

---

## Полезные ссылки

- [pycozmo на GitHub](https://github.com/zayfod/pycozmo)
- [Документация pycozmo](https://pycozmo.readthedocs.io/en/latest/)
- [Описание протокола Cozmo](https://pycozmo.readthedocs.io/en/latest/external/protocol.html)
- [Список функций и что поддержано](https://github.com/zayfod/pycozmo/blob/master/docs/functions.md)
- [pycozmo на PyPI](https://pypi.org/project/pycozmo/)

pycozmo — неофициальный проект, не связанный с Anki и Digital Dream Labs.
