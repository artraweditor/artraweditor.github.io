# --- USER SETTINGS ----------------------------------------------------------

# ART-cli location
# -----------------

# By default this script will search ART-cli.exe location in ART versioned subdirectories using
# the default ART installation layout.
# Otherwise, if ART-cli.exe exists directly in the directory reported below, then this will be used:

$ArtRoot = "C:\Program Files\ART"

# SMART location
# ---------------
# The SMART-*-win64-portable.7z could be unzipped almost everywhere and its resulting main directory + subdirs & files
# could be moved into many different places. By default SMART root directory lives into the user LOCALAPPDATA.
# So, at first, this script will search for SMART.exe into versioned 'SMART-*-win64-portable' subdirectories.
# If this is the case, then you need NOT to change anything: you simply use the line below "as is":

$SmartRoot = Join-Path $env:LOCALAPPDATA

# Otherwise, you can set SMART root directory (and its content):
#  1. into user LOCALAPPDATA, changing its default name from: 'SMART-*-win64-portable' to, for example: 'SMART'.
#     In this case you need to comment the line above and uncomment the line below:

# $SmartRoot = Join-Path $env:LOCALAPPDATA "SMART"

#  2.  as a subdirectory of: 'C:\Program Files\', like, for example: 'C:\Program Files\SMART'
#      In this case you have to comment both the previous lines and uncomment the following one:

# $SmartRoot = "C:\Program Files\SMART"

# --- END OF USER SETTINGS -----------------------------------------------------

# Function: show an error dialog
function Show-ErrorBox($Message, $Title = "SMART Error") {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($Message, $Title, 'OK', 'Error') | Out-Null
}

# ------------------- Locate ART-cli (newest version) ------------------------

$ArtDir = Get-ChildItem -Path $ArtRoot -Directory |
          Where-Object { $_.Name -match '^\d+\.\d+\.\d+$' } |
          Sort-Object { [version]$_.Name } -Descending |
          Select-Object -First 1

if (-not $ArtDir) {
    Show-ErrorBox "Could not find any ART installation in:`n$ArtRoot"
    exit 1
}

$ArtCli = Join-Path $ArtDir.FullName "art-cli.exe"

if (-not (Test-Path $ArtCli)) {
    Show-ErrorBox "ART-cli was not found at:`n$ArtCli"
    exit 1
}

# ------------------- Locate SMART portable (newest version) -----------------

$SmartDir = Get-ChildItem -Path $SmartRoot -Directory |
            Where-Object { $_.Name -match '^SMART-\d+(\.\d+)*-win64-portable$' } |
            Sort-Object {
                # Extract version number from folder name
                [version]($_.Name -replace '^SMART-','' -replace '-win64-portable$','')
            } -Descending |
            Select-Object -First 1

if (-not $SmartDir) {
    Show-ErrorBox "Could not find any SMART portable installation in:`n$SmartRoot"
    exit 1
}

$SmartExe = Join-Path $SmartDir.FullName "SMART.exe"

if (-not (Test-Path $SmartExe)) {
    Show-ErrorBox "SMART.exe was not found in:`n$($SmartDir.FullName)"
    exit 1
}

# ------------------- Validate input RAW file --------------------------------
if ($args.Count -eq 0) {
    Show-ErrorBox "No input file received from ART."
    exit 1
}

$InputFile = $args[0]

if (-not (Test-Path $InputFile)) {
    Show-ErrorBox "Input file does not exist:`n$InputFile"
    exit 1
}

# ------------------- Create a temporary directory ---------------------------

$TempDir = New-Item -ItemType Directory -Path ([System.IO.Path]::GetTempPath()) -Name ("ART_SMART_" + [System.Guid]::NewGuid().ToString()) -Force
$Profile = Join-Path $TempDir "p1.arp"
$OutputFile = Join-Path $TempDir "out.jpg"
$ErrorLog = Join-Path $TempDir "error.txt"

# ------------------- Write minimal ARP profile ------------------------------

@"
[Version]
Version=1037

[Crop]
Enabled=false
"@ | Out-File -Encoding ascii $Profile

# ------------------- Run ART-cli -------------------------------------------

# Remove the "-f" if you want the SMART tool to work on the source-resolution image instead of a downscaled version.
# This is slow but keeps mask edge artifacts to the minimum possible.
$ArtArgs = @(
    "-f"
    "-d"
    "-s"
    "-p", $Profile
    "-Y"
    "-j"
    "-o", $OutputFile
    "-c", $InputFile
)

& $ArtCli @ArtArgs 2> $ErrorLog

# ------------------- Check for errors ---------------------------------------

if (-not (Test-Path $OutputFile)) {

    $ErrMsg = ""
    if (Test-Path $ErrorLog) {
        $ErrMsg = Get-Content $ErrorLog -Raw
    }

    if ([string]::IsNullOrWhiteSpace($ErrMsg)) {
        $ErrMsg = "ART-cli did not produce output, but no error message was available."
    }

    Show-ErrorBox $ErrMsg
    Remove-Item -Recurse -Force $TempDir
    exit 1
}

# ------------------- Rename to <raw>_SMART*.jpg -----------------------------

$Base = [System.IO.Path]::GetFileNameWithoutExtension($InputFile)
$Dir  = Split-Path $InputFile -Parent
$Target = Join-Path $Dir "${Base}_SMART.jpg"

$i = 1
while (Test-Path $Target) {
    $Target = Join-Path $Dir ("${Base}_SMART-$i.jpg")
    $i++
}

Move-Item -Force $OutputFile $Target

# ------------------- Call SMART.exe -----------------------------------------

Start-Process -FilePath $SmartExe -ArgumentList "`"$Target`""

# ------------------- Cleanup -------------------------------------------------

Remove-Item -Recurse -Force $TempDir
exit 0
