"""Téléchargeur de playlists YouTube, interface Tkinter."""
import configparser
import importlib.util
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from urllib.parse import urlparse, parse_qs


FROZEN = bool(getattr(sys, "frozen", False))
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
APP_DIR = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent
CONFIG_FILE = APP_DIR / "config.ini"
LEGACY_FILES = {
    "destination": APP_DIR / "destination.txt",
    "mode": APP_DIR / "mode.txt",
    "quality": APP_DIR / "quality.txt",
}
QUALITY_OPTIONS = ("320 kb/s", "256 kb/s", "192 kb/s", "128 kb/s")
YOUTUBE_URL = re.compile(
    r"https?://(?:(?:www|music|m)\.)?(?:youtube\.com|youtu\.be)/[^\s<>\]\)]+",
    re.IGNORECASE,
)


def load_settings():
    settings = {
        "destination": str(Path.home() / "Music" / "YouTube MP3"),
        "mode": "track",
        "quality": QUALITY_OPTIONS[0],
    }
    try:
        if CONFIG_FILE.exists():
            config = configparser.ConfigParser(interpolation=None)
            config.read(CONFIG_FILE, encoding="utf-8")
            section = config["application"] if config.has_section("application") else {}
            settings.update({key: section.get(key, default) for key, default in settings.items()})
        else:
            for key, path in LEGACY_FILES.items():
                if path.exists():
                    settings[key] = path.read_text(encoding="utf-8").strip() or settings[key]
    except (OSError, UnicodeError, configparser.Error):
        pass
    if settings["mode"] not in ("track", "playlist"):
        settings["mode"] = "track"
    if settings["quality"] not in QUALITY_OPTIONS:
        settings["quality"] = QUALITY_OPTIONS[0]
    return settings


def save_settings(destination, mode, quality):
    config = configparser.ConfigParser(interpolation=None)
    config["application"] = {
        "destination": destination.strip(),
        "mode": mode if mode in ("track", "playlist") else "track",
        "quality": quality if quality in QUALITY_OPTIONS else QUALITY_OPTIONS[0],
    }
    temporary = CONFIG_FILE.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        config.write(stream)
    temporary.replace(CONFIG_FILE)
    for path in LEGACY_FILES.values():
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def playlist_url(value, mode="track"):
    value = value.strip().replace("\\&", "&").replace("\\_", "_")
    markdown = re.fullmatch(r"\[[^\]]*\]\((https?://[^\s]+)\)", value)
    parsed = urlparse(markdown[1] if markdown else value)
    if parsed.scheme not in ("https", "http") or parsed.hostname not in (
        "youtube.com", "www.youtube.com", "music.youtube.com", "m.youtube.com",
        "youtu.be", "www.youtu.be",
    ):
        raise ValueError("Colle un lien YouTube vers une vidéo, une playlist ou un Mix.")
    query = parse_qs(parsed.query)
    playlist = query.get("list", [""])[0]
    video = query.get("v", [""])[0]
    parts = parsed.path.strip("/").split("/")
    if parsed.hostname in ("youtu.be", "www.youtu.be") and len(parts) == 1:
        video = parts[0]
    elif len(parts) == 2 and parts[0] in ("shorts", "live", "embed"):
        video = parts[1]
    if mode == "track":
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", video):
            return "https://www.youtube.com/watch?v=" + video
        raise ValueError("Mode Morceau : colle le lien d’une vidéo, ou choisis Playlist / Mix.")
    if playlist:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", playlist):
            raise ValueError("L’identifiant de la playlist est invalide.")
        if playlist.startswith("RD"):
            if not video and re.fullmatch(r"RD[A-Za-z0-9_-]{11}", playlist):
                video = playlist[2:]
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video):
                raise ValueError("Pour ce Mix, copie le lien depuis la vidéo en lecture (avec v= et list=).")
            return f"https://www.youtube.com/watch?v={video}&list={playlist}"
        return "https://www.youtube.com/playlist?list=" + playlist
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", video):
        return "https://www.youtube.com/watch?v=" + video
    raise ValueError("Lien incomplet : copie le lien de partage de la vidéo ou de la playlist.")


def extract_urls(value, mode):
    clean_value = value.replace("\\&", "&").replace("\\_", "_")
    candidates = YOUTUBE_URL.findall(clean_value)
    if not candidates and clean_value.strip():
        candidates = [clean_value.strip()]
    urls = []
    for candidate in candidates:
        normalized = playlist_url(candidate.rstrip(".,;"), mode)
        if normalized not in urls:
            urls.append(normalized)
    return urls


