#!/usr/bin/env python3
"""AgentCore Payments プレビュー API を SigV4 直叩きで操作するミニマムサンプル。

公式 boto3 / bedrock-agentcore SDK にまだ Payments 関連メソッドが含まれて
いないため、botocore の SigV4 ヘルパーで自前 HTTPS リクエストを組み立てて
API を呼び出している。

2026年5月時点で動作確認済み:
- ListPaymentManagers
- ListPaymentCredentialProviders
- CreatePaymentCredentialProvider (Coinbase)
- GetPaymentCredentialProvider
- DeletePaymentCredentialProvider

CreatePaymentManager / ProcessPayment 等はサーバー側未展開のため非対応。
GA 後は公式 SDK の利用を推奨。
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


REGION = os.environ.get("AWS_REGION", "us-east-1")
PROFILE = os.environ.get("AWS_PROFILE", "default")

# ホスト名と signing service が異なる点に注意
CONTROL_HOST = f"https://bedrock-agentcore-control.{REGION}.amazonaws.com"
SIGNING_SERVICE = "bedrock-agentcore"


def _request(path, body):
    """SigV4 で署名した POST リクエストを送信する。"""
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    credentials = session.get_credentials().get_frozen_credentials()

    url = CONTROL_HOST + path
    body_str = json.dumps(body) if body else ""
    request = AWSRequest(
        method="POST", url=url, data=body_str,
        headers={"Content-Type": "application/json"}
    )
    SigV4Auth(credentials, SIGNING_SERVICE, REGION).add_auth(request)

    req = urllib.request.Request(
        url, data=body_str.encode("utf-8"),
        method="POST", headers=dict(request.headers)
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            # DELETE などはボディが空で返る場合があるため空対応
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read())
        except Exception:
            err = {"raw": "(non-JSON response)"}
        return e.code, err


def _print(status, body):
    """HTTP ステータスとレスポンスボディを整形表示する。"""
    print(f"HTTP {status}")
    print(json.dumps(body, indent=2, ensure_ascii=False))


def cmd_list_managers(args):
    """PaymentManager 一覧を取得して表示する。"""
    status, body = _request("/payments/managers-list", None)
    _print(status, body)


def cmd_list_providers(args):
    """PaymentCredentialProvider 一覧を取得して表示する。"""
    status, body = _request(
        "/identities/ListPaymentCredentialProviders",
        {"maxResults": 20},
    )
    _print(status, body)


def cmd_create_coinbase(args):
    """Coinbase の認証情報を PaymentCredentialProvider として登録する。"""
    api_key_id = os.environ.get("COINBASE_API_KEY_ID")
    api_key_secret = os.environ.get("COINBASE_API_KEY_SECRET")
    wallet_secret = os.environ.get("COINBASE_WALLET_SECRET")
    missing = [
        k for k, v in [
            ("COINBASE_API_KEY_ID", api_key_id),
            ("COINBASE_API_KEY_SECRET", api_key_secret),
            ("COINBASE_WALLET_SECRET", wallet_secret),
        ] if not v
    ]
    if missing:
        print(
            f"ERROR: 環境変数 {', '.join(missing)} を設定してください "
            f"(.env を使う場合は事前に `set -a; source .env; set +a`)",
            file=sys.stderr,
        )
        sys.exit(1)

    status, body = _request(
        "/identities/CreatePaymentCredentialProvider",
        {
            "name": args.name,
            "credentialProviderVendor": "CoinbaseCDP",
            "providerConfigurationInput": {
                "coinbaseCdpConfiguration": {
                    "apiKeyId": api_key_id,
                    "apiKeySecret": api_key_secret,
                    "walletSecret": wallet_secret,
                }
            },
        },
    )
    _print(status, body)


def cmd_get_provider(args):
    """指定した PaymentCredentialProvider の詳細を取得する。"""
    status, body = _request(
        "/identities/GetPaymentCredentialProvider",
        {"name": args.name},
    )
    _print(status, body)


def cmd_delete_provider(args):
    """指定した PaymentCredentialProvider を削除する。"""
    status, body = _request(
        "/identities/DeletePaymentCredentialProvider",
        {"name": args.name},
    )
    _print(status, body)


def main():
    parser = argparse.ArgumentParser(
        description="AgentCore Payments プレビュー API のミニマム実行サンプル"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-managers", help="PaymentManager 一覧を取得")
    sub.add_parser("list-providers", help="認証情報プロバイダー一覧を取得")

    p_create = sub.add_parser(
        "create-coinbase", help="Coinbase 認証情報を登録"
    )
    p_create.add_argument("--name", required=True, help="プロバイダー名")

    p_get = sub.add_parser("get-provider", help="プロバイダー詳細を取得")
    p_get.add_argument("--name", required=True, help="プロバイダー名")

    p_del = sub.add_parser("delete-provider", help="プロバイダーを削除")
    p_del.add_argument("--name", required=True, help="プロバイダー名")

    args = parser.parse_args()

    handlers = {
        "list-managers": cmd_list_managers,
        "list-providers": cmd_list_providers,
        "create-coinbase": cmd_create_coinbase,
        "get-provider": cmd_get_provider,
        "delete-provider": cmd_delete_provider,
    }
    handlers[args.cmd](args)


if __name__ == "__main__":
    main()
