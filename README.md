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

ログインできるか確認します。

```bash
uv run python main.py
```

認証ファイルの場所を変更したい場合は `--auth-file` を指定します。

```bash
uv run python main.py --auth-file config/auth.toml
```

成功すると `Login succeeded.` と表示されます。
