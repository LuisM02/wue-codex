[CmdletBinding()]
param([switch]$CheckOnly)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'WueRuntime.psm1') -Force
$wueRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$services = @(
    @{ Name = 'Worker'; Port = 8010; ExpectedService = 'WUE local vision worker' },
    @{ Name = 'API'; Port = 8011; ExpectedService = 'WUE API' },
    @{ Name = 'Frontend'; Port = 5174; Frontend = $true }
)

# Inspect every target before starting anything. Never kill a conflicting app.
$states = @($services | ForEach-Object { Get-WueServiceState @_ })
$states | Format-Table Name, Port, State -AutoSize
$conflicts = @($states | Where-Object State -eq 'Conflict')
if ($conflicts.Count -gt 0) {
    throw "Unrecognized or unhealthy service on port(s) $($conflicts.Port -join ', '). Nothing was started or stopped. Resolve the conflict first."
}
$stopped = @($states | Where-Object State -eq 'Stopped')
if ($CheckOnly -and $stopped.Count -gt 0) {
    throw "WUE is not fully running. Run this script without -CheckOnly to start missing services."
}

if (-not $CheckOnly -and $stopped.Count -gt 0) {
    $python = Join-Path $wueRoot '.venv\Scripts\python.exe'
    $vite = Join-Path $wueRoot 'frontend\node_modules\vite\bin\vite.js'
    if (-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $vite)) {
        throw 'Existing Python environment or frontend dependencies are missing. No installation is performed by this script.'
    }
    $node = (Get-Command node.exe -ErrorAction Stop).Source
    $null = Get-Command wsl.exe -ErrorAction Stop
    $logDirectory = Join-Path $wueRoot '.wue-runtime'
    $null = New-Item -ItemType Directory -Path $logDirectory -Force
    foreach ($service in $services) {
        # Re-check after another service starts, avoiding duplicate startup.
        $state = Get-WueServiceState @service
        if ($state.State -eq 'Healthy') { continue }
        if ($state.State -ne 'Stopped') { throw "$($service.Name) port became busy. No process was stopped." }
        switch ($service.Name) {
            'Worker' {
                $working = $wueRoot
                $script = (Join-Path $PSScriptRoot 'start-sam2-worker.ps1').Replace("'", "''")
                $command = "& '$script'"
            }
            'API' {
                $working = Join-Path $wueRoot 'backend'
                $executable = $python.Replace("'", "''")
                $command = "`$env:WUE_CLASSIFICATION_PROVIDER='http'; `$env:WUE_RECONSTRUCTION_PROVIDER='http'; " +
                    "`$env:WUE_CLASSIFICATION_SERVICE_URL='http://127.0.0.1:8010'; `$env:WUE_RECONSTRUCTION_SERVICE_URL='http://127.0.0.1:8010'; " +
                    "& '$executable' -m uvicorn app.main:app --host 127.0.0.1 --port 8011"
            }
            'Frontend' {
                $working = Join-Path $wueRoot 'frontend'
                $command = "`$env:WUE_API_PROXY_TARGET='http://127.0.0.1:8011'; & '$($node.Replace("'", "''"))' '$($vite.Replace("'", "''"))' --host 127.0.0.1 --port 5174 --strictPort"
            }
        }
        Write-Host "Starting $($service.Name) on port $($service.Port)..."
        $process = Start-WueBackgroundProcess -Name $service.Name -WorkingDirectory $working -Command $command -LogDirectory $logDirectory
        Wait-WueService @service -Process $process
    }
}

$database = Invoke-RestMethod 'http://127.0.0.1:8011/api/v1/health/database' -TimeoutSec 5
if ($database.status -ne 'ok') { throw 'PostgreSQL is not ready. No database changes were made.' }
$proxy = Invoke-RestMethod 'http://127.0.0.1:5174/api/v1/health' -TimeoutSec 5
if (-not (Test-WueIdentity -Payload $proxy -ExpectedService 'WUE API')) {
    throw 'The frontend does not reach the WUE API. Check WUE_API_PROXY_TARGET; no service was stopped.'
}
$model = Invoke-RestMethod 'http://127.0.0.1:8010/v1/model-status' -TimeoutSec 5
if (-not $model.ready -or $model.pipeline -notlike 'sam2.1-*' -or -not $model.uses_gpu) {
    throw 'The worker is reachable but the expected local SAM 2.1 GPU provider is not ready. No provider was replaced.'
}
Write-Host 'WUE API, database, frontend proxy, and local SAM provider are ready.'
Write-Host 'Open http://127.0.0.1:5174/ to test WUE.'
Write-Host 'No migrations, installations, data resets, or process termination were performed.'
