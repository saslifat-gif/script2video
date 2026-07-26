$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Version = "1.0.5"
$IconScript = Join-Path $ProjectRoot "packaging\windows\generate_icon.py"
$SpecFile = Join-Path $ProjectRoot "packaging\windows\script2video.spec"
$InstallerFile = Join-Path $ProjectRoot "packaging\windows\installer.iss"

python $IconScript
python -m PyInstaller --noconfirm --clean $SpecFile

$LanguageTagsIndex = Join-Path $ProjectRoot "dist\Script2Video Studio\_internal\language_tags\data\json\index.json"
if (-not (Test-Path $LanguageTagsIndex)) {
    throw "Packaged language-tags registry is missing: $LanguageTagsIndex"
}

$IsccCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
if ($IsccCommand) {
    $IsccPath = $IsccCommand.Source
} else {
    $DefaultIscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $DefaultIscc) {
        $IsccPath = $DefaultIscc
    } else {
        throw "Inno Setup 6 was not found. Install it before building the installer."
    }
}

& $IsccPath "/DMyAppVersion=$Version" $InstallerFile
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE."
}

$Installer = Join-Path $ProjectRoot "release\Script2Video-Studio-$Version-Windows-x64.exe"
if (-not (Test-Path $Installer)) {
    throw "Expected installer was not created: $Installer"
}

$SizeMb = [math]::Round((Get-Item $Installer).Length / 1MB, 1)
Write-Host "Built $Installer ($SizeMb MB)"
