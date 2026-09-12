$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$tempDir = Join-Path $env:TEMP ("youtube-mp3-install-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

function Download-File([string]$Url, [string]$Destination, [string]$Label) {
    if (Test-Path -LiteralPath $Destination) {
        Write-Host "$Label est déjà installé." -ForegroundColor Green
        return
    }
    Write-Host "Téléchargement de $Label..." -ForegroundColor Cyan
    Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Destination
}

try {
    Write-Host "Installation des composants de YouTube MP3" -ForegroundColor White

    Download-File `
        "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" `
        (Join-Path $appDir "yt-dlp.exe") "yt-dlp"

    if (-not (Test-Path -LiteralPath (Join-Path $appDir "deno.exe"))) {
        $denoZip = Join-Path $tempDir "deno.zip"
        Download-File `
            "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip" `
            $denoZip "Deno"
        Expand-Archive -LiteralPath $denoZip -DestinationPath (Join-Path $tempDir "deno") -Force
        Copy-Item -LiteralPath (Join-Path $tempDir "deno\deno.exe") -Destination (Join-Path $appDir "deno.exe") -Force
    } else {
        Write-Host "Deno est déjà installé." -ForegroundColor Green
    }

    $ffmpegPath = Join-Path $appDir "ffmpeg.exe"
    $ffprobePath = Join-Path $appDir "ffprobe.exe"
    if (-not (Test-Path -LiteralPath $ffmpegPath) -or -not (Test-Path -LiteralPath $ffprobePath)) {
        $ffmpegZip = Join-Path $tempDir "ffmpeg.zip"
        Download-File `
            "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" `
            $ffmpegZip "FFmpeg"
        $ffmpegExtract = Join-Path $tempDir "ffmpeg"
        Expand-Archive -LiteralPath $ffmpegZip -DestinationPath $ffmpegExtract -Force
        $ffmpeg = Get-ChildItem -Path $ffmpegExtract -Filter "ffmpeg.exe" -Recurse | Select-Object -First 1
        $ffprobe = Get-ChildItem -Path $ffmpegExtract -Filter "ffprobe.exe" -Recurse | Select-Object -First 1
        if (-not $ffmpeg -or -not $ffprobe) { throw "Les fichiers FFmpeg sont introuvables." }
        Copy-Item -LiteralPath $ffmpeg.FullName -Destination $ffmpegPath -Force
        Copy-Item -LiteralPath $ffprobe.FullName -Destination $ffprobePath -Force
    } else {
        Write-Host "FFmpeg est déjà installé." -ForegroundColor Green
    }

    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktop "YouTube MP3.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = Join-Path $appDir "YouTube MP3.exe"
    $shortcut.WorkingDirectory = $appDir
    $shortcut.Save()

    Write-Host ""
    Write-Host "Installation terminée. Utilise le raccourci YouTube MP3 sur le Bureau." -ForegroundColor Green
    Start-Process -FilePath (Join-Path $appDir "YouTube MP3.exe") -WorkingDirectory $appDir
} catch {
    Write-Host ""
    Write-Host "Échec de l'installation : $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Appuie sur Entrée pour fermer"
    exit 1
} finally {
    if (Test-Path -LiteralPath $tempDir) {
        Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
