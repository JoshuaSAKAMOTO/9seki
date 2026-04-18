# 9seki Writing Pipeline

ローカル実行のLLM執筆パイプライン。R2に蓄積されたStatcastデータから、Claude Sonnet 4.6で英語分析 → 日本語執筆の2ステップを回してMDX記事草稿を生成する。

## アーキテクチャ

```
R2 Parquet (DuckDB経由) ─┐
                         │
選手マスタ (D1)          ├──▶  統計サマリ (JSON)
期間・題材 (引数)         │          │
                         ┘          │
                                    ▼
                   Claude Sonnet 4.6 (英語で分析)
                                    │
                                    ▼
                         英語の bulleted findings
                                    │
                                    ▼
                    Style Guide + Few-shot (Prompt Cached)
                                    │
                                    ▼
                   Claude Sonnet 4.6 (日本語執筆)
                                    │
                                    ▼
                        MDX草稿 (status: draft)
                                    │
                                    ▼
             src/content/articles/drafts/{slug}.mdx
```

## 必要な環境変数

| 変数 | 用途 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude Sonnet 4.6 (分析 + 執筆) |
| `CLOUDFLARE_ACCOUNT_ID` | R2/D1アクセス |
| `CLOUDFLARE_API_TOKEN` | D1選手マスタ検索 |
| `D1_DATABASE_ID` | D1のUUID |
| `R2_ACCESS_KEY_ID` | DuckDBでR2 Parquet読み取り |
| `R2_SECRET_ACCESS_KEY` | 同上 |

APIキーの発行手順:

- **Anthropic**: https://console.anthropic.com/settings/keys

## セットアップ

事前に uv をインストール:
```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```sh
cd scripts/writing
cp .env.example .env    # APIキー等を設定
uv sync
```

## 使い方

### 基本

```sh
uv run --env-file .env python -m writing draft \
  --player "山本由伸" \
  --topic "スプリッターの使い方の変化" \
  --days 14
```

出力先: `src/content/articles/drafts/{slug}.mdx`

### オプション

```sh
--player <名前または MLBAM ID>   # 必須
--topic "題材"                    # 必須
--days 14                         # 遡る日数（デフォルト14）
--end-date 2026-04-15             # 終端日（デフォルト昨日）
--role pitcher|batter              # two_way選手の役割指定
--output path/to/file.mdx          # 出力先を指定
```

### 例

```sh
# 大谷翔平（two_way）の投手側の成績について
uv run --env-file .env python -m writing draft \
  --player 660271 \
  --topic "スイーパーの支配力" \
  --role pitcher \
  --days 21

# 鈴木誠也の打者としての傾向
uv run --env-file .env python -m writing draft \
  --player "鈴木誠也" \
  --topic "左投手への強さ" \
  --days 30
```

## プロンプト設計

### システムプロンプト (Prompt Cached)

`docs/style-guide.md` + 既存公開記事（few-shot）を1つの巨大システムブロックとしてキャッシュ。以下の条件を満たす限り、同じキャッシュを読む:

- style-guide.md を編集していない
- few-shotリスト (`FEW_SHOT_SLUGS` in `prompts.py`) が変わっていない
- 該当記事MDXが変わっていない

キャッシュ有効時、2本目以降の記事生成でシステムプロンプト分のコストが約10%に圧縮される。

### ユーザープロンプト

- 題材 (topic)
- 対象選手 + 役割
- 期間
- 英語findings (分析ステップの出力)
- 生統計のJSONサマリ
- 出力形式の制約（frontmatter必須フィールド、単位、文体）

## 出力の扱い方

1. 草稿ファイル (`drafts/*.mdx`) はデフォルトで `status: draft` なので、Astroのトップページには表示されない
2. Josh がブラウザで `npm run dev` を起動してプレビュー（ドラフト状態でも `/articles/{slug}` で見られる）
3. 内容を確認・微修正
4. 問題なければ `status: published` に変更 + `drafts/` から上位ディレクトリに移動
5. git commit → Cloudflare Pages 自動デプロイ

## コスト目安

1記事あたり（prompt cache有効時）:

| Step | Model | 入力 | 出力 | コスト |
|---|---|---|---|---|
| 分析 | claude-sonnet-4-6 | ~5k tok | ~1k tok | ~$0.030 |
| 執筆（初回） | claude-sonnet-4-6 | ~15k tok | ~4k tok | ~$0.105 |
| 執筆（キャッシュ読込時） | claude-sonnet-4-6 | ~15k tok（90%キャッシュ） | ~4k tok | ~$0.070 |

月30本想定で**$3〜4**程度。分析ステップもClaude Sonnetに寄せた分、深掘り度が明確に上がる。

## モジュール構成

```
writing/
├── __main__.py     # CLIディスパッチ
├── config.py       # 環境変数ロード
├── data.py         # D1選手検索 + DuckDB/R2 Parquetクエリ + 集計
├── prompts.py      # style-guide + few-shot の読み込み、プロンプト構築
├── analyze.py      # Claude Sonnet 4.6 (英語分析)
├── write.py        # Claude Sonnet 4.6 (日本語執筆、prompt caching有効)
└── commands.py     # draft() オーケストレーション
```

## Style Guideの更新

`docs/style-guide.md` を編集すると、次回実行時に**キャッシュが無効化される**（初回は書き込みコスト、2回目以降はまた再利用）。頻繁な小変更より、変更をまとめてコミットする方が効率的。

## Few-shot記事の追加

執筆品質を上げるには `src/content/articles/` に良質な記事を追加し、`writing/prompts.py` の `FEW_SHOT_SLUGS` に slugを追加する。3〜5本で85%のスタイル一致度、という目安（設計ドキュメント参照）。
