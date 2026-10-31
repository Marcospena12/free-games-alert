param(
    [switch]$SkipTests,
    [switch]$SkipInstaller
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Ambiente virtual não encontrado em .venv."
}

if (-not $SkipTests) {
    Write-Host "Executando testes..."
    & $python -m pytest
    if ($LASTEXITCODE -ne 0) {
        throw "Os testes falharam."
    }
}

Write-Host "Garantindo dependências de build..."
& $python -m pip install --disable-pip-version-check -e ".[build]"
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível instalar as dependências de build."
}

Write-Host "Gerando ícone..."
& $python (Join-Path $PSScriptRoot "generate_icon.py")
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível gerar o ícone."
}

$version = (& $python -c "import sys; sys.path.insert(0, 'src'); from free_games_hub import __version__; print(__version__)").Trim()
if ($LASTEXITCODE -ne 0 -or -not $version) {
    throw "Não foi possível obter a versão do aplicativo."
}
Write-Host "Versão: $version"

& $python (Join-Path $PSScriptRoot "make_version_info.py") $version (Join-Path $root "build\version_info.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível gerar os metadados de versão."
}

Write-Host "Gerando executável com PyInstaller..."
& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath (Join-Path $root "dist") `
    --workpath (Join-Path $root "build\pyinstaller") `
    (Join-Path $PSScriptRoot "free_games_hub.spec")
if ($LASTEXITCODE -ne 0) {
    throw "O PyInstaller falhou."
}

$exe = Join-Path $root "dist\FreeGamesHub\FreeGamesHub.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Executável não encontrado após o build: $exe"
}
Write-Host "Executável: $exe"

if ($SkipInstaller) {
    return
}

$isccCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
)
$iscc = $isccCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if (-not $iscc) {
    throw "Inno Setup 6 não encontrado. Instale com: winget install --id JRSoftware.InnoSetup -e"
}

Write-Host "Gerando instalador com Inno Setup..."
& $iscc "/DAppVersion=$version" (Join-Path $PSScriptRoot "FreeGamesHub.iss")
if ($LASTEXITCODE -ne 0) {
    throw "O Inno Setup falhou."
}

$installer = Join-Path $root "dist\FreeGamesHub-Setup-$version.exe"
if (-not (Test-Path -LiteralPath $installer)) {
    throw "Instalador não encontrado após o build: $installer"
}
Write-Host "Instalador: $installer"
