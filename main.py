from __future__ import annotations

import argparse
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests


DEFAULT_AUTH_FILE = Path("config/auth.toml")
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


@dataclass(frozen=True)
class AuthConfig:
    site_url: str
    login_id: str
    password: str


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


def login(auth: AuthConfig) -> requests.Session:
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

    return session


def is_login_failure(response: requests.Response) -> bool:
    if "CODE=002" in response.url:
        return True

    return any(marker in response.text for marker in LOGIN_FAILURE_MARKERS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Log in to shane-timetotalk.jp and prepare an authenticated session."
    )
    parser.add_argument(
        "--auth-file",
        type=Path,
        default=DEFAULT_AUTH_FILE,
        help=f"Path to auth TOML file. Default: {DEFAULT_AUTH_FILE}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        auth = load_auth_config(args.auth_file)
        login(auth)
    except (ConfigError, LoginError, requests.RequestException) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print("Login succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
