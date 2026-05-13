param(
    [Parameter(Mandatory = $true)]
    [string] $Phase,

    [string] $ProjectRoot = (Get-Location).Path
)

$ErrorActionPreference = 'Stop'

$GatePath = Join-Path $ProjectRoot "phases/$Phase/wiring-gate.json"
if (-not (Test-Path -LiteralPath $GatePath)) {
    throw "Wiring gate not found: $GatePath"
}

function Save-Gate {
    param($Gate, [string] $Path)
    $Gate | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function New-Attempt {
    param(
        [string] $Command,
        [int] $ExitCode,
        [string] $Stdout,
        [string] $Stderr
    )
    [pscustomobject]@{
        command = $Command
        exit_code = $ExitCode
        stdout_tail = if ($Stdout.Length -gt 2000) { $Stdout.Substring($Stdout.Length - 2000) } else { $Stdout }
        stderr_tail = if ($Stderr.Length -gt 2000) { $Stderr.Substring($Stderr.Length - 2000) } else { $Stderr }
        timestamp = (Get-Date).ToUniversalTime().ToString('o')
    }
}

$Gate = Get-Content -LiteralPath $GatePath -Raw -Encoding UTF8 | ConvertFrom-Json

if (-not [bool]$Gate.required) {
    $Gate.status = 'pass'
    Save-Gate $Gate $GatePath
    Write-Output "Wiring gate skipped: required=false"
    exit 0
}

$Commands = @($Gate.commands)
if ($Commands.Count -eq 0) {
    $Gate.status = 'spec_gap'
    Save-Gate $Gate $GatePath
    Write-Output 'Wiring gate status: spec_gap (no commands)'
    exit 2
}

if (-not ($Gate.PSObject.Properties.Name -contains 'attempts') -or $null -eq $Gate.attempts) {
    $Gate | Add-Member -NotePropertyName attempts -NotePropertyValue @() -Force
}

$Attempts = @($Gate.attempts)
foreach ($Command in $Commands) {
    $OutFile = Join-Path $env:TEMP ("ezpowers-gate-out-" + [guid]::NewGuid().ToString("N") + ".txt")
    $ErrFile = Join-Path $env:TEMP ("ezpowers-gate-err-" + [guid]::NewGuid().ToString("N") + ".txt")
    try {
        $Process = Start-Process -FilePath powershell.exe `
            -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $Command) `
            -WorkingDirectory $ProjectRoot `
            -PassThru `
            -Wait `
            -WindowStyle Hidden `
            -RedirectStandardOutput $OutFile `
            -RedirectStandardError $ErrFile

        $Stdout = if (Test-Path -LiteralPath $OutFile) { Get-Content -LiteralPath $OutFile -Raw -Encoding UTF8 } else { '' }
        $Stderr = if (Test-Path -LiteralPath $ErrFile) { Get-Content -LiteralPath $ErrFile -Raw -Encoding UTF8 } else { '' }
        $Attempts += New-Attempt $Command $Process.ExitCode $Stdout $Stderr

        if ($Process.ExitCode -ne 0) {
            $Gate.attempts = $Attempts
            $Gate.status = 'fail'
            Save-Gate $Gate $GatePath
            Write-Output "Wiring gate status: fail ($Command)"
            exit 1
        }
    }
    finally {
        Remove-Item -LiteralPath $OutFile, $ErrFile -ErrorAction SilentlyContinue
    }
}

$Gate.attempts = $Attempts
$Gate.status = 'pass'
Save-Gate $Gate $GatePath
Write-Output 'Wiring gate status: pass'
