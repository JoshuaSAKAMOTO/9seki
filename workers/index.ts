/**
 * 9seki API — Cloudflare Workers + Hono
 *
 * D1を直接叩いて、Astro (SSG) からは賄いきれない「動的に変わるデータ」を返す:
 * - /api/players           : 追跡中の日本人MLB選手一覧
 * - /api/players/:id       : 選手プロフィール
 * - /api/players/:id/game-logs?limit=N&role=pitcher|batter : 最近の試合ログ
 *
 * 記事本文・指標解説・トップページはAstro静的ビルド側で処理している
 * (src/pages/articles, src/pages/metrics)。
 */

import { Hono } from "hono";
import { cors } from "hono/cors";

type Bindings = {
  DB: D1Database;
  DATA: R2Bucket;
};

const app = new Hono<{ Bindings: Bindings }>();

app.use(
  "*",
  cors({
    origin: [
      "https://9seki.pages.dev",
      "https://9seki.dev",
      "http://localhost:4321",
    ],
    allowMethods: ["GET"],
    maxAge: 86400,
  }),
);

app.get("/", (c) =>
  c.json({
    service: "9seki-api",
    status: "ok",
    endpoints: [
      "GET /api/players",
      "GET /api/players/:id",
      "GET /api/players/:id/game-logs?limit=N&role=pitcher|batter",
    ],
  }),
);

app.get("/api/players", async (c) => {
  const { results } = await c.env.DB.prepare(
    `SELECT mlbam_id, name_en, name_ja, name_ja_kana, team_code, primary_role
     FROM players
     ORDER BY name_ja`,
  ).all();

  c.header("Cache-Control", "public, max-age=60, s-maxage=300");
  return c.json({ players: results });
});

app.get("/api/players/:id", async (c) => {
  const id = Number(c.req.param("id"));
  if (!Number.isFinite(id)) {
    return c.json({ error: "invalid player id" }, 400);
  }

  const player = await c.env.DB.prepare(
    `SELECT mlbam_id, name_en, name_ja, name_ja_kana, team_code, primary_role,
            jersey_number, debut_date
     FROM players
     WHERE mlbam_id = ?`,
  )
    .bind(id)
    .first();

  if (!player) {
    return c.json({ error: "player not found", mlbam_id: id }, 404);
  }

  c.header("Cache-Control", "public, max-age=300, s-maxage=3600");
  return c.json({ player });
});

app.get("/api/players/:id/game-logs", async (c) => {
  const id = Number(c.req.param("id"));
  if (!Number.isFinite(id)) {
    return c.json({ error: "invalid player id" }, 400);
  }

  const limit = Math.min(
    Math.max(Number(c.req.query("limit") ?? "10") || 10, 1),
    100,
  );
  const role = c.req.query("role");
  if (role && role !== "pitcher" && role !== "batter") {
    return c.json({ error: "role must be pitcher or batter" }, 400);
  }

  const stmt = role
    ? c.env.DB.prepare(
        `SELECT game_date, game_pk, role, stats
         FROM player_game_logs
         WHERE mlbam_id = ? AND role = ?
         ORDER BY game_date DESC, game_pk DESC
         LIMIT ?`,
      ).bind(id, role, limit)
    : c.env.DB.prepare(
        `SELECT game_date, game_pk, role, stats
         FROM player_game_logs
         WHERE mlbam_id = ?
         ORDER BY game_date DESC, game_pk DESC
         LIMIT ?`,
      ).bind(id, limit);

  const { results } = await stmt.all<{
    game_date: string;
    game_pk: number;
    role: string;
    stats: string;
  }>();

  const logs = results.map((r) => ({
    game_date: r.game_date,
    game_pk: r.game_pk,
    role: r.role,
    stats: JSON.parse(r.stats),
  }));

  c.header("Cache-Control", "public, max-age=60, s-maxage=300");
  return c.json({ mlbam_id: id, count: logs.length, logs });
});

app.notFound((c) => c.json({ error: "not found" }, 404));

app.onError((err, c) => {
  console.error("api error:", err);
  return c.json({ error: "internal error" }, 500);
});

export default app;
