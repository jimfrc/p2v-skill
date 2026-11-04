<#
.SYNOPSIS
    Windows text-to-speech helper for the prompt2video skill.

.DESCRIPTION
    Renders a UTF-8 text file to a WAV file using the built-in System.Speech
    (SAPI) engine, so no extra dependencies are needed on Windows.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File tts.ps1 `
        -TextFile public/scenes/scene1.txt -OutFile public/scenes/scene1.wav `
        -Voice "Microsoft Huihui Desktop" -Wpm 175

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File tts.ps1 -ListVoices
#>
param(
    [string]$TextFile,
    [string]$OutFile,
    [string]$Voice = '',
    [int]$Wpm = 175,
    [switch]$ListVoices
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer

if ($ListVoices) {
    try {
        $synth.GetInstalledVoices() |
            Where-Object { $_.Enabled } |
            ForEach-Object { $_.VoiceInfo.Name }
    } finally {
        $synth.Dispose()
    }
    exit 0
}

if ([string]::IsNullOrWhiteSpace($TextFile)) { throw 'Missing -TextFile' }
if ([string]::IsNullOrWhiteSpace($OutFile)) { throw 'Missing -OutFile' }

$textPath = (Resolve-Path -LiteralPath $TextFile).Path
$text = [System.IO.File]::ReadAllText($textPath, [System.Text.Encoding]::UTF8)
if ([string]::IsNullOrWhiteSpace($text)) { throw "Text file is empty: $TextFile" }

if (-not [string]::IsNullOrWhiteSpace($Voice)) {
    $available = @($synth.GetInstalledVoices() |
        Where-Object { $_.Enabled } |
        ForEach-Object { $_.VoiceInfo.Name })
    if ($available -notcontains $Voice) {
        $synth.Dispose()
        throw "Voice '$Voice' not found. Installed voices: $($available -join ', ')"
    }
    $synth.SelectVoice($Voice)
}

# Map words-per-minute onto the SAPI rate scale (-10..10), where 175 wpm is normal.
$synth.Rate = [Math]::Max(-10, [Math]::Min(10, [int][Math]::Round(($Wpm - 175) / 12.0)))

$outPath = [System.IO.Path]::GetFullPath($OutFile)
$outDir = [System.IO.Path]::GetDirectoryName($outPath)
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}

try {
    $synth.SetOutputToWaveFile($outPath)
    $synth.Speak($text)
} finally {
    $synth.Dispose()
}

Write-Output $outPath
