#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v powershell.exe >/dev/null 2>&1; then
  exit 0
fi

if ! command -v wslpath >/dev/null 2>&1; then
  exit 0
fi

PS_SCRIPT="$(mktemp /tmp/opencommotion-shim-XXXXXX.ps1)"
cat >"$PS_SCRIPT" <<'PS1'
param(
  [string]$WslRoot,
  [string]$ApplyFirewall = "ask"
)
$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($WslRoot)) {
  throw "Missing WSL root path"
}

$targetDir = Join-Path $env:USERPROFILE ".local\bin"
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
$cmdPath = Join-Path $targetDir "opencommotion.cmd"

$cmdLine = "wsl.exe bash -lc ""cd ''{0}'' && bash ./opencommotion %*""" -f $WslRoot
$cmdContent = "@echo off`r`nsetlocal`r`n$cmdLine`r`n"
Set-Content -Path $cmdPath -Value $cmdContent -Encoding Ascii

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ([string]::IsNullOrWhiteSpace($userPath)) {
  $userPath = ""
}
if ($userPath -notmatch [Regex]::Escape($targetDir)) {
  $newPath = if ($userPath.Length -gt 0) { "$userPath;$targetDir" } else { "$targetDir" }
  [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
  Write-Output "Installed Windows launcher: $cmdPath"
  Write-Output "Added to user PATH: $targetDir"
  Write-Output "Restart PowerShell to use: opencommotion -run"
} else {
  Write-Output "Installed Windows launcher: $cmdPath"
}

$firewallChoice = if ([string]::IsNullOrWhiteSpace($ApplyFirewall)) { "ask" } else { $ApplyFirewall.Trim().ToLowerInvariant() }
if ($firewallChoice -eq "ask") {
  $firewallChoice = "no"
  try {
    $interactive = ($Host.Name -eq "ConsoleHost") -and [Environment]::UserInteractive
    if ($interactive) {
      $answer = Read-Host "Allow Windows inbound firewall rules for OpenCommotion ports (only needed to reach services from Windows/external networks)? [y/N]"
      if ($answer -and $answer.Trim().ToLowerInvariant() -in @("y", "yes")) {
        $firewallChoice = "yes"
      }
    } else {
      Write-Output "Firewall: skipped (non-interactive; only needed for external access)."
    }
  } catch {
    Write-Output "Firewall: skipped (prompt unavailable; only needed for external access)."
  }
}

# Add Windows Firewall inbound allow rules so WSL2 services are reachable from
# Windows or other devices only when requested. Rules remain Private,Domain scoped.
if ($firewallChoice -eq "yes") {
  $fwPorts = @(8000, 8001, 8010, 8011, 5173)
  $fwScript = '$ports=@(' + ($fwPorts -join ',') + ');foreach($p in $ports){$r="OpenCommotion-$p";Remove-NetFirewallRule -DisplayName $r -ErrorAction SilentlyContinue;try{New-NetFirewallRule -DisplayName $r -Direction Inbound -Protocol TCP -LocalPort $p -Action Allow -Profile Private,Domain|Out-Null;Write-Output "Firewall: allowed inbound TCP $p (Private/Domain only)"}catch{Write-Output "Firewall: skipped port $p - $_"}}'
  try {
    Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden `
      -ArgumentList @('-NoProfile', '-Command', $fwScript)
    Write-Output "Firewall rules applied (Private/Domain only)."
    Write-Output "Remove later with opencommotion -uninstall or rerun this shim and decline."
  } catch {
    Write-Output "Firewall: could not apply rules (requires admin). Run as admin to enable external access from Windows."
  }
} else {
  Write-Output "Firewall: skipped (only required if you expose services beyond WSL)."
}
PS1

WINDOWS_PS_SCRIPT="$(wslpath -w "$PS_SCRIPT")"
FIREWALL_CHOICE="${OPENCOMMOTION_WINDOWS_FIREWALL:-ask}"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$WINDOWS_PS_SCRIPT" -WslRoot "$ROOT" -ApplyFirewall "$FIREWALL_CHOICE"
rm -f "$PS_SCRIPT"
