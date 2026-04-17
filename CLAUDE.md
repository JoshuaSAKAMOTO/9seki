# 球析 (9seki)

日本語MLBデータジャーナリズムメディア。

## Tech Stack

- **Frontend**: Astro 6 + MDX, Cloudflare Pages
- **API**: Cloudflare Workers + Hono
- **DB**: Cloudflare D1 (動的データ), R2 + Parquet (Statcastデータ)
- **Data Pipeline**: Python + pybaseball, GitHub Actions
- **Writing Pipeline**: Gemini Flash (分析/英語) → Claude Sonnet (執筆/日本語)

## Architecture Decisions

- 記事コンテンツはMDX (Content Collections) で管理。D1には入れない。
- D1は動的データのみ: players, metrics, player_latest_stats, player_game_logs
- 画像は一切使わない。ビジュアルは自前SVG/HTMLのみ。
- モバイルファースト。max-width: 40rem。

## Content Model

記事は中上級者向けのシングルバージョン:
- 本文 = 中上級者向けの読み物として執筆
- `<Advanced>` コンポーネント = クリック展開型の技術的補足（任意で深掘り）
- `<Metric>` コンポーネント = 指標解説へのインラインリンク
- `<StatCard>` / `<HBarChart>` = 数字/可視化コンポーネント

## Commands

```bash
npm run dev        # Astro dev server
npm run build      # Production build
npm run preview    # Preview build
```

## Directory Structure

```
src/
  content/articles/  # 分析記事 (MDX, Content Collections)
  content/metrics/   # 指標解説 (MDX, Content Collections)
  components/article/ # 2バージョン切替コンポーネント
  components/charts/  # SVGチャートコンポーネント
  layouts/            # ページレイアウト
  pages/              # Astroルーティング
  lib/                # ユーティリティ
db/                   # D1スキーマ
scripts/pipeline/     # Python データ収集バッチ
scripts/writing/      # Python 執筆パイプライン
workers/              # Cloudflare Workers API (Hono)
docs/                 # 設計ドキュメント
```

## Conventions

- コミットメッセージ: Conventional Commits (英語)
- 単位: km/h, m (mph/ft は使わない)
- 率: 小数3桁 (.380)
- 日本語テキスト: 「〜だ。」「〜である。」調
