from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree

import requests


DEFAULT_AUTH_FILE = Path("config/auth.toml")
DEFAULT_OUTPUT_DIR = Path("downloads")
DEFAULT_SECTION_PREFIX = "CD Audio"
DEFAULT_AUDIO_PREFIX = "Audio"
LOGIN_PATH = "src/login.php"
LOGIN_FAILURE_MARKERS = (
    "ログインできませんでした",
    "ログインに失敗しました",
    "IDとパスワードをお確かめください",
)


class ConfigError(RuntimeError):
    pass


class LoginError(RuntimeError):
    pass


class DownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuthConfig:
    site_url: str
    login_id: str
    password: str


@dataclass(frozen=True)
class LoginResult:
    session: requests.Session
    landing_url: str
    landing_html: str


@dataclass(frozen=True)
class Link:
    href: str
    text: str


@dataclass(frozen=True)
class ResolvedLink:
    url: str
    text: str


class ShaneHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[Link] = []
        self.frames: list[dict[str, str]] = []
        self._href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: value or "" for name, value in attrs}
        if tag == "a" and attr_map.get("href"):
            self._href = attr_map["href"]
            self._text_parts = []
        elif tag == "frame":
            self.frames.append(attr_map)

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._href is None:
            return

        text = " ".join("".join(self._text_parts).split())
        self.links.append(Link(href=self._href, text=text))
        self._href = None
        self._text_parts = []


def load_auth_config(path: Path) -> AuthConfig:
    if not path.exists():
        raise ConfigError(
            f"Auth config not found: {path}\n"
            "Create it with: cp config/auth.example.toml config/auth.toml"
        )

    with path.open("rb") as file:
        data = tomllib.load(file)

    section = data.get("shane_timetotalk")
    if not isinstance(section, dict):
        raise ConfigError("Missing [shane_timetotalk] section in auth config.")

    missing_keys = [
        key
        for key in ("site_url", "login_id", "password")
        if not str(section.get(key, "")).strip()
    ]
    if missing_keys:
        raise ConfigError(f"Missing auth config value(s): {', '.join(missing_keys)}")

    return AuthConfig(
        site_url=str(section["site_url"]).strip(),
        login_id=str(section["login_id"]).strip(),
        password=str(section["password"]),
    )


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            ),
        }
    )
    return session


def login(auth: AuthConfig) -> LoginResult:
    session = create_session()

    top_response = session.get(auth.site_url, timeout=30)
    top_response.raise_for_status()

    login_url = urljoin(auth.site_url, LOGIN_PATH)
    response = session.post(
        login_url,
        data={"uid": auth.login_id, "pwd": auth.password},
        headers={"Referer": auth.site_url},
        timeout=30,
        allow_redirects=True,
    )
    response.raise_for_status()

    if is_login_failure(response):
        raise LoginError("Login failed. Please check config/auth.toml.")

    return LoginResult(
        session=session,
        landing_url=response.url,
        landing_html=response.text,
    )


def is_login_failure(response: requests.Response) -> bool:
    if "CODE=002" in response.url:
        return True

    return any(marker in response.text for marker in LOGIN_FAILURE_MARKERS)


def download_track(
    login_result: LoginResult,
    section_prefix: str,
    audio_prefix: str,
    track_number: int,
    output_dir: Path,
) -> Path:
    session = login_result.session
    section_link = find_link_by_prefix(
        html=login_result.landing_html,
        base_url=login_result.landing_url,
        link_prefix=section_prefix,
    )
    section_response = session.get(section_link.url, timeout=30)
    section_response.raise_for_status()

    audio_link = find_link_by_prefix(
        html=section_response.text,
        base_url=section_response.url,
        link_prefix=audio_prefix,
    )
    track_url = find_track_url(session, audio_link.url, track_number)
    api_url = find_api_frame_url(session, track_url)
    content_url = find_content_url(session, api_url, track_url)
    source_url = find_mp4_source_url(session, content_url)

    output_path = output_dir / safe_filename(audio_link.text) / f"Track {track_number}.mp4"
    download_file(session, source_url, output_path, referer=content_url)
    return output_path


