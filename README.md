# AgentCore Paymentsを宇宙最速で試そう！

Amazon Bedrock AgentCore Payments のプレビュー段階で、公式 SDK 公開を待たずに API を試せる**ミニマムサンプル**です。

## これは何？

日本時間2026/5/7夜、AWS が AgentCore Payments のプレビューを発表しました。しかし発表時点では `boto3` / `bedrock-agentcore` SDK に Payments 関連メソッドが含まれておらず、AWS CLI のサブコマンドも未公開のため、SDK ベースで動かそうとすると詰まります。

このリポジトリは `botocore` の SigV4 ヘルパーで自前 HTTPS リクエストを組み立てることで、**SDK 公開を待たずに今すぐ Payments API を叩く**サンプルです。依存ライブラリは `boto3` 1個だけ。

## ⚠️ 注意

- 公式リファレンスではありません。AWS 公式 SDK / CLI が Payments に対応次第、そちらの利用を推奨します。
- 2026年5月時点で動作確認済みですが、プレビュー段階のため API 仕様は GA までに変更される可能性があります。

## 動作確認済みの API

| 操作 | パス | 概要 |
|------|------|------|
| ListPaymentManagers | `POST /payments/managers-list` | PaymentManager 一覧 |
| ListPaymentCredentialProviders | `POST /identities/ListPaymentCredentialProviders` | 認証情報プロバイダー一覧 |
| CreatePaymentCredentialProvider | `POST /identities/CreatePaymentCredentialProvider` | Coinbase 等の認証情報を登録 |
| GetPaymentCredentialProvider | `POST /identities/GetPaymentCredentialProvider` | プロバイダー詳細取得 |
| DeletePaymentCredentialProvider | `POST /identities/DeletePaymentCredentialProvider` | プロバイダー削除 |

## 現時点で動かない API

- CreatePaymentManager / GetPaymentManager / Update / Delete
- CreatePaymentConnector / etc.
- CreatePaymentSession / CreatePaymentInstrument / ProcessPayment

これらはサーバー側で operation がまだ展開されていません。リクエストすると `403 "Unable to determine service/operation name to be authorized"` が返ります。

## 前提

- Python 3.10 以上
- AWS アカウント（Payments 対応リージョン: **us-east-1 / us-west-2 / eu-central-1 / ap-southeast-2**。東京は非対応）
- AWS CLI で SSO ログイン済みのプロファイル
- Coinbase Developer Platform アカウント（API キー + Wallet Secret）

## セットアップ

依存関係をインストール（`uv` 推奨）：

```bash
uv sync
```

`pip` を使う場合：

```bash
pip install -r <(echo "boto3>=1.34.0")
```

`.env.example` をコピーして編集：

```bash
cp .env.example .env
$EDITOR .env
```

`.env` に Coinbase 認証情報を記入：

```env
AWS_PROFILE=your-sso-profile
AWS_REGION=us-east-1

COINBASE_API_KEY_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
COINBASE_API_KEY_SECRET=...
COINBASE_WALLET_SECRET=MIGHAgEA...
```

## 使い方

`.env` を読み込んでから実行：

```bash
set -a; source .env; set +a

# PaymentManager 一覧（プレビュー段階では空配列が返る）
uv run python main.py list-managers

# 認証情報プロバイダー一覧
uv run python main.py list-providers

# Coinbase 認証情報を登録
uv run python main.py create-coinbase --name my-coinbase

# 詳細取得
uv run python main.py get-provider --name my-coinbase

# 削除（クリーンアップ）
uv run python main.py delete-provider --name my-coinbase
```

## ハマりどころ

### 1. ホスト名と SigV4 signing service が違う

エンドポイントは `bedrock-agentcore-control.<region>.amazonaws.com` ですが、SigV4 の signing service は `bedrock-agentcore`（`-control` 抜き）。間違えると以下のエラーが返ります。

```
403 "Credential should be scoped to correct service: 'bedrock-agentcore'"
```

### 2. Wallet Secret は EC P-256 base64

Coinbase の `walletSecret` は **EC P-256 形式の秘密鍵を base64 エンコードしたもの**を要求します。Coinbase Developer Platform の Server Wallets セクションで生成してください（API キーとは別）。例：

```
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg...
```

API キーをそのまま渡すと `400 "Invalid walletSecret format: Expected base64-encoded EC P-256 private key"` が返ります。

### 3. リージョン制限

Payments は **us-east-1 / us-west-2 / eu-central-1 / ap-southeast-2** のみ対応。**東京（ap-northeast-1）は非対応**です。

### 4. 認証情報は Secrets Manager に自動保存

`CreatePaymentCredentialProvider` で渡したシークレットは AWS Secrets Manager に自動保管されます（`bedrock-agentcore-identity!default/payment/<vendor>/<name>-<random>/...` 形式）。`DeletePaymentCredentialProvider` でリソースを削除すると、対応する Secrets Manager のエントリも消える設計と思われます（要動作確認）。

## クリーンアップ

検証で作成したリソースは終わったら必ず削除：

```bash
uv run python main.py delete-provider --name my-coinbase
```

Coinbase 側の API キー / Wallet Secret も検証完了後にローテーションすることを強く推奨します（保管された旧キーが残るため）。

## このサンプルの寿命

公式 `boto3` に Payments メソッドが追加され次第、そちらに移行してください。このリポジトリはあくまで**プレビュー初日の検証用**です。

## 関連リソース

- [AgentCore Payments 開発者ガイド](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/payments.html)
- [x402 プロトコル](https://www.x402.org/)
- [Coinbase Developer Platform](https://portal.cdp.coinbase.com/)