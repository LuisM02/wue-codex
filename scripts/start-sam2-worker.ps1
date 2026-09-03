[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8010,

    [ValidateSet("Ubuntu-24.04")]
    [string]$Distribution = "Ubuntu-24.04"
)

$ErrorActionPreference = "Stop"

$workerWindowsPath = (Resolve-Path (
    Join-Path $PSScriptRoot "..\reconstruction-worker"
)).Path
$workerLinuxPath = (& wsl.exe -d $Distribution -u wueai -- wslpath -a $workerWindowsPath).Trim()
if ($LASTEXITCODE -ne 0 -or -not $workerLinuxPath) {
    throw "Could not resolve the WUE worker path inside WSL."
}

$checkpoint = "/home/wueai/checkpoints/sam2.1_hiera_base_plus.pt"
$python = "/home/wueai/wue-ai/bin/python"
$arguments = @(
    "-d", $Distribution,
    "-u", "wueai",
    "--cd", $workerLinuxPath,
    "--",
    "env",
    "WUE_WORKER_SEGMENTATION_PROVIDER=sam2",
    "WUE_SAM2_CHECKPOINT=$checkpoint",
    "WUE_SAM2_MODEL_CONFIG=configs/sam2.1/sam2.1_hiera_b+.yaml",
    "WUE_SAM2_DEVICE=cuda",
    $python,
    "-m", "uvicorn",
    "wue_worker.main:app",
    "--host", "127.0.0.1",
    "--port", $Port
)

Write-Host "Starting the WUE SAM 2.1 worker on http://127.0.0.1:$Port"
Write-Host "Keep this window open while WUE is using AI reconstruction."
& wsl.exe @arguments
exit $LASTEXITCODE
