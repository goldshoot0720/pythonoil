param(
    [string]$TaskName = "PythonOilDailyTracker",
    [string]$Time = "13:00",
    [string]$PythonExe = "",
    [string]$DbPath = "data\oil_prices.db"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $PythonExe) {
    $venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $PythonExe = $venvPython
    } else {
        $PythonExe = "python"
    }
}

$triggerTime = [datetime]::ParseExact($Time, "HH:mm", $null)
$actionArgs = "-m oil_tracker.cli --db `"$DbPath`""
$action = New-ScheduledTaskAction -Execute $PythonExe -Argument $actionArgs -WorkingDirectory $projectRoot
$dailyTrigger = New-ScheduledTaskTrigger -Daily -At $triggerTime
$startupTrigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
$settings.MultipleInstances = "IgnoreNew"

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger @($dailyTrigger, $startupTrigger) `
    -Settings $settings `
    -Description "Fetch and store daily OQD marker price from gulfmerc.com at 13:00 and on startup." `
    -Force | Out-Null

Write-Host "Scheduled task created."
Write-Host "TaskName: $TaskName"
Write-Host "DailyTime: $Time"
Write-Host "StartupTrigger: Enabled"
Write-Host "Python: $PythonExe"
Write-Host "WorkingDirectory: $projectRoot"
Write-Host "Arguments: $actionArgs"
