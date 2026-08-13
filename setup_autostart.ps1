param(
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$taskName = "ResearchJournal"
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$batchPath = Join-Path $projectDir "start_public.bat"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run PowerShell as Administrator, then execute this script again."
}

if ($Remove) {
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "The ResearchJournal startup task was removed."
    } else {
        Write-Host "The ResearchJournal startup task does not exist."
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $batchPath)) {
    throw "Startup script not found: $batchPath"
}

$condaPython = "D:\conda\Miniconda\envs\research-journal\python.exe"
if (-not (Test-Path -LiteralPath $condaPython)) {
    throw "The research-journal environment is missing. Create it using the README first."
}

$action = New-ScheduledTaskAction `
    -Execute "$env:SystemRoot\System32\cmd.exe" `
    -Argument "/d /c `"`"$batchPath`"`"" `
    -WorkingDirectory $projectDir
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartCount 99 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -MultipleInstances IgnoreNew
$taskPrincipal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $taskName `
    -Description "Start the Research Journal Waitress server at system startup" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $taskPrincipal `
    -Force | Out-Null

Start-ScheduledTask -TaskName $taskName
Write-Host "The startup task was registered and started: $taskName"
Write-Host "Remove it with: .\setup_autostart.ps1 -Remove"
