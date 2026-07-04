# shene-timetotalk-contents-downloader

`https://shane-timetotalk.jp/` のCDオーディオコンテンツを、認証済みアカウントで取得するための個人利用向けダウンロード補助ツールです。

ログイン後の `uri` や `sid` は実行ごとに変わるため、URLを固定せず、画面上のリンク名をたどって対象コンテンツを探します。

このリポジトリは非公式ツールです。Shane Corporationおよび関連サービスの公式プロジェクトではありません。

## Features

- `requests` を使ったログイン
- コース一覧から `CD Audio` で始まるセクションを自動検出
- セクション配下の `Audio` で始まる教材を漏れなく検出
- 各教材のすべての `Track` をmp4としてダウンロード
- Android向けに `.m4a` と `.m3u8` プレイリストを作成

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- `ffmpeg`
  - Android向け `.m4a` 作成時のみ必要です。
  - mp4のままプレイリストだけ作る場合は不要です。
  - 例: `brew install ffmpeg`、`sudo apt install ffmpeg`

## Setup

依存関係をインストールします。

```bash
uv sync
```

認証情報テンプレートをコピーします。

```bash
cp config/auth.example.toml config/auth.toml
```

`config/auth.toml` を開いて、自分の認証情報に書き換えます。

```toml
[shane_timetotalk]
site_url = "https://shane-timetotalk.jp/"
login_id = "your-login-id"
password = "your-password"
```

`config/auth.toml` は実際のログインIDやパスワードを含むため、Gitにコミットしないでください。このファイルは `.gitignore` に追加済みです。

## Usage

ログインできるかだけ確認します。

```bash
uv run python main.py --login-only
```

CD Audioセクション配下にあるすべてのAudio教材の全Trackをダウンロードします。

```bash
uv run python main.py
```

保存先は以下の形式です。

```text
downloads/<教材タイトル>/Track <番号>.mp4
```

セクション名、教材名、保存先を変更したい場合は、`--section-prefix`、`--audio-prefix`、`--output-dir` を指定します。

```bash
uv run python main.py \
  --section-prefix "CD Audio" \
  --audio-prefix "Audio" \
  --output-dir downloads
```

特定のTrackだけダウンロードしたい場合は `--track` を指定します。

```bash
uv run python main.py --track 1
```

## Android Music

Androidの音楽アプリで扱いやすい `.m4a` ファイルと `.m3u8` プレイリストを作成します。

```bash
uv run python scripts/create_android_playlists.py
```

`android-music` 配下に以下が作成されます。

```text
android-music/All Tracks.m3u8
android-music/<教材タイトル>/Track <番号>.m4a
android-music/<教材タイトル>/<教材タイトル>.m3u8
```

`android-music` フォルダごとAndroid端末のMusicフォルダなどにコピーすると、対応している音楽アプリから音声ファイルとプレイリストを読み込めます。

別のフォルダを対象にする場合は `--input-dir`、出力先を変更する場合は `--audio-dir` を指定します。

```bash
uv run python scripts/create_android_playlists.py \
  --input-dir downloads \
  --audio-dir android-music
```

mp4のままプレイリストだけ作成したい場合は `--no-convert` を指定します。

```bash
uv run python scripts/create_android_playlists.py --no-convert
```

## Generated Files

以下はローカル生成物として `.gitignore` に追加されています。

- `config/auth.toml`
- `downloads/`
- `android-music/`

## Notes

- このリポジトリには認証情報、Cookie、ダウンロード済みコンテンツを含めないでください。
- このツールは、自分が正当にアクセスできる教材を個人利用の範囲で扱うための補助ツールです。
- サイトの利用規約、教材の著作権、所属組織やサービス提供者のルールに従って利用してください。
- サイト側のHTMLやSCORM構造が変わると、リンク検出やダウンロード処理が動かなくなる可能性があります。
- このツールは非公式であり、サービス提供者によるサポート対象ではありません。

## License

MIT Licenseです。詳細は [LICENSE](LICENSE) を参照してください。
