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

現在は認証情報テンプレートの準備段階です。ダウンロード処理は今後 `main.py` に実装します。
