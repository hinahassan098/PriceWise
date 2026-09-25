# Fast PriceWise Android icon restore (System.Drawing)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$root = "C:\Users\KLH\OneDrive\Desktop\hina github repo\PriceWise\mobile"
$assets = Join-Path $root "assets"
$res = Join-Path $root "android\app\src\main\res"
$maroon = [System.Drawing.Color]::FromArgb(255, 92, 18, 40)

function Load-Bmp([string]$path) {
  $bytes = [IO.File]::ReadAllBytes($path)
  $ms = New-Object IO.MemoryStream(,$bytes)
  return [Drawing.Bitmap]::FromStream($ms)
}

function Save-Png([Drawing.Bitmap]$bmp, [string]$path) {
  $dir = Split-Path $path -Parent
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  $tmp = "$path.tmp.png"
  $bmp.Save($tmp, [Drawing.Imaging.ImageFormat]::Png)
  Move-Item $tmp $path -Force
}

function Solid([int]$size, [Drawing.Color]$color) {
  $bmp = New-Object Drawing.Bitmap $size, $size
  $g = [Drawing.Graphics]::FromImage($bmp)
  $g.Clear($color)
  $g.Dispose()
  return $bmp
}

function ResizeTo([Drawing.Bitmap]$src, [int]$size) {
  $dst = New-Object Drawing.Bitmap $size, $size
  $g = [Drawing.Graphics]::FromImage($dst)
  $g.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g.PixelOffsetMode = [Drawing.Drawing2D.PixelOffsetMode]::HighQuality
  $g.Clear([Drawing.Color]::Transparent)
  $g.DrawImage($src, 0, 0, $size, $size)
  $g.Dispose()
  return $dst
}

# Good PW sources still on disk
$icon = Load-Bmp (Join-Path $assets "icon.png")
$fgSrc = Load-Bmp (Join-Path $assets "android-icon-foreground.png")
# If foreground was overwritten by Expo somehow, fall back to icon
if ($fgSrc.Width -lt 64) { $fgSrc = $icon }

$bg = Solid 1024 $maroon
Save-Png $bg (Join-Path $assets "android-icon-background.png")
Save-Png $fgSrc (Join-Path $assets "android-icon-foreground.png")
# Monochrome: use icon resized onto transparent isn't trivial without pixels;
# reuse foreground as monochrome stand-in (Android themed icons)
Save-Png $fgSrc (Join-Path $assets "android-icon-monochrome.png")
foreach ($n in @("icon.png","favicon.png","adaptive-icon.png","splash-icon.png")) {
  Save-Png $icon (Join-Path $assets $n)
}
Write-Host "assets ok"

$dens = @{
  mdpi = @(48,108); hdpi=@(72,162); xhdpi=@(96,216); xxhdpi=@(144,324); xxxhdpi=@(192,432)
}
foreach ($d in $dens.Keys) {
  $folder = Join-Path $res "mipmap-$d"
  $L = $dens[$d][0]; $A = $dens[$d][1]
  $lBmp = ResizeTo $icon $L
  $bBmp = ResizeTo $bg $A
  $fBmp = ResizeTo $fgSrc $A
  Save-Png $lBmp (Join-Path $folder "ic_launcher.png")
  Save-Png $lBmp (Join-Path $folder "ic_launcher_round.png")
  Save-Png $bBmp (Join-Path $folder "ic_launcher_background.png")
  Save-Png $fBmp (Join-Path $folder "ic_launcher_foreground.png")
  Save-Png $fBmp (Join-Path $folder "ic_launcher_monochrome.png")
  Get-ChildItem $folder -Filter "ic_launcher*.webp" | Remove-Item -Force
  $lBmp.Dispose(); $bBmp.Dispose(); $fBmp.Dispose()
  Write-Host "mipmap-$d ok"
}

$splash = @{ mdpi=200; hdpi=300; xhdpi=400; xxhdpi=600; xxxhdpi=800 }
foreach ($d in $splash.Keys) {
  $folder = Join-Path $res "drawable-$d"
  if (-not (Test-Path $folder)) { New-Item -ItemType Directory -Force -Path $folder | Out-Null }
  $s = ResizeTo $icon $splash[$d]
  Save-Png $s (Join-Path $folder "splashscreen_logo.png")
  $s.Dispose()
}
$icon.Dispose(); $fgSrc.Dispose(); $bg.Dispose()
Write-Host "DONE"