def find_link_by_prefix(html: str, base_url: str, link_prefix: str) -> ResolvedLink:
    parser = ShaneHtmlParser()
    parser.feed(html)

    for link in parser.links:
        if link.text.startswith(link_prefix):
            return ResolvedLink(url=urljoin(base_url, link.href), text=link.text)

    raise DownloadError(f"Link starting with {link_prefix!r} was not found.")


def find_track_url(
    session: requests.Session,
    page_url: str,
    track_number: int,
) -> str:
    response = session.get(page_url, timeout=30)
    response.raise_for_status()

    parser = ShaneHtmlParser()
    parser.feed(response.text)

    track_text = f"Track {track_number}"
    for link in parser.links:
        if link.text == track_text:
            return urljoin(response.url, link.href)

    raise DownloadError(f"{track_text} link was not found.")


def find_api_frame_url(session: requests.Session, track_url: str) -> str:
    response = session.get(track_url, timeout=30)
    response.raise_for_status()

    parser = ShaneHtmlParser()
    parser.feed(response.text)

    for frame in parser.frames:
        if frame.get("name") == "apiFrame" and frame.get("src"):
            return urljoin(response.url, frame["src"])

    raise DownloadError("apiFrame was not found in the track page.")


def find_content_url(
    session: requests.Session,
    api_url: str,
    track_url: str,
) -> str:
    response = session.get(api_url, headers={"Referer": track_url}, timeout=30)
    response.raise_for_status()

    match = re.search(r"contentFrame\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", response.text)
    if not match:
        raise DownloadError("Content URL was not found in the SCORM API page.")

    return urljoin(response.url, match.group(1))


def find_mp4_source_url(session: requests.Session, content_url: str) -> str:
    response = session.get(content_url, timeout=30)
    response.raise_for_status()

    match = re.search(r"\.init\(['\"]([^'\"]+)['\"]\)", response.text)
    if not match:
        raise DownloadError("param.xml URL was not found in the content page.")

    param_url = urljoin(response.url, match.group(1))
    param_response = session.get(param_url, headers={"Referer": content_url}, timeout=30)
    param_response.raise_for_status()

    xml_text = param_response.text.lstrip("\ufeff")
    root = ElementTree.fromstring(xml_text)
    source = root.findtext("source")
    if not source:
        raise DownloadError("MP4 source was not found in param.xml.")

    return urljoin(param_response.url, source)


def download_file(
    session: requests.Session,
    url: str,
    output_path: Path,
    referer: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".part")

    with session.get(url, headers={"Referer": referer}, stream=True, timeout=60) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "video" not in content_type and "mp4" not in content_type:
            raise DownloadError(f"Unexpected content type: {content_type or 'unknown'}")

        with temporary_path.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)

    temporary_path.replace(output_path)


def safe_filename(value: str) -> str:
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value).strip()
    return filename or "download"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download CD audio content from shane-timetotalk.jp."
    )
    parser.add_argument(
        "--auth-file",
        type=Path,
        default=DEFAULT_AUTH_FILE,
        help=f"Path to auth TOML file. Default: {DEFAULT_AUTH_FILE}",
    )
    parser.add_argument(
        "--login-only",
        action="store_true",
        help="Only check whether login succeeds.",
    )
    parser.add_argument(
        "--section-prefix",
        default=DEFAULT_SECTION_PREFIX,
        help=f"Section link prefix. Default: {DEFAULT_SECTION_PREFIX}",
    )
    parser.add_argument(
        "--audio-prefix",
        default=DEFAULT_AUDIO_PREFIX,
        help=f"Audio link prefix under the selected section. Default: {DEFAULT_AUDIO_PREFIX}",
    )
    parser.add_argument(
        "--track",
        type=int,
        default=1,
        help="Track number to download. Default: 1.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save downloaded files. Default: {DEFAULT_OUTPUT_DIR}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        auth = load_auth_config(args.auth_file)
        login_result = login(auth)
        if args.login_only:
            print("Login succeeded.")
            return 0

        output_path = download_track(
            login_result=login_result,
            section_prefix=args.section_prefix,
            audio_prefix=args.audio_prefix,
            track_number=args.track,
            output_dir=args.output_dir,
        )
    except (
        ConfigError,
        LoginError,
        DownloadError,
        ElementTree.ParseError,
        requests.RequestException,
    ) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Downloaded: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
