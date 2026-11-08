# Установка окружения для Cozmo на Windows.
#
# Запуск из PowerShell, находясь в папке проекта:
#     powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)
Write-Host "Папка проекта: $(Get-Location)`n"

# pycozmo 0.8.0 не работает на Python 3.13+, ищем подходящую версию.
$py = $null
foreach ($v in @("3.12", "3.11", "3.10")) {
    & py "-$v" --version 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $py = $v; break }
}

if (-not $py) {
    Write-Host "ОШИБКА: не найден Python 3.10, 3.11 или 3.12." -ForegroundColor Red
    Write-Host ""
    Write-Host "На Python 3.13+ pycozmo падает с 'No module named chunk'."
    Write-Host "Поставьте Python 3.12 одним из способов:"
    Write-Host "  1) https://www.python.org/downloads/windows/ — найдите любой 3.12.x,"
    Write-Host "     скачайте 'Windows installer (64-bit)'."
    Write-Host "     При установке ОБЯЗАТЕЛЬНО галочка 'Add python.exe to PATH'."
    Write-Host "  2) Microsoft Store — найдите 'Python 3.12' и нажмите Получить."
    exit 1
}

Write-Host "==> Использую Python $py" -ForegroundColor Green
& py "-$py" -m venv .venv
if ($LASTEXITCODE -ne 0) { Write-Host "Не удалось создать .venv" -ForegroundColor Red; exit 1 }

$python = ".\.venv\Scripts\python.exe"

Write-Host "==> Устанавливаю зависимости" -ForegroundColor Green
& $python -m pip install --upgrade pip --quiet
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "Не удалось установить зависимости" -ForegroundColor Red; exit 1 }

Write-Host "==> Скачиваю ассеты Cozmo (около 570 МБ, это надолго)" -ForegroundColor Green
& $python .\.venv\Scripts\pycozmo_resources.py download
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ассеты не скачались. Без них не будет анимаций и звуков," -ForegroundColor Yellow
    Write-Host "но подключиться к роботу можно. Повторить позже:" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\python.exe .\.venv\Scripts\pycozmo_resources.py download"
}

Write-Host "==> Генерирую русские фразы" -ForegroundColor Green
& $python scripts\make_voice.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Фразы не сгенерировались (нужен интернет). Повторить позже:" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\python.exe scripts\make_voice.py"
}

Write-Host @"

================================================================
Установка закончена. Дальше:

  1. Поставьте Cozmo на зарядную базу, он проснётся.
  2. Поднимите и опустите ковш — на экране покажется Wi-Fi-пароль.
  3. Подключите компьютер к сети Cozmo_XXXXXX этим паролем.
  4. Проверьте готовность:

       .\.venv\Scripts\python.exe scripts\doctor.py

  5. Подключитесь к роботу:

       .\.venv\Scripts\python.exe examples\01_connect.py

Команды можно копировать как есть — активировать venv не нужно.
================================================================
"@ -ForegroundColor Cyan
