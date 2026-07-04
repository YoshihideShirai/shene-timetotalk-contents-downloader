# shene-timetotalk-contents-downloader

https://shane-timetotalk.jp/ から CD オーディオコンテンツをダウンロードするためのツールです。

## 認証情報の準備

認証情報は `config/auth.toml` に保存します。

まず、テンプレートをコピーしてください。

```bash
cp config/auth.example.toml config/auth.toml
```

次に、`config/auth.toml` を開いて自分の認証情報に書き換えます。

```toml
[shane_timetotalk]
site_url = "https://shane-timetotalk.jp/"
login_id = "your-login-id"
password = "your-password"
```

`config/auth.toml` は実際のログイン ID やパスワードを含むため、Git にコミットしないでください。このファイルは `.gitignore` に追加済みです。

テンプレートの `config/auth.example.toml` には実データを入れず、設定項目の例だけを残します。

## 実行

CD Audio セクション配下にあるすべての Audio 教材の全 Track をダウンロードします。

```bash
uv run python main.py
```

保存先は `downloads/<教材タイトル>/Track <番号>.mp4` です。

ログインだけ確認したい場合は `--login-only` を指定します。

```bash
uv run python main.py --login-only
```

ログイン後のリンクは実行時に取得します。`uri` や `sid` は固定せず、コース一覧から `CD Audio` で始まるセクションを探し、その配下から `Audio` で始まる教材タイトルを漏れなく集め、それぞれのすべての `Track` をたどります。

認証ファイルの場所、セクション名の前方一致、音声教材名の前方一致、保存先を変更したい場合は、それぞれ `--auth-file`、`--section-prefix`、`--audio-prefix`、`--output-dir` を指定します。

```bash
uv run python main.py \
  --auth-file config/auth.toml \
  --section-prefix "CD Audio" \
  --audio-prefix "Audio" \
  --output-dir downloads
```

特定の Track だけダウンロードしたい場合は `--track` を指定します。

```bash
uv run python main.py --track 1
```

## Android向け音楽ファイルとプレイリスト作成

ダウンロード済みのmp4から、Androidの音楽アプリで読み込みやすい `.m4a` と `.m3u8` プレイリストを作成します。

この処理には `ffmpeg` が必要です。

```bash
uv run python scripts/create_android_playlists.py
```

`android-music` 配下に以下が作成されます。

- `android-music/All Tracks.m3u8`
- `android-music/<教材タイトル>/Track <番号>.m4a`
- `android-music/<教材タイトル>/<教材タイトル>.m3u8`

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
