Set-StrictMode -Version Latest

function Test-WuePort {
    param([int]$Port)
    $connection = [System.Net.Sockets.TcpClient]::new()
    try {
        $pending = $connection.BeginConnect('127.0.0.1', $Port, $null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne(1000)) { return $false }
        $connection.EndConnect($pending)
        return $true
    } catch { return $false }
    finally { $connection.Dispose() }
}

function Test-WueIdentity {
    param($Payload, [string]$ExpectedService)
    if ($null -eq $Payload -or $null -eq $Payload.PSObject.Properties['status'] -or
        $null -eq $Payload.PSObject.Properties['service']) { return $false }
    return $Payload.status -eq 'ok' -and $Payload.service -eq $ExpectedService
}

function Test-WueFrontendIdentity {
    param([string]$Content)
    return $Content -match '<title>WUE .*Furniture Workshop</title>' -and
        $Content -match 'src="/src/main\.tsx(?:\?[^\"]*)?"'
}

function Get-WueServiceState {
    param([string]$Name, [int]$Port, [string]$ExpectedService, [switch]$Frontend)
    $portOpen = Test-WuePort -Port $Port
    if (-not $portOpen) {
        return [pscustomobject]@{ Name = $Name; Port = $Port; State = 'Stopped' }
    }
    $matches = $false
    try {
        if ($Frontend) {
            $page = Invoke-WebRequest "http://127.0.0.1:$Port/" -UseBasicParsing -TimeoutSec 3
            # Proxy readiness is checked after the API starts. A stopped API
            # must not misidentify an existing WUE frontend as a conflict.
            $matches = Test-WueFrontendIdentity -Content $page.Content
        } else {
            $path = if ($Name -eq 'API') { '/api/v1/health' } else { '/health' }
            $payload = Invoke-RestMethod "http://127.0.0.1:$Port$path" -TimeoutSec 3
            $matches = Test-WueIdentity -Payload $payload -ExpectedService $ExpectedService
        }
    } catch { $matches = $false }
    $state = if ($matches) { 'Healthy' } else { 'Conflict' }
    return [pscustomobject]@{ Name = $Name; Port = $Port; State = $state }
}

function Start-WueBackgroundProcess {
    param([string]$Name, [string]$WorkingDirectory, [string]$Command, [string]$LogDirectory)
    $shellName = if ($PSVersionTable.PSEdition -eq 'Core') { 'pwsh.exe' } else { 'powershell.exe' }
    $shell = Join-Path $PSHOME $shellName
    $quotedDirectory = $WorkingDirectory.Replace("'", "''")
    $code = "`$ErrorActionPreference = 'Stop'; Set-Location -LiteralPath '$quotedDirectory'; $Command"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($code))
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    return Start-Process -FilePath $shell -ArgumentList @('-NoProfile', '-EncodedCommand', $encoded) `
        -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $LogDirectory "$Name-$stamp.out.log") `
        -RedirectStandardError (Join-Path $LogDirectory "$Name-$stamp.err.log")
}

function Wait-WueService {
    param([string]$Name, [int]$Port, [string]$ExpectedService, [switch]$Frontend, $Process)
    $deadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
        $state = Get-WueServiceState -Name $Name -Port $Port -ExpectedService $ExpectedService -Frontend:$Frontend
        if ($state.State -eq 'Healthy') { return }
        if ($null -ne $Process) {
            $Process.Refresh()
            if ($Process.HasExited) { throw "$Name exited before it became ready. Check .wue-runtime logs." }
        }
        Start-Sleep -Seconds 1
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "$Name did not become ready within 60 seconds. Check .wue-runtime logs; no process was stopped."
}

Export-ModuleMember -Function Test-WuePort, Test-WueIdentity, Test-WueFrontendIdentity, Get-WueServiceState, Start-WueBackgroundProcess, Wait-WueService
