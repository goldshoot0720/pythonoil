param(
    [string]$TaskName = "PythonOilDailyTracker",
    [string]$Time = "13:00"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$triggerTime = [datetime]::ParseExact($Time, "HH:mm", $null)
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$projectRoot\run-oil-tracker-hidden.ps1`""
$dailyTrigger = New-ScheduledTaskTrigger -Daily -At $triggerTime
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
$settings.MultipleInstances = "IgnoreNew"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $dailyTrigger -Settings $settings -Description "Fetch and store daily OQD marker price silently at 13:00." -Force | Out-Null

Write-Host "Scheduled task created."
Write-Host "TaskName: $TaskName"
Write-Host "DailyTime: $Time"
Write-Host "Action: powershell.exe -WindowStyle Hidden -File run-oil-tracker-hidden.ps1"
