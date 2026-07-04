from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_INPUT_DIR = Path("downloads")
ALL_TRACKS_PLAYLIST = "All Tracks.m3u8"


@dataclass(frozen=True)
class Track:
    path: Path
    title: str
    number: int


def natural_track_number(path: Path) -> int:
    match = re.search(r"Track\s+(\d+)", path.stem)
    if match:
        return int(match.group(1))

    return 10**9


def find_album_tracks(input_dir: Path) -> dict[Path, list[Track]]:
    albums: dict[Path, list[Track]] = {}

    for path in sorted(input_dir.glob("*/*.mp4")):
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


def format_m3u_entry(track: Track, playlist_path: Path) -> str:
    relative_path = track.path.relative_to(playlist_path.parent).as_posix()
    return f"#EXTINF:-1,{track.title}\n{relative_path}\n"


def write_playlist(path: Path, tracks: list[Track]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "#EXTM3U\n" + "".join(format_m3u_entry(track, path) for track in tracks)
    path.write_text(content, encoding="utf-8", newline="\n")


def create_playlists(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    albums = find_album_tracks(input_dir)
    if not albums:
        raise FileNotFoundError(f"No mp4 files found under: {input_dir}")

    playlist_paths = []
    all_tracks = []
    for album_dir, tracks in albums.items():
        playlist_path = album_dir / f"{album_dir.name}.m3u8"
        write_playlist(playlist_path, tracks)
        playlist_paths.append(playlist_path)
        all_tracks.extend(tracks)

    all_tracks_path = input_dir / ALL_TRACKS_PLAYLIST
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        playlist_paths = create_playlists(args.input_dir)
    except OSError as error:
        print(f"Error: {error}")
        return 1

    print(f"Created {len(playlist_paths)} playlist(s).")
    for playlist_path in playlist_paths:
        print(f"- {playlist_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
