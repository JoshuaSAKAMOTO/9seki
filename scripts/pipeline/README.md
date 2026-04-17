# 9seki Data Pipeline

pybaseball経由でStatcastデータを日次取得し、R2 (Parquet) + D1 (集計) に保存するバッチ。

## 必要な環境変数

| 変数 | 用途 |
|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | アカウントID |
| `CLOUDFLARE_API_TOKEN` | D1への書き込み用APIトークン（D1:Edit権限） |
| `D1_DATABASE_ID` | 9seki-db のUUID |
| `R2_ACCESS_KEY_ID` | R2 APIトークンのAccess Key ID |
| `R2_SECRET_ACCESS_KEY` | R2 APIトークンのSecret |
| `R2_BUCKET` | デフォルト `9seki-data`（通常変更不要） |

### トークン発行手順

1. **Cloudflare API Token**（D1アクセス用）
   - ダッシュボード右上の **My Profile** → **API Tokens** → **Create Token**
   - **Custom token** を選択
   - Permissions: `Account` → `D1` → `Edit`
   - Account Resources: 該当アカウントのみに限定
   - トークンをコピーして保存

2. **R2 API Token**
   - ダッシュボード → **R2** → **Manage R2 API Tokens** → **Create API Token**
   - Permission: `Object Read & Write`
   - Specify bucket: `9seki-data`
   - 発行後の **Access Key ID** と **Secret Access Key** を保存

3. **GitHub Secrets/Variables に登録**
   - リポジトリ → **Settings** → **Secrets and variables** → **Actions**
   - **Secrets**: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`
   - **Variables**: `D1_DATABASE_ID` (値: `b3b4538f-8ee1-4968-adfe-da3c75c83d3e`)

## ローカル実行

事前に [uv](https://docs.astral.sh/uv/) をインストール:
```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```sh
cd scripts/pipeline
cp .env.example .env    # .envに値を設定
uv sync
uv run --env-file .env python -m pipeline seed-players
uv run --env-file .env python -m pipeline daily --date 2026-04-15
```

## 利用可能なコマンド

- `seed-players` — `data/players.json` の選手マスタを D1 に投入（既存はUPDATE）
- `daily [--date YYYY-MM-DD]` — 前日（または指定日）のStatcast取得 → R2 Parquet保存 → D1 集計書き込み

## アーキテクチャ

```
pipeline/
├── __main__.py    # CLI dispatcher
├── config.py      # 環境変数ロード
├── clients.py     # D1 (HTTP API) + R2 (S3互換 boto3) クライアント
├── statcast.py    # pybaseball呼び出し + 集計ロジック
└── commands.py    # seed_players, daily_batch の実装

data/
└── players.json   # 日本人選手マスタ（手動キュレーション）
```

## Parquet配置

R2バケット内:

```
statcast/year=2026/month=04/day=15/pitches.parquet
```

DuckDBから読むときの例:

```sql
SELECT pitch_type, AVG(release_speed)
FROM 's3://9seki-data/statcast/year=2026/month=*/day=*/pitches.parquet'
WHERE pitcher = 808967
GROUP BY pitch_type;
```

## 定期実行

GitHub Actionsで毎日 15:00 UTC（= 00:00 JST）に自動実行される。
`.github/workflows/daily-pipeline.yml` を参照。

手動実行:
- リポジトリ → Actions → "Daily Statcast Pipeline" → "Run workflow"
- 任意の日付を指定可能
