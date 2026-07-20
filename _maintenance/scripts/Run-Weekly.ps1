<#
.SYNOPSIS
    Weekly Maintenance Orchestrator für einen Obsidian Vault.
.DESCRIPTION
    Führt Index, Delta, Analyse, Trend und Quellen-Scan in Reihenfolge aus.
    Prüft Git-Status und sichert den letzten Index als last_run.
    Jeder Schritt wird gegen seine erwartete JSON-Ausgabe validiert.
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
$StateDir     = Join-Path $ScriptDir '..\state'
$IndexFile    = Join-Path $StateDir 'index.json'
$LastRun      = Join-Path $StateDir 'last_run.json'
$DeltaFile    = Join-Path $StateDir 'delta.json'
$FindingsFile = Join-Path $StateDir 'findings.json'
$HistoryFile  = Join-Path $StateDir 'history.json'
$SourcesFile  = Join-Path $StateDir 'missing_sources.json'

Write-Host "=== Vault Maintenance: $(Get-Date -Format 'yyyy-MM-dd HH:mm') ===" -ForegroundColor Cyan
Write-Host "Vault: $VaultRoot"

# --- Git: stale index.lock aufräumen + Safety-Check ---
Push-Location $VaultRoot
try {
    $gitDir = git rev-parse --git-dir 2>$null
    if ($LASTEXITCODE -eq 0) {
        # git-dir kann relativ (".git") oder absolut zurückkommen
        $gitDirFull = if ([System.IO.Path]::IsPathRooted($gitDir)) {
            $gitDir
        } else {
            Join-Path $VaultRoot $gitDir
        }

        # Stale .git/index.lock entfernen — aber nur, wenn kein git-Prozess läuft.
        # obsidian-git/Auto-Backup kann bei einem Absturz ein verwaistes Lock
        # hinterlassen, das jede spätere Git-Operation blockiert.
        $lockFile = Join-Path $gitDirFull 'index.lock'
        if (Test-Path $lockFile) {
            if (Get-Process -Name git -ErrorAction SilentlyContinue) {
                Write-Warning "index.lock vorhanden, aber ein git-Prozess läuft — Lock bleibt bestehen."
            } else {
                Write-Warning "Stale .git/index.lock gefunden (kein git-Prozess aktiv) — wird entfernt."
                Remove-Item -LiteralPath $lockFile -Force
            }
        }

        # Uncommitted-Changes-Check (mit -SkipGitCheck überspringbar)
        if (-not $SkipGitCheck) {
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
    }
} finally {
    Pop-Location
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

# --- Validierungs-Gate ---
# Prüft, ob eine erzeugte JSON existiert und parsebar ist. Bricht hart ab,
# damit kein Folgeschritt auf korrupten/halb geschriebenen Daten aufsetzt.
function Assert-ValidJson {
    param(
        [string]$Path,
        [string]$Producer
    )
    if (-not (Test-Path $Path)) {
        Write-Error "$Producer hat die erwartete JSON nicht erzeugt: $Path"
        exit 1
    }
    try {
        Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null
    } catch {
        Write-Error "$Producer hat ungueltige JSON erzeugt ($Path): $($_.Exception.Message)"
        exit 1
    }
    Write-Host "  OK: $(Split-Path -Leaf $Path) ist valide JSON" -ForegroundColor DarkGray
}

# --- Pipeline ausführen ---
function Invoke-PyStep {
    param(
        [string]$Label,
        [string]$Script,
        [string]$ExpectJson
    )
    Write-Host "`n[$Label] $Script" -ForegroundColor Green
    $scriptPath = Join-Path $ScriptDir $Script
    & python $scriptPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "$Script failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
    if ($ExpectJson) {
        Assert-ValidJson -Path $ExpectJson -Producer $Script
    }
}

Invoke-PyStep -Label "1/5" -Script "vault_index.py"   -ExpectJson $IndexFile
Invoke-PyStep -Label "2/5" -Script "vault_delta.py"   -ExpectJson $DeltaFile
Invoke-PyStep -Label "3/5" -Script "vault_analyze.py" -ExpectJson $FindingsFile
Invoke-PyStep -Label "4/5" -Script "vault_trend.py"   -ExpectJson $HistoryFile
Invoke-PyStep -Label "5/5" -Script "scan_sources.py"  -ExpectJson $SourcesFile

Write-Host ""
Write-Host "=== Ready for Claude Code ===" -ForegroundColor Cyan
Write-Host "Next step: run 'claude' in the vault directory, then use /weekly-maintenance"
