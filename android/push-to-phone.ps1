$ErrorActionPreference = "Stop"
if (-not $env:JAVA_HOME) {
    $jdk = Get-ChildItem "$env:ProgramFiles\Microsoft" -Directory -Filter "jdk-17*" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending |
        Select-Object -First 1
    if ($jdk) { $env:JAVA_HOME = $jdk.FullName }
}
if (-not $env:ANDROID_HOME) {
    foreach ($candidate in @("$env:LOCALAPPDATA\Android\Sdk", "C:\Android\Sdk")) {
        if (Test-Path $candidate) { $env:ANDROID_HOME = $candidate; break }
    }
}
if (-not $env:ANDROID_HOME) { Write-Error "未找到 Android SDK。请设置 ANDROID_HOME。" }
$adb = Join-Path $env:ANDROID_HOME "platform-tools\adb.exe"

Set-Location $PSScriptRoot
& .\gradlew.bat :app:assembleDebug
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$devices = & $adb devices
$ready = $devices | Select-String "^\S+\s+device$"
if (-not $ready) {
    Write-Error "手机未就绪。请解锁手机并允许 USB 调试。当前：`n$($devices -join "`n")"
}

& $adb push "app\build\outputs\apk\debug\app-debug.apk" "/sdcard/Download/Longriver-debug.apk"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "已复制到手机下载目录：Longriver-debug.apk"
