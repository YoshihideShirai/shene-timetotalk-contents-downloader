from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


DEFAULT_INPUT_DIR = Path("downloads")
DEFAULT_AUDIO_DIR = Path("android-music")
ALL_TRACKS_PLAYLIST = "All Tracks.m3u8"
RIGHTS_HOLDER = "Shane English School"
ALBUM_TITLE_PREFIX = "Time to Talk"


@dataclass(frozen=True)
class Track:
    path: Path
    title: str
    number: int


class FfmpegNotFoundError(RuntimeError):
    pass


def natural_track_number(path: Path) -> int:
    number = track_number_from_title(path.stem)
    if number is not None:
        return number

    return 10**9


def track_number_from_title(title: str) -> int | None:
    match = re.search(r"Track\s+(\d+)", title)
    if match:
        return int(match.group(1))

    return None


def metadata_track_number(path: Path) -> int:
    number = track_number_from_title(path.stem)
    if number is None:
        return 0

    return number


def album_title(album_dir_name: str) -> str:
    if album_dir_name.startswith(ALBUM_TITLE_PREFIX):
        return album_dir_name

    return f"{ALBUM_TITLE_PREFIX} {album_dir_name}"


def read_m4a_metadata(ffprobe: str, path: Path) -> dict[str, str]:
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format_tags",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return {}

    try:
        metadata = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}

    tags = metadata.get("format", {}).get("tags", {})
    return {str(key).lower(): str(value) for key, value in tags.items()}


def should_convert_m4a(
    mp4_path: Path,
    output_path: Path,
    expected_metadata: dict[str, str],
    ffprobe: str | None,
) -> bool:
    if not output_path.exists():
        return True

    if output_path.stat().st_mtime < mp4_path.stat().st_mtime:
        return True

    if ffprobe is None:
        return True

    current_metadata = read_m4a_metadata(ffprobe, output_path)
    return any(
        current_metadata.get(key.lower()) != value
        for key, value in expected_metadata.items()
    )


def find_album_tracks(input_dir: Path, suffix: str) -> dict[Path, list[Track]]:
    albums: dict[Path, list[Track]] = {}

    for path in sorted(input_dir.glob(f"*/*{suffix}")):
        if not path.is_file():
            continue

        album_dir = path.parent
        track = Track(
            path=path,
            title=f"{album_dir.name} - {path.stem}",
            number=natural_track_number(path),
        )
        albums.setdefault(album_dir, []).append(track)

    for tracks in albums.values():
        tracks.sort(key=lambda track: (track.number, track.path.name))

    return dict(sorted(albums.items(), key=lambda item: item[0].name))


def convert_mp4_to_m4a(input_dir: Path, audio_dir: Path) -> list[Path]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FfmpegNotFoundError(
            "ffmpeg is required to create Android music files. "
            "Install ffmpeg and run this script again."
        )
    ffprobe = shutil.which("ffprobe")

    mp4_paths = sorted(input_dir.glob("*/*.mp4"))
    if not mp4_paths:
        raise FileNotFoundError(f"No mp4 files found under: {input_dir}")

    album_track_counts: dict[Path, int] = {}
    for mp4_path in mp4_paths:
        album_track_counts[mp4_path.parent] = album_track_counts.get(mp4_path.parent, 0) + 1

    output_paths = []
    for mp4_path in mp4_paths:
        relative_path = mp4_path.relative_to(input_dir).with_suffix(".m4a")
        output_path = audio_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        total_tracks = album_track_counts[mp4_path.parent]
        expected_metadata = {
            "title": mp4_path.stem,
            "album": album_title(mp4_path.parent.name),
            "artist": RIGHTS_HOLDER,
            "album_artist": RIGHTS_HOLDER,
            "copyright": RIGHTS_HOLDER,
            "track": f"{metadata_track_number(mp4_path)}/{total_tracks}",
        }

        if not should_convert_m4a(mp4_path, output_path, expected_metadata, ffprobe):
            output_paths.append(output_path)
            continue

        temporary_path = output_path.with_name(output_path.stem + ".part.m4a")
        command = [
            ffmpeg,
            "-y",
            "-i",
            str(mp4_path),
            "-vn",
            "-c:a",
            "copy",
            "-metadata",
            f"title={expected_metadata['title']}",
            "-metadata",
            f"album={expected_metadata['album']}",
            "-metadata",
            f"artist={expected_metadata['artist']}",
            "-metadata",
            f"album_artist={expected_metadata['album_artist']}",
            "-metadata",
            f"copyright={expected_metadata['copyright']}",
            "-metadata",
            f"track={expected_metadata['track']}",
            str(temporary_path),
        ]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        temporary_path.replace(output_path)
        output_paths.append(output_path)

    return output_paths


def format_m3u_entry(track: Track, playlist_path: Path) -> str:
    relative_path = track.path.relative_to(playlist_path.parent).as_posix()
    return f"#EXTINF:-1,{track.title}\n{relative_path}\n"


def write_playlist(path: Path, tracks: list[Track]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "#EXTM3U\n" + "".join(format_m3u_entry(track, path) for track in tracks)
    path.write_text(content, encoding="utf-8", newline="\n")


def create_playlists(input_dir: Path, audio_dir: Path, convert: bool) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    playlist_input_dir = audio_dir if convert else input_dir
    suffix = ".m4a" if convert else ".mp4"

    if convert:
        convert_mp4_to_m4a(input_dir, audio_dir)

    albums = find_album_tracks(playlist_input_dir, suffix)
    if not albums:
        raise FileNotFoundError(f"No {suffix} files found under: {playlist_input_dir}")

    playlist_paths = []
    all_tracks = []
    for album_dir, tracks in albums.items():
        playlist_path = album_dir / f"{album_dir.name}.m3u8"
        write_playlist(playlist_path, tracks)
        playlist_paths.append(playlist_path)
        all_tracks.extend(tracks)

    all_tracks_path = playlist_input_dir / ALL_TRACKS_PLAYLIST
    write_playlist(all_tracks_path, all_tracks)
    playlist_paths.append(all_tracks_path)

    return playlist_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create Android-friendly M3U8 playlists for downloaded MP4 tracks."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Directory containing downloaded album folders. Default: {DEFAULT_INPUT_DIR}",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=DEFAULT_AUDIO_DIR,
        help=f"Directory to write Android music files and playlists. Default: {DEFAULT_AUDIO_DIR}",
    )
    parser.add_argument(
        "--no-convert",
        action="store_true",
        help="Skip mp4 to m4a conversion and create playlists for existing mp4 files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        playlist_paths = create_playlists(
            input_dir=args.input_dir,
            audio_dir=args.audio_dir,
            convert=not args.no_convert,
        )
    except (FfmpegNotFoundError, OSError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}")
        return 1

    print(f"Created {len(playlist_paths)} playlist(s).")
    for playlist_path in playlist_paths:
        print(f"- {playlist_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
