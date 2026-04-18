[CmdletBinding()]
param(
    [switch]$DisableAI
)

$ErrorActionPreference = "Stop"

Write-Host "Starting APK build..." -ForegroundColor Cyan

$pythonHome = Join-Path $env:LocalAppData 'Programs\Python\Python312'
$pythonExe = Join-Path $pythonHome 'python.exe'
$pythonScripts = Join-Path $pythonHome 'Scripts'
$fletExe = Join-Path $pythonScripts 'flet.exe'
$flutterBin = "C:\Users\user\flutter\3.38.7\bin"
$javaHome = "C:\Program Files\Android\Android Studio\jbr"

if (Test-Path $flutterBin) {
    $env:PATH = "$flutterBin;$env:PATH"
}

if (Test-Path $pythonScripts) {
    $env:PATH = "$pythonScripts;$env:PATH"
}

if (Test-Path $javaHome) {
    $env:JAVA_HOME = $javaHome
    $env:PATH = "$javaHome\bin;$env:PATH"
    Write-Host "Using Java from Android Studio..." -ForegroundColor Cyan
}

if (-not (Test-Path $pythonExe)) {
    throw "Python 3.12 was not found at $pythonExe"
}

if (-not (Test-Path $fletExe)) {
    throw "Flet was not found at $fletExe"
}

& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install "flet>=0.84.0" openai

if ($DisableAI) {
    $env:CARE_APP_DISABLE_AI = "1"
    Write-Host "Building test APK with AI disabled..." -ForegroundColor Yellow
}

& $fletExe build apk . --exclude build dist __pycache__ care_records.db *.txt apk_build_log.txt

Write-Host ""
Write-Host "APK build finished. Check build\\apk." -ForegroundColor Green
