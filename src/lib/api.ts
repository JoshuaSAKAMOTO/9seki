/**
 * Workers API クライアント。
 * ビルド時 (Astro SSG) からもブラウザ側からも呼べるよう、
 * 純粋な fetch ベースで組む。
 */

const API_BASE =
  import.meta.env.PUBLIC_API_BASE ??
  "https://9seki-api.josh-8b9.workers.dev";

export type PlayerRole = "pitcher" | "batter" | "two_way";

export type Player = {
  mlbam_id: number;
  name_en: string;
  name_ja: string;
  name_ja_kana: string | null;
  team_code: string;
  primary_role: PlayerRole;
  jersey_number?: number | null;
  debut_date?: string | null;
};

export type PitcherGameStats = {
  pitches?: number;
  swings?: number;
  whiffs?: number;
  called_strikes?: number;
  batters_faced?: number;
  whiff_rate?: number | null;
  csw_rate?: number | null;
  avg_velocity_mph?: number | null;
  max_velocity_mph?: number | null;
  pitch_types?: Record<string, number>;
};

export type BatterGameStats = {
  pa?: number;
  ab?: number;
  hits?: number;
  home_runs?: number;
  walks?: number;
  strikeouts?: number;
  avg?: number | null;
  hard_hit_rate?: number | null;
  avg_launch_speed_mph?: number | null;
  avg_launch_speed_kmh?: number | null;
  avg_launch_angle_deg?: number | null;
  events?: Record<string, number>;
};

export type GameLog = {
  game_date: string;
  game_pk: number;
  role: "pitcher" | "batter";
  stats: PitcherGameStats | BatterGameStats;
};

async function fetchJson<T>(path: string): Promise<T> {
  const url = `${API_BASE}${path}`;
  const r = await fetch(url);
  if (!r.ok) {
    throw new Error(`API ${path} → ${r.status} ${r.statusText}`);
  }
  return r.json() as Promise<T>;
}

export const api = {
  async listPlayers(): Promise<Player[]> {
    const data = await fetchJson<{ players: Player[] }>("/api/players");
    return data.players;
  },
  async getPlayer(id: number): Promise<Player> {
    const data = await fetchJson<{ player: Player }>(`/api/players/${id}`);
    return data.player;
  },
  async getGameLogs(
    id: number,
    opts: { limit?: number; role?: "pitcher" | "batter" } = {},
  ): Promise<GameLog[]> {
    const params = new URLSearchParams();
    if (opts.limit) params.set("limit", String(opts.limit));
    if (opts.role) params.set("role", opts.role);
    const qs = params.toString();
    const data = await fetchJson<{ logs: GameLog[] }>(
      `/api/players/${id}/game-logs${qs ? "?" + qs : ""}`,
    );
    return data.logs;
  },
};

/** English full name を URL slug に変換。"Shohei Ohtani" → "shohei-ohtani" */
export function playerSlug(player: Pick<Player, "name_en">): string {
  return player.name_en.toLowerCase().replace(/\s+/g, "-");
}

/** primary_role の日本語ラベル */
export function roleLabel(role: PlayerRole): string {
  return role === "pitcher" ? "投手" : role === "batter" ? "野手" : "二刀流";
}
