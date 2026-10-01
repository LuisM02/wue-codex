# Dependency-free startup safety checks; does not start or stop WUE.
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'WueRuntime.psm1') -Force
$checks = 0
function Assert-WueCheck {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
    $script:checks += 1
}
Assert-WueCheck (Test-WueIdentity ([pscustomobject]@{status='ok';service='WUE API'}) 'WUE API') 'Expected API was rejected'
Assert-WueCheck (-not (Test-WueIdentity ([pscustomobject]@{status='ok';service='Other API'}) 'WUE API')) 'Another app was accepted'
Assert-WueCheck (-not (Test-WueIdentity ([pscustomobject]@{status='failed';service='WUE API'}) 'WUE API')) 'Failed health was accepted'
Assert-WueCheck (-not (Test-WueIdentity ([pscustomobject]@{unexpected='value'}) 'WUE API')) 'Malformed response was accepted'
Assert-WueCheck (-not (Test-WueIdentity $null 'WUE API')) 'Missing response was accepted'
$frontend = '<title>WUE · Furniture Workshop</title><script type="module" src="/src/main.tsx"></script>'
Assert-WueCheck (Test-WueFrontendIdentity $frontend) 'WUE frontend was rejected'
Assert-WueCheck (Test-WueFrontendIdentity ($frontend.Replace('main.tsx"', 'main.tsx?t=123"'))) 'Vite development query was rejected'
Assert-WueCheck (-not (Test-WueFrontendIdentity '<title>Other App</title>')) 'Another frontend was accepted'
Assert-WueCheck (-not (Test-WueFrontendIdentity '<title>WUE · Furniture Workshop</title>')) 'Non-development HTML was accepted'

# Check port occupancy without using any application port. The temporary
# listener is created here and closed in finally; it never belongs to WUE.
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
try {
    $listener.Start()
    $probePort = $listener.LocalEndpoint.Port
    Assert-WueCheck (Test-WuePort $probePort) 'An occupied local port was reported free'
} finally { $listener.Stop() }
Assert-WueCheck (-not (Test-WuePort $probePort)) 'The closed test port was reported occupied'

# Mock only inside this imported module, then restore it. These cases never
# contact a service and verify partial-startup identification and conflicts.
$runtime = Get-Module WueRuntime
$states = & $runtime {
    function script:Test-WuePort { return $true }
    function script:Invoke-RestMethod { return [pscustomobject]@{status='ok';service='Other API'} }
    function script:Invoke-WebRequest { return [pscustomobject]@{Content='<title>WUE · Furniture Workshop</title><script src="/src/main.tsx?t=123"></script>'} }
    Get-WueServiceState -Name 'API' -Port 8011 -ExpectedService 'WUE API'
    # Frontend identity must remain recognizable when the API is unavailable.
    function script:Invoke-RestMethod { throw 'API offline' }
    Get-WueServiceState -Name 'Frontend' -Port 5174 -Frontend
    Get-WueServiceState -Name 'API' -Port 8011 -ExpectedService 'WUE API'
    function script:Test-WuePort { return $false }
    Get-WueServiceState -Name 'API' -Port 8011 -ExpectedService 'WUE API'
}
Import-Module (Join-Path $PSScriptRoot 'WueRuntime.psm1') -Force
Assert-WueCheck ($states[0].State -eq 'Conflict') 'Other API must be a conflict'
Assert-WueCheck ($states[1].State -eq 'Healthy') 'Stopped API must not hide frontend identity'
Assert-WueCheck ($states[2].State -eq 'Conflict') 'Unhealthy occupied API must be a conflict'
Assert-WueCheck ($states[3].State -eq 'Stopped') 'Unused API port must be stopped'

# Exercise hidden process launch and working-directory quoting with an
# immediately exiting harmless child, not a second application instance.
$testRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$testLogs = Join-Path $testRoot '.wue-runtime\startup-tests'
$null = New-Item -ItemType Directory -Path $testLogs -Force
$child = Start-WueBackgroundProcess -Name 'startup-test' -WorkingDirectory $testRoot `
    -Command 'Write-Output $pwd.Path; exit 0' -LogDirectory $testLogs
Assert-WueCheck ($child.WaitForExit(10000)) 'Harmless startup test child did not exit'
$child.Refresh()
Assert-WueCheck ($child.ExitCode -eq 0) 'Hidden child launch failed'
$outputLog = Get-ChildItem -LiteralPath $testLogs -Filter 'startup-test-*.out.log' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
Assert-WueCheck ((Get-Content -LiteralPath $outputLog.FullName -Raw).Trim() -eq $testRoot) 'Child working directory was incorrect'
Write-Host "$checks startup safety checks passed. No WUE service was changed."
