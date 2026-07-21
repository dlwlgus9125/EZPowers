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

    $PhaseDir = Split-Path -Parent $IndexPath
    $Invalidated = New-Object System.Collections.ArrayList

    $TaskGatePath = Join-Path $PhaseDir "task-gates/task-$($ResetStep + 1).json"
    if (Test-Path -LiteralPath $TaskGatePath) {
        Remove-Item -LiteralPath $TaskGatePath -Force
        [void]$Invalidated.Add($TaskGatePath)
    }

    $ProbePath = Join-Path $PhaseDir 'runtime-probe.json'
    if (Test-Path -LiteralPath $ProbePath) {
        $ProbeStep = -1
        try {
            $Probe = Get-Content -LiteralPath $ProbePath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($null -ne $Probe -and $Probe.PSObject.Properties.Name -contains 'step') {
                $ProbeStep = [int]$Probe.step
            }
        }
        catch {
            $ProbeStep = -1
        }
        if ($ProbeStep -eq $ResetStep) {
            Remove-Item -LiteralPath $ProbePath -Force
            [void]$Invalidated.Add($ProbePath)
        }
    }

    if ($Invalidated.Count -gt 0) {
        Write-Output "Invalidated stale evidence for step ${ResetStep}: $($Invalidated -join ', ')"
    }
    else {
        Write-Output "No stale evidence artifacts found for step $ResetStep"
    }
}

if ($Status -or $ResetStep -ge 0) {
    $Index.steps |
        Sort-Object { [int]$_.step } |
        Select-Object step, name, status, step_md |
        Format-Table -AutoSize | Out-String -Width 200 |
        Write-Output
}
