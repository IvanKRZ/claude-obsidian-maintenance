<#
.SYNOPSIS
    Weekly Maintenance Orchestrator für Obsidian Vault.
.DESCRIPTION
    Führt Index, Delta und Analyse in Reihenfolge aus.
    Prüft Git-Status und sichert den letzten Index als last_run.
.EXAMPLE
    .\Run-Weekly.ps1
    .\Run-Weekly.ps1 -SkipGitCheck
#>

[CmdletBinding()]
param(
    [switch]$SkipGitCheck
)

$ErrorActionPreference = 'Stop'
$OutputEncoding = [System.Text.Encoding]::UTF8

# UTF-8 für Python-Subprozesse erzwingen
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

# Pfade auflösen
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VaultRoot = Resolve-Path (Join-Path $ScriptDir '..\..')
$StateDir  = Join-Path $ScriptDir '..\state'
$IndexFile = Join-Path $StateDir 'index.json'
$LastRun   = Join-Path $StateDir 'last_run.json'

Write-Host "=== Vault Maintenance: $(Get-Date -Format 'yyyy-MM-dd HH:mm') ===" -ForegroundColor Cyan
Write-Host "Vault: $VaultRoot"

# --- Git-Safety-Check ---
if (-not $SkipGitCheck) {
    Push-Location $VaultRoot
    try {
        $gitDir = git rev-parse --git-dir 2>$null
        if ($LASTEXITCODE -eq 0) {
            $dirty = git status --porcelain
            if ($dirty) {
                Write-Warning "Uncommitted changes in vault detected."
                $answer = Read-Host "Continue anyway? [y/N]"
                if ($answer -notmatch '^[Yy]') {
                    Write-Host "Aborted." -ForegroundColor Yellow
                    exit 1
                }
            }
        }
    } finally {
        Pop-Location
    }
}

# --- State-Verzeichnis sicherstellen ---
if (-not (Test-Path $StateDir)) {
    New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
}

# --- last_run Backup ---
if (Test-Path $IndexFile) {
    Copy-Item -Path $IndexFile -Destination $LastRun -Force
    Write-Host "Previous index backed up to last_run.json" -ForegroundColor DarkGray
}

# --- Pipeline ausführen ---
function Invoke-PyStep {
    param(
        [string]$Label,
        [string]$Script
    )
    Write-Host "`n[$Label] $Script" -ForegroundColor Green
    $scriptPath = Join-Path $ScriptDir $Script
    & python $scriptPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "$Script failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

Invoke-PyStep -Label "1/3" -Script "vault_index.py"
Invoke-PyStep -Label "2/3" -Script "vault_delta.py"
Invoke-PyStep -Label "3/3" -Script "vault_analyze.py"

Write-Host ""
Write-Host "=== Ready for Claude Code ===" -ForegroundColor Cyan
Write-Host "Next step: run 'claude' in the vault directory, then use /weekly-maintenance"