def find_tool(name):
    filename = name + ".exe" if sys.platform == "win32" else name
    bundled = APP_DIR / filename
    return str(bundled) if bundled.exists() else shutil.which(name)


def downloader_command():
    if FROZEN:
        executable = find_tool("yt-dlp")
        if not executable:
            raise RuntimeError("yt-dlp.exe est absent. Réinstalle l’application.")
        return [executable]
    return [sys.executable, "-m", "yt_dlp"]

def download_command(url, folder, runtime, quality="320 kb/s"):
    is_playlist = bool(parse_qs(urlparse(url).query).get("list"))
    playlist_id = parse_qs(urlparse(url).query).get("list", [""])[0]
    bitrate = quality.split()[0] + "K" if quality in QUALITY_OPTIONS else "320K"
    ffmpeg = find_tool("ffmpeg")
    return [
        *downloader_command(), "--ignore-config", "--yes-playlist" if is_playlist else "--no-playlist",
        *([] if is_playlist else ["--playlist-items", "1"]),
        "--progress", "--progress-delta", "0.2",
        "--progress-template", "download:MP3_PROGRESS|%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
        "--print", "after_move:MP3_COMPLETE", "--no-simulate", "--no-quiet",
        "--js-runtimes", runtime, "--no-abort-on-error", "--newline", "--no-color",
        *(["--ffmpeg-location", str(Path(ffmpeg).parent)] if ffmpeg else []),
        "--windows-filenames", "--trim-filenames", "160", "--socket-timeout", "30",
        "-f", "bestaudio/best", "-x", "--audio-format", "mp3",
        "--audio-quality", bitrate, "--embed-metadata", "--embed-thumbnail",
        "--convert-thumbnails", "jpg",
        "--postprocessor-args",
        "ThumbnailsConvertor+ffmpeg_o:-vf scale=600:600:force_original_aspect_ratio=increase,crop=600:600 -q:v 4",
        "--parse-metadata", "%(artist,creator,uploader)s:%(meta_artist)s",
        "--parse-metadata", "%(track,title)s:%(meta_title)s",
        "--parse-metadata", "%(title)s:%(meta_artist)s - %(meta_title)s",
        "--parse-metadata", "%(album,playlist_title)s:%(meta_album)s",
        "--parse-metadata", "%(playlist_index)s:%(meta_track)s",
        "--replace-in-metadata", "meta_title",
        r"(?i)\s*[\[(](official\s+(music\s+)?video|official\s+audio|lyrics?|visuali[sz]er)[\])]\s*$", "",
        "--no-overwrites",
        *(["--download-archive", str(folder / f"historique-{playlist_id}.txt")] if is_playlist else []),
        "-P", str(folder), "-o", "%(playlist_title).80s/%(title)s.%(ext)s" if is_playlist else "%(title)s.%(ext)s",
        *( ["--playlist-end", "50"] if parse_qs(urlparse(url).query).get("list", [""])[0].startswith("RD") else [] ),
        "--", url,
    ]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube → MP3")
        self.geometry("780x650")
        self.minsize(600, 400)
        icon_path = RESOURCE_DIR / "app_icon.png"
        if icon_path.exists():
            try:
                self.app_icon = tk.PhotoImage(file=str(icon_path))
                self.iconphoto(True, self.app_icon)
            except tk.TclError:
                self.app_icon = None
        self.events = queue.Queue()
        self.pending_lock = threading.Lock()
        self.pending_urls = []
        self.queued_urls = set()
        self.worker_index = 0
        self.running = False
        self.process = None
        self.stop_requested = False
        self.queue_index = 1
        self.queue_total = 1
        settings = load_settings()
        self.mode = tk.StringVar(value=settings["mode"])
        self.quality = tk.StringVar(value=settings["quality"])
        self.folder = tk.StringVar(value=settings["destination"])
        self.save_job = None
        self.folder.trace_add("write", self.schedule_save)
        self.mode.trace_add("write", self.schedule_save)
        self.quality.trace_add("write", self.schedule_save)
        panel = ttk.Frame(self, padding=18)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="Télécharger une vidéo ou playlist en MP3", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(panel, text="Meilleur audio disponible • Qualité MP3 réglable • Reprise automatique").pack(anchor="w", pady=(4, 16))
        modes = ttk.Frame(panel)
        modes.pack(fill="x", pady=(0, 10))
        self.track_mode = ttk.Radiobutton(modes, text="Morceau (une seule vidéo)", variable=self.mode, value="track")
        self.track_mode.pack(side="left")
        self.playlist_mode = ttk.Radiobutton(modes, text="Playlist / Mix", variable=self.mode, value="playlist")
        self.playlist_mode.pack(side="left", padx=18)
        quality_row = ttk.Frame(panel)
        quality_row.pack(fill="x", pady=(0, 10))
        ttk.Label(quality_row, text="Qualité MP3 :").pack(side="left")
        self.quality_box = ttk.Combobox(
            quality_row, textvariable=self.quality, values=QUALITY_OPTIONS,
            state="readonly", width=12,
        )
        self.quality_box.pack(side="left", padx=(8, 0))
        ttk.Label(panel, text="Liens YouTube — un lien par ligne").pack(anchor="w")
        self.url_input = ScrolledText(panel, height=4, wrap="word")
        self.url_input.pack(fill="x", pady=(4, 12))
        ttk.Label(panel, text="Pendant le traitement, colle d’autres liens puis clique sur Ajouter à la file.").pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(panel)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.folder).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Parcourir…", command=self.browse).pack(side="right", padx=(8, 0))
        actions = ttk.Frame(panel)
        actions.pack(fill="x", pady=14)
        self.start_button = ttk.Button(actions, text="Télécharger en MP3", command=self.start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(actions, text="Arrêter", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=(10, 0))
        self.progress = ttk.Progressbar(panel, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 10))
        self.completed = 0
        self.total = 1
        self.current = 1
        self.item_completed = False
        self.status = tk.StringVar(value="Prêt")
        self.track = ""
        ttk.Label(panel, textvariable=self.status).pack(anchor="w", pady=(0, 8))
        self.log = ScrolledText(panel, height=12, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True)
        ttk.Label(panel, text="Le débit choisi ne peut pas améliorer la qualité de la source. Contenus autorisés uniquement.").pack(anchor="w", pady=(10, 0))
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(100, self.poll)

    def schedule_save(self, *_):
        if self.save_job is not None:
            self.after_cancel(self.save_job)
        self.save_job = self.after(500, self.persist_destination)

    def persist_destination(self):
        self.save_job = None
        try:
            save_settings(self.folder.get(), self.mode.get(), self.quality.get())
        except OSError as error:
            self.events.put(("log", f"Dossier non mémorisé : {error}\n"))

    def mark_completed(self):
        if not self.item_completed:
            self.item_completed = True
            self.completed += 1
        self.set_progress(100 * self.completed / max(self.total, 1))

    def set_progress(self, link_percent):
        self.current_link_percent = min(100, max(0, link_percent))
        total_percent = 100 * (
            (self.queue_index - 1) + self.current_link_percent / 100
        ) / max(self.queue_total, 1)
        self.progress.configure(value=total_percent)
        return total_percent

    def browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder.set(folder)
            self.persist_destination()

    def start(self):
        if self.running:
            self.add_to_queue()
            return
        try:
            urls = extract_urls(self.url_input.get("1.0", "end"), self.mode.get())
            if not urls:
                raise ValueError("Colle au moins un lien YouTube.")
            if not self.folder.get().strip():
                raise ValueError("Choisis un dossier de destination.")
            folder = Path(self.folder.get()).expanduser().resolve()
            if FROZEN and not find_tool("yt-dlp"):
                raise ValueError("yt-dlp est absent. Relance Installer.bat.")
            if not FROZEN and importlib.util.find_spec("yt_dlp") is None:
                raise ValueError("Installe les dépendances : python -m pip install -r requirements.txt")
            if not find_tool("ffmpeg") or not find_tool("ffprobe"):
                raise ValueError("FFmpeg est absent. Relance Installer.bat.")
            runtime_path = next((find_tool(name) for name in ("deno", "node") if find_tool(name)), None)
            if not runtime_path:
                raise ValueError("Le moteur JavaScript est absent. Réinstalle l’application.")
            runtime_name = Path(runtime_path).stem.lower()
            runtime = f"{runtime_name}:{runtime_path}"
            folder.mkdir(parents=True, exist_ok=True)
        except (ValueError, OSError) as error:
            messagebox.showerror("Impossible de démarrer", str(error))
            return
        if any(parse_qs(urlparse(url).query).get("list", [""])[0].startswith("RD") for url in urls):
            self.events.put(("log", "Les Mix YouTube sont limités aux 50 premiers morceaux.\n"))
        self.running = True
        self.stop_requested = False
        self.start_button.configure(text="Ajouter à la file", state="normal")
        self.stop_button.configure(state="normal")
        self.track_mode.configure(state="disabled")
        self.playlist_mode.configure(state="disabled")
        self.quality_box.configure(state="disabled")
        self.persist_destination()
        self.progress.configure(value=0)
        self.completed = 0
        self.total = 1
        self.current = 1
        self.queue_index = 1
        self.queue_total = len(urls)
        self.current_link_percent = 0
        self.pending_urls = list(urls)
        self.queued_urls = set(urls)
        self.worker_index = 0
        self.item_completed = False
        self.track = ""
        self.status.set(f"Préparation de {len(urls)} lien(s)…")
        self.events.put(("log", f"Destination : {folder}\nFile d’attente : {len(urls)} lien(s)\n"))
        self.url_input.delete("1.0", "end")
        threading.Thread(
            target=self.download_queue,
            args=(folder, runtime, self.quality.get()), daemon=True,
        ).start()

    def add_to_queue(self):
        try:
            urls = extract_urls(self.url_input.get("1.0", "end"), self.mode.get())
            if not urls:
                raise ValueError("Colle au moins un nouveau lien YouTube.")
        except ValueError as error:
            messagebox.showerror("Impossible d’ajouter", str(error))
            return
        with self.pending_lock:
            new_urls = [url for url in urls if url not in self.queued_urls]
            self.pending_urls.extend(new_urls)
            self.queued_urls.update(new_urls)
            self.queue_total += len(new_urls)
            queue_total = self.queue_total
        self.url_input.delete("1.0", "end")
        if new_urls:
            self.events.put(("queue_size", (queue_total, len(new_urls))))
        else:
            messagebox.showinfo("Déjà présent", "Ce lien est déjà dans la file d’attente.")

    def download_queue(self, folder, runtime, quality):
        final_code = 0
        while True:
            with self.pending_lock:
                if not self.pending_urls:
                    break
                url = self.pending_urls.pop(0)
                self.worker_index += 1
                index = self.worker_index
                queue_total = self.queue_total
            if self.stop_requested:
                final_code = 1
                break
            self.events.put(("job", (index, queue_total)))
            self.events.put(("log", f"\n=== Lien {index} / {queue_total} ===\n{url}\n"))
            code = self.download_one(url, folder, runtime, quality)
            if code != 0:
                final_code = code
            if self.stop_requested:
                break
        if self.stop_requested:
            result = "Téléchargement arrêté. Un fichier partiel peut être repris plus tard."
        elif final_code == 0:
            result = f"Terminé. {self.worker_index} lien(s) traité(s)."
        else:
            result = "File terminée avec des erreurs. Consulte le journal."
        self.events.put(("log", result + "\n"))
        self.events.put(("done", final_code))

    def download_one(self, url, folder, runtime, quality):
        code = 1
        try:
            if self.stop_requested:
                return code
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "utf-8"
            environment["PYTHONUTF8"] = "1"
            with subprocess.Popen(
                download_command(url, folder, runtime, quality), stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                errors="replace", creationflags=flags, env=environment,
            ) as process:
                self.process = process
                if self.stop_requested:
                    self.terminate_process(process)
                for line in process.stdout:
                    self.events.put(("log", line))
                code = process.wait()
        except Exception as error:
            self.events.put(("log", f"Erreur : {error}\n"))
        finally:
            self.process = None
        return code

    def notify(self, title, message):
        try:
            if sys.platform == "win32":
                from winotify import Notification, audio
                toast = Notification(app_id="YouTube vers MP3", title=title, msg=message)
                toast.set_audio(audio.Default, loop=False)
                toast.show()
            else:
                self.bell()
        except Exception:
            self.bell()

    def terminate_process(self, process):
        if process.poll() is not None:
            return
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW, check=False,
                )
                if process.poll() is None:
                    process.kill()
            else:
                process.terminate()
        except OSError as error:
            self.events.put(("log", f"Impossible d’arrêter le processus : {error}\n"))

    def stop(self):
        if not self.running or self.stop_requested:
            return
        self.stop_requested = True
        self.stop_button.configure(state="disabled")
        self.status.set("Arrêt en cours…")
        process = self.process
        if process is not None:
            threading.Thread(target=self.terminate_process, args=(process,), daemon=True).start()

    def poll(self):
        for _ in range(200):
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "job":
                self.queue_index, self.queue_total = value
                self.completed = 0
                self.total = 1
                self.current = 1
                self.item_completed = False
                self.track = f"Lien {self.queue_index} / {self.queue_total}"
                total_percent = self.set_progress(0)
                self.status.set(f"{self.track} — analyse • progression totale {total_percent:.1f} %")
            elif kind == "queue_size":
                self.queue_total, added = value
                self.track = re.sub(
                    r"Lien \d+ / \d+",
                    f"Lien {self.queue_index} / {self.queue_total}", self.track,
                )
                total_percent = self.set_progress(self.current_link_percent)
                self.status.set(
                    f"{added} lien(s) ajouté(s) • {self.queue_total} au total • "
                    f"progression {total_percent:.1f} %"
                )
                self.events.put(("log", f"Ajout à la file : {added} lien(s), total {self.queue_total}.\n"))
            elif kind == "done":
                was_stopped = self.stop_requested
                self.running = False
                self.stop_requested = False
                self.start_button.configure(text="Télécharger en MP3", state="normal")
                self.stop_button.configure(state="disabled")
                self.track_mode.configure(state="normal")
                self.playlist_mode.configure(state="normal")
                self.quality_box.configure(state="readonly")
                self.progress.stop()
                if was_stopped:
                    self.status.set("Téléchargement arrêté.")
                elif value == 0:
                    self.progress.configure(value=100)
                    self.status.set("Terminé — tous les fichiers ont été traités.")
                    self.notify("Téléchargement terminé", "Tous les MP3 sont prêts dans le dossier choisi.")
                else:
                    self.status.set("Terminé avec des erreurs — consulte le journal.")
                    self.notify("Téléchargement terminé avec des erreurs", "Consulte le journal de l’application.")
            else:
                item = re.search(r"Downloading item (\d+) of (\d+)", value)
                if item:
                    self.current = int(item[1])
                    self.total = int(item[2])
                    self.item_completed = False
                    self.track = (
                        f"Lien {self.queue_index} / {self.queue_total} • "
                        f"Morceau {item[1]} / {item[2]}"
                    )
                    link_percent = 100 * (self.current - 1) / max(self.total, 1)
                    total_percent = self.set_progress(link_percent)
                    self.status.set(f"{self.track} — préparation • progression totale {total_percent:.1f} %")
                elif value.startswith("MP3_PROGRESS|"):
                    fields = value.strip().split("|")
                    percent = re.search(r"(\d+(?:\.\d+)?)%", fields[1])
                    if percent:
                        amount = min(100, float(percent[1]))
                        link_percent = 100 * ((self.current - 1) + amount / 100) / max(self.total, 1)
                        total_percent = self.set_progress(link_percent)
                        speed = fields[2].strip() if len(fields) > 2 else "?"
                        eta = fields[3].strip() if len(fields) > 3 else "?"
                        self.status.set(
                            f"{self.track} — téléchargement {amount:.1f} % • "
                            f"total {total_percent:.1f} % • {speed} • reste {eta}"
                        )
                    else:
                        self.status.set(self.track + " — téléchargement, taille inconnue")
                    continue
                elif value.strip() == "MP3_COMPLETE":
                    self.mark_completed()
                    link_percent = 100 * self.completed / max(self.total, 1)
                    total_percent = self.set_progress(link_percent)
                    self.status.set(f"{self.track} — MP3 terminé • progression totale {total_percent:.1f} %")
                    continue
                elif "has already been recorded in the archive" in value:
                    self.mark_completed()
                    self.status.set(self.track + " — déjà téléchargé")
                elif any(tag in value for tag in (
                    "[ExtractAudio]", "[Metadata]", "[ThumbnailsConvertor]", "[EmbedThumbnail]",
                )):
                    link_percent = 100 * self.current / max(self.total, 1)
                    total_percent = self.set_progress(link_percent)
                    step = (
                        "préparation et intégration de la pochette"
                        if "Thumbnail" in value else "conversion MP3 / métadonnées"
                    )
                    self.status.set(
                        f"{self.track} — {step} • "
                        f"progression totale {total_percent:.1f} %"
                    )
                self.log.configure(state="normal")
                self.log.insert("end", value)
                if int(self.log.index("end-1c").split(".")[0]) > 1500:
                    self.log.delete("1.0", "300.0")
                self.log.see("end")
                self.log.configure(state="disabled")
        self.after(100, self.poll)

    def close(self):
        if self.running:
            messagebox.showinfo("Téléchargement en cours", "Attends la fin du téléchargement avant de fermer.")
        else:
            self.persist_destination()
            self.destroy()


if __name__ == "__main__":
    App().mainloop()
