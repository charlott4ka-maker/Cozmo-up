# Установка окружения для Cozmo на Windows.
#
# Запуск из PowerShell, находясь в папке проекта:
#     powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)
Write-Host "Папка проекта: $(Get-Location)`n"

# pycozmo 0.8.0 не работает на Python 3.13+, ищем подходящую версию.
# Сначала через лаунчер py, потом по прямым именам в PATH.
$python = $null

function Test-PythonExe([string]$exe, [string[]]$prefix) {
    # Возвращает путь к интерпретатору, если он живой и версия подходит.
    try {
        $out = & $exe @prefix "-c" "import sys;print(sys.executable)" 2>$null
    } catch {
        return $null
    }
    if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
    return ($out | Select-Object -Last 1).Trim()
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($v in @("3.12", "3.11", "3.10")) {
        $found = Test-PythonExe "py" @("-$v")
        if ($found) { $python = $found; break }
    }
}

if (-not $python) {
    foreach ($name in @("python3.12", "python3.11", "python3.10", "python")) {
        if (-not (Get-Command $name -ErrorAction SilentlyContinue)) { continue }
        $found = Test-PythonExe $name @()
        if (-not $found) { continue }
        $ver = & $found "-c" "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($ver -in @("3.12", "3.11", "3.10")) { $python = $found; break }
    }
}

if (-not $python) {
    Write-Host "ОШИБКА: не найден Python 3.10, 3.11 или 3.12." -ForegroundColor Red
    Write-Host ""
    Write-Host "На Python 3.13+ pycozmo падает с 'No module named chunk'."
    Write-Host "Поставьте Python 3.12 одним из способов:"
    Write-Host "  1) winget install -e --id Python.Python.3.12"
    Write-Host "     (потом закройте и откройте PowerShell заново)"
    Write-Host "  2) https://www.python.org/downloads/windows/ — найдите любой 3.12.x,"
    Write-Host "     скачайте 'Windows installer (64-bit)'."
    Write-Host "     При установке ОБЯЗАТЕЛЬНО галочка 'Add python.exe to PATH'."
    exit 1
}

Write-Host "==> Использую $python" -ForegroundColor Green
& $python -m venv .venv
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
