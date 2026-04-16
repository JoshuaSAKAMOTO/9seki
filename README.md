# 球析 (9seki)

日本語MLBデータジャーナリズムメディア。中級者・上級者の2バージョンで執筆する、画像なし・軽量・モバイルファーストの分析サイト。

## Tech Stack

- Astro 6 + MDX / Cloudflare Pages
- Cloudflare Workers + Hono / D1 / R2
- Python + pybaseball / DuckDB (データパイプライン)

## Development

```sh
npm install
npm run dev      # http://localhost:4321
npm run build
```

## Structure

```
src/content/articles/   # 分析記事 (MDX)
src/content/metrics/    # 指標解説 (MDX)
src/components/article/ # <Advanced>, <Rewrite>, <Metric>
db/schema.sql           # D1スキーマ
scripts/                # Python データ/執筆パイプライン
workers/                # Cloudflare Workers API
```
