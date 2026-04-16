import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const articles = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/articles" }),
  schema: z.object({
    title: z.object({
      intermediate: z.string(),
      advanced: z.string().optional(),
    }),
    summary: z.string(),
    type: z.enum([
      "game-analysis",
      "metric-explainer",
      "weekly-recap",
      "season-analysis",
    ]),
    players: z.array(z.number()).default([]),
    metrics: z.array(z.string()).default([]),
    publishedAt: z.coerce.date(),
    updatedAt: z.coerce.date().optional(),
    status: z.enum(["draft", "published"]).default("draft"),
  }),
});

const metrics = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/metrics" }),
  schema: z.object({
    nameEn: z.string(),
    nameJa: z.string(),
    shortDesc: z.string(),
    level: z.enum(["basic", "intermediate", "advanced"]),
    source: z.string(),
    unit: z.string().optional(),
    leagueAverage: z.number().optional(),
    relatedMetrics: z.array(z.string()).default([]),
    publishedAt: z.coerce.date(),
  }),
});

export const collections = { articles, metrics };
