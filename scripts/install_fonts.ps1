# Install Persian fonts for WeasyPrint
# Requires: pip install fonttools
param(
    [string]$SourceDir = "../personnel-certification/app/fonts",
    [string]$DestDir = "../fonts"
)

$SourceDir = Resolve-Path $SourceDir
$DestDir = Resolve-Path $DestDir

pip install fonttools
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install fonttools"
    exit 1
}

python -c @"
from fontTools.ttLib import TTFont
import os
src = r'$SourceDir'
dst = r'$DestDir'
for f in os.listdir(src):
    if f.endswith('.woff2'):
        woff2 = os.path.join(src, f)
        ttf_name = f.replace('.woff2', '.ttf')
        ttf = os.path.join(dst, ttf_name)
        font = TTFont(woff2)
        font.flavor = None
        font.save(ttf)
        print(f'Converted: {f} -> {ttf_name}')
"@

Write-Host "Fonts installed successfully"
