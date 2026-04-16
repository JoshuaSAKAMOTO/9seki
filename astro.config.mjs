// @ts-check
import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";

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
});