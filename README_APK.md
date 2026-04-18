# 福祉記録アプリ APK 化メモ

## 1. 事前準備

Windows の PowerShell でこのフォルダを開き、以下を実行します。

```powershell
py -m pip install --upgrade pip
py -m pip install "flet[all]" openai
```

## 2. 現場テスト向けの考え方

- 通常の記録データは端末内ストレージに保存されます。
- AI 下書きは OpenAI API 通信が必要です。
- 現場テストでは、まず AI を使わずに基本記録だけ試す運用がおすすめです。
- AI を止めて試す場合は、起動前に `CARE_APP_DISABLE_AI=1` を設定します。

## 3. APK ビルド

このフォルダで次を実行します。

```powershell
flet build apk . --exclude care_records.db __pycache__ *.txt
```

AI を止めた状態で試験するなら:

```powershell
$env:CARE_APP_DISABLE_AI="1"
flet build apk . --exclude care_records.db __pycache__ *.txt
```

出力先の目安:

```text
build\apk\
```

## 4. スマホへ入れる

生成された APK を Android 端末へコピーしてインストールします。
インストール時は「提供元不明のアプリ」を一時的に許可する場合があります。

## 5. 正式配布前にやること

- アプリ署名用の keystore を作る
- `AAB` も作れるようにする
- AI 用の API キーを端末に直接置かない構成へ変える
- バックアップやデータ移行方法を決める

## 6. GitHub Actions で APK を作る

ローカルPCで `Packaging Python app...` が止まる場合は、GitHub Actions でのビルドがおすすめです。

### 事前にやること

1. GitHub で新しいリポジトリを作る
2. この `care_app` フォルダの中身をそのリポジトリへアップロードする
3. `build/` や `care_records.db` はアップしない

### このフォルダに入っている準備済みファイル

- `.github/workflows/build-apk.yml`
- `.gitignore`

### GitHub 上での使い方

1. GitHub の対象リポジトリを開く
2. `Actions` タブを開く
3. `Build Android APK` を選ぶ
4. `Run workflow` を押す

### 完了後

ビルド成功後は `Artifacts` から `android-apk` をダウンロードできます。
中に APK ファイルが入ります。
