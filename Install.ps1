param([string]$MO2Directory = 'I:\.other.games\Mod.Organizer-2.5.2')
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'ExternalFileManager')).Path
$plugins = (Resolve-Path -LiteralPath (Join-Path $MO2Directory 'plugins')).Path
$destination = Join-Path $plugins 'ExternalFileManager'
if (Get-Process -Name ModOrganizer -ErrorAction SilentlyContinue) {
    throw 'Close MO2 before installing the plugin.'
}
$existing = Get-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.LinkType -eq 'Junction' -and
        [string]::Equals([IO.Path]::GetFullPath([string]$existing.Target), $source, [StringComparison]::OrdinalIgnoreCase)) {
        Write-Output 'The correct plugin junction is already installed.'
        exit 0
    }
    throw "Destination already exists; no files were replaced: $destination"
}
New-Item -ItemType Junction -Path $destination -Target $source
