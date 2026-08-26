param(
    [ValidateSet("start", "stop", "status", "health")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$runDir = Join-Path $PSScriptRoot ".run"
$logDir = Join-Path $PSScriptRoot "logs"

New-Item -ItemType Directory -Force -Path $runDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$services = @(
    @{
        Name = "pizza-api"
        Port = 7071
        Args = "mocks/mock_api_server.py --service pizza --port 7071"
    },
    @{
        Name = "registration-api"
        Port = 7072
        Args = "mocks/mock_api_server.py --service registration --port 7072"
    },
    @{
        Name = "mcp-sse"
        Port = 8081
        Args = "mocks/mock_mcp_sse_server.py --port 8081"
    }
)

function Get-PidFilePath([string]$name) {
    return Join-Path $runDir ("{0}.pid" -f $name)
}

function Get-ServicePid([string]$name) {
    $pidFile = Get-PidFilePath $name
    if (-not (Test-Path $pidFile)) {
        return $null
    }

    $pidText = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not $pidText) {
        return $null
    }

    $pidVal = 0
    if (-not [int]::TryParse($pidText, [ref]$pidVal)) {
        return $null
    }

    try {
        $proc = Get-Process -Id $pidVal -ErrorAction Stop
        return $proc.Id
    }
    catch {
        return $null
    }
}

function Start-ServiceMock($svc) {
    $name = $svc.Name
    $pidFile = Get-PidFilePath $name
    $existingPid = Get-ServicePid $name
    if ($existingPid) {
        Write-Host "[SKIP] $name already running (PID $existingPid)"
        return
    }

    $stdoutLog = Join-Path $logDir ("{0}.out.log" -f $name)
    $stderrLog = Join-Path $logDir ("{0}.err.log" -f $name)

    $process = Start-Process -FilePath $pythonExe `
        -ArgumentList $svc.Args `
        -WorkingDirectory $repoRoot `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru

    Set-Content -Path $pidFile -Value $process.Id -Encoding ascii
    Write-Host "[START] $name on port $($svc.Port) (PID $($process.Id))"
}

function Stop-ServiceMock($svc) {
    $name = $svc.Name
    $pidFile = Get-PidFilePath $name
    $pidVal = Get-ServicePid $name
    if (-not $pidVal) {
        Write-Host "[SKIP] $name not running"
        if (Test-Path $pidFile) {
            Remove-Item $pidFile -Force
        }
        return
    }

    try {
        Stop-Process -Id $pidVal -Force
        Write-Host "[STOP] $name stopped (PID $pidVal)"
    }
    catch {
        Write-Host "[WARN] failed to stop $name (PID $pidVal): $($_.Exception.Message)"
    }

    if (Test-Path $pidFile) {
        Remove-Item $pidFile -Force
    }
}

function Show-ServiceStatus($svc) {
    $name = $svc.Name
    $pidVal = Get-ServicePid $name
    if ($pidVal) {
        Write-Host "[RUNNING] $name (PID $pidVal, port $($svc.Port))"
    }
    else {
        Write-Host "[STOPPED] $name (port $($svc.Port))"
    }
}

function Check-Health($svc) {
    $name = $svc.Name
    $uri = "http://127.0.0.1:$($svc.Port)/health"
    try {
        $response = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec 3
        Write-Host "[HEALTHY] $name $uri -> $($response.StatusCode)"
    }
    catch {
        Write-Host "[UNHEALTHY] $name $uri -> $($_.Exception.Message)"
    }
}

switch ($Action) {
    "start" {
        foreach ($svc in $services) {
            Start-ServiceMock $svc
        }
        Start-Sleep -Seconds 1
        foreach ($svc in $services) {
            Check-Health $svc
        }
    }
    "stop" {
        foreach ($svc in $services) {
            Stop-ServiceMock $svc
        }
    }
    "status" {
        foreach ($svc in $services) {
            Show-ServiceStatus $svc
        }
    }
    "health" {
        foreach ($svc in $services) {
            Check-Health $svc
        }
    }
}
