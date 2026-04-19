// @ts-check
import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";

import cloudflare from "@astrojs/cloudflare";

export default defineConfig({
  site: "https://9seki.dev",
  integrations: [mdx()],

  vite: {
    resolve: {
      alias: {
        "@": "/src",
      },
    },
  },

  adapter: cloudflare(),
});