param(
    [Parameter(Mandatory = $true)]
    [string] $Phase,

    [switch] $Status,

    [int] $ResetStep = -1,

    [string] $ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'

$IndexPath = Join-Path $ProjectRoot "phases/$Phase/index.json"

if (-not (Test-Path -LiteralPath $IndexPath)) {
    throw "Harness phase index not found: $IndexPath"
}

$Index = Get-Content -LiteralPath $IndexPath -Raw -Encoding UTF8 | ConvertFrom-Json

if (-not $Status -and $ResetStep -lt 0) {
    $Status = $true
}

if ($ResetStep -ge 0) {
    $Target = $Index.steps | Where-Object { [int]$_.step -eq $ResetStep } | Select-Object -First 1
    if (-not $Target) {
        throw "Step $ResetStep not found in phase '$Phase'"
    }

    $Target.status = 'pending'
    $Index | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $IndexPath -Encoding UTF8
    Write-Output "Reset step $ResetStep to pending in $IndexPath"
}

if ($Status -or $ResetStep -ge 0) {
    $Index.steps |
        Sort-Object { [int]$_.step } |
        Select-Object step, name, status, step_md |
        Format-Table -AutoSize | Out-String -Width 200 |
        Write-Output
}
