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

Audio Brown A の Track 1 をダウンロードします。

```bash
uv run python main.py
```

保存先は `downloads/Audio Brown A/Track 1.mp4` です。

ログインだけ確認したい場合は `--login-only` を指定します。

```bash
uv run python main.py --login-only
```

ログイン後のリンクは実行時に取得します。`uri` や `sid` は固定せず、リンク名で `CD Audio Brown`、`Audio Brown A`、`Track 1` の順にたどります。

認証ファイルの場所、セクション名、音声教材名、トラック番号、保存先を変更したい場合は、それぞれ `--auth-file`、`--section-title`、`--audio-title`、`--track`、`--output-dir` を指定します。

```bash
uv run python main.py \
  --auth-file config/auth.toml \
  --section-title "CD Audio Brown" \
  --audio-title "Audio Brown A" \
  --track 1 \
  --output-dir downloads
```
