# YouTube MP3

<p align="center">
  <img src="app_icon.png" alt="YouTube MP3" width="120">
</p>

<p align="center">
  <strong>Téléchargez vos vidéos et playlists YouTube autorisées en MP3.</strong><br>
  Une application simple, rapide et accessible à tous.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Windows-10%2B-0078D6?logo=windows&logoColor=white">
  <img src="https://img.shields.io/badge/Audio-MP3-orange">
</p>

## Aperçu

<p align="center">
  <img src="capture.png" alt="Interface de YouTube MP3" width="750">
</p>

## Présentation

YouTube MP3 est une application graphique permettant de convertir des vidéos YouTube en fichiers MP3.

Elle récupère automatiquement, lorsque les informations sont disponibles, le titre, l’artiste, les métadonnées et la pochette de l’album.

L’application propose deux modes :

- **Morceau** : télécharge une seule vidéo ;
- **Playlist / Mix** : télécharge une playlist complète ou un Mix YouTube.

## Fonctionnalités

- Téléchargement d’un ou plusieurs liens YouTube.
- Prise en charge des vidéos, playlists et Mix.
- File d’attente de téléchargement.
- Ajout de liens pendant un téléchargement.
- Bouton d’arrêt.
- Barre de progression avec pourcentage, vitesse et temps restant.
- Qualité MP3 sélectionnable : 128, 192, 256 ou 320 kb/s.
- Nettoyage automatique des noms de fichiers.
- Métadonnées et pochette intégrées dans les fichiers MP3.
- Notifications à la fin du téléchargement.
- Destination et préférences conservées automatiquement.

## Installation sous Windows

Cette méthode est destinée aux utilisateurs qui veulent simplement utiliser l’application. Aucun logiciel de programmation n’est nécessaire.

1. Dans la page **Releases** de GitHub, téléchargez `YouTube-MP3-Windows.zip`.
2. Ouvrez le dossier **Téléchargements**.
3. Faites un clic droit sur le fichier ZIP, puis choisissez **Extraire tout**.
4. Ouvrez le nouveau dossier extrait.
5. Double-cliquez sur **`Installer.bat`**.
6. Attendez la fin de l’installation. Une fenêtre indique quand elle est terminée.
7. Lancez ensuite l’application avec le raccourci **YouTube MP3** créé sur le Bureau.

L’installateur télécharge automatiquement **yt-dlp**, **FFmpeg** et **Deno**. Il ne demande pas les droits administrateur et peut être relancé pour réparer une installation.

Conservez `YouTube MP3.exe`, `Installer.bat` et `Installer.ps1` dans le même dossier. Python n’est pas nécessaire : il est intégré dans l’exécutable et aucune fenêtre console ne s’affiche.

## Utilisation

1. Sélectionnez le mode **Morceau** ou **Playlist / Mix**.
2. Collez un ou plusieurs liens YouTube.
3. Choisissez le dossier de destination.
4. Sélectionnez la qualité audio.
5. Cliquez sur **Télécharger**.

### Mode Morceau

En mode **Morceau**, un lien contenant un Mix automatique reste limité à une seule vidéo :

```text
https://www.youtube.com/watch?v=VIDEO_ID&list=RDVIDEO_ID&start_radio=1
```

Même avec les paramètres `list=RD...` et `start_radio=1`, seule la vidéo indiquée est téléchargée.

### Mode Playlist / Mix

En mode **Playlist / Mix**, l’application traite les éléments de la playlist les uns après les autres. De nouveaux liens peuvent être ajoutés pendant le traitement.

## Qualité audio

Le débit choisi correspond à la qualité maximale d’encodage du fichier MP3.

Une source YouTube qui ne fournit pas réellement 320 kb/s ne peut pas être améliorée artificiellement. Choisir 320 kb/s évite simplement de réduire davantage la qualité lors de la conversion.

## Lancer depuis le code source

Python 3.10 ou supérieur est requis.

```powershell
python -m pip install -r requirements.txt
python app.py
```

Sous Windows, `pythonw.exe app.py` permet de lancer l’application sans console. FFmpeg et Deno ou Node.js doivent également être disponibles.

## Structure du projet

```text
app.py
Installer.bat
Installer.ps1
app_icon.png
capture.png
requirements.txt
LICENSE
README.md
THIRD_PARTY_NOTICES.txt
```

## Dépannage

### Une dépendance est absente

Relancez `Installer.bat` dans le dossier où se trouve `YouTube MP3.exe`.

### Plusieurs morceaux sont téléchargés

Vérifiez que le mode **Morceau** est sélectionné avant de démarrer le téléchargement.

### Le titre ou la pochette est incorrect

Les informations dépendent des données disponibles pour la vidéo YouTube.

### Le téléchargement échoue

La vidéo peut être indisponible, privée, supprimée ou limitée par YouTube.

## Composants utilisés

- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://ffmpeg.org/)
- [Deno](https://github.com/denoland/deno)
- [Python](https://www.python.org/)
- [Tkinter](https://docs.python.org/3/library/tkinter.html)

Les informations de licence sont disponibles dans [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

## Licence

Ce projet est distribué sous licence MIT.

Utilisez cette application uniquement pour les contenus que vous êtes autorisé à télécharger et dans le respect des conditions d’utilisation du service concerné.
