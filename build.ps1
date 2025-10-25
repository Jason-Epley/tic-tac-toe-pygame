Param(
    [string]$SpecFile = "TicTacToe_Python_Capstone_Project_1.spec",
    [string]$ExeName = "TicTacToe_Python_Capstone_Project_1",
    [bool]$OneDir = $true,
    [string]$DistPath = "dist",
    [string]$WorkPath = "build"
)

Write-Host "Running build helper..."

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "python not found on PATH. Activate your venv or add python to PATH and try again."
    exit 2
}

# Ensure PyInstaller is available
try {
    python -c "import PyInstaller" 2>$null
} catch {
    Write-Host "PyInstaller not found. Installing into current environment..."
    python -m pip install --upgrade pip
    python -m pip install pyinstaller
}

    if (Test-Path $SpecFile) {
        Write-Host "Using spec file: $SpecFile"
        $cmd = "pyinstaller --noconfirm --clean --distpath `"$DistPath`" --workpath `"$WorkPath`" $SpecFile"
    } else {
        Write-Host "Spec file not found; building from script using one-dir mode"
        $extra = ""
        if ($OneDir) { $extra = "--onedir" } else { $extra = "--onefile" }
        $addData = 'assets;assets'
        # Escape the embedded quotes for the --add-data argument so PowerShell parser doesn't misinterpret it
        $cmd = "pyinstaller --noconfirm --clean $extra --distpath `"$DistPath`" --workpath `"$WorkPath`" --add-data `"$addData`" TicTacToe_Python_Capstone_Project_1.py"
    }

Write-Host "Running: $cmd"
cmd /c $cmd

# Determine the expected dist folder (pyinstaller places a folder named after the entry exe when --onedir)
$distSubFolder = Join-Path -Path $DistPath -ChildPath $ExeName
if (-not (Test-Path $distSubFolder)) {
    Write-Error "Build did not produce expected $distSubFolder folder. Check output above for errors."
    exit 3
}

$zipName = "$ExeName-$(Get-Date -Format yyyyMMdd-HHmmss).zip"
if (Test-Path $zipName) { Remove-Item $zipName -Force }

Write-Host "Zipping $distSubFolder -> $zipName"
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory((Resolve-Path -Path $distSubFolder), (Resolve-Path -Path $zipName))

Write-Host "Build complete. Created $zipName"