param(
    [string]$Compiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    [string]$Version = "0.1.0"
)
$ErrorActionPreference = 'Stop'
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Version must be MAJOR.MINOR.PATCH.' }
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Compiler)) { throw 'Pass -Compiler with the full path to Inno Setup ISCC.exe.' }
Push-Location -LiteralPath $repoRoot
try {
    & $pythonPath -m PyInstaller packaging/eduai.spec --noconfirm
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    & $pythonPath packaging/write_build_info.py $Version
    if ($LASTEXITCODE -ne 0) { throw 'Writing build information failed.' }
    & $Compiler "/DAppVersion=$Version" packaging/installer.iss
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup failed.' }
    $installerPath = Join-Path $repoRoot "dist\EduAI-Audit-Setup-$Version.exe"
    (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash.ToLower() + '  ' + (Split-Path -Leaf $installerPath) |
        Set-Content -LiteralPath "$installerPath.sha256" -Encoding ASCII
    Get-Item -LiteralPath $installerPath | Select-Object FullName, Length
} finally { Pop-Location }
