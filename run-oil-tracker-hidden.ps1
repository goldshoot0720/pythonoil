$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPythonw = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$scriptPath = Join-Path $projectRoot "run_oil_tracker_silent.pyw"

if (Test-Path $venvPythonw) {
    $pythonExe = $venvPythonw
} elseif (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = "pythonw.exe"
}

Start-Process -FilePath $pythonExe -ArgumentList ('"' + $scriptPath + '"') -WorkingDirectory $projectRoot -WindowStyle Hidden
