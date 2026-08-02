import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  root: ".",
  publicDir: "public",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        login: resolve(__dirname, "src/pages/login.html"),
        register: resolve(__dirname, "src/pages/register.html"),
        dashboard: resolve(__dirname, "src/pages/dashboard.html"),
        level: resolve(__dirname, "src/pages/level-designer.html"),
        quest: resolve(__dirname, "src/pages/quest-generator.html"),
        texture: resolve(__dirname, "src/pages/texture-upscaler.html"),
        character: resolve(__dirname, "src/pages/character-creator.html"),
        sound: resolve(__dirname, "src/pages/sound-designer.html"),
        playtester: resolve(__dirname, "src/pages/playtester.html"),
        localization: resolve(__dirname, "src/pages/localization.html"),
        resetPassword: resolve(__dirname, "src/pages/reset-password.html"),
        team: resolve(__dirname, "src/pages/team.html"),
        acceptInvite: resolve(__dirname, "src/pages/accept-invite.html"),
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: process.env.VITE_PROXY_TARGET || "http://api:8000",
        changeOrigin: true,
      },
      "/local-assets": {
        target: process.env.VITE_PROXY_TARGET || "http://api:8000",
        changeOrigin: true,
      },
      "/docs": {
        target: process.env.VITE_PROXY_TARGET || "http://api:8000",
        changeOrigin: true,
      },
      "/openapi.json": {
        target: process.env.VITE_PROXY_TARGET || "http://api:8000",
        changeOrigin: true,
      },
    },
  },
});
