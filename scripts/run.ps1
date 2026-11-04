# Thin launcher for Windows PowerShell. All arguments are forwarded to p2v-agent.
$ErrorActionPreference = "Stop"

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 "$PSScriptRoot\p2v.py" @args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python "$PSScriptRoot\p2v.py" @args
} else {
    Write-Error "p2v-agent-skill: Python 3.10+ is required (py/python not found)."
    exit 1
}

exit $LASTEXITCODE
