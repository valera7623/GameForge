import { defineConfig } from "vite";
import { resolve } from "path";

const CLEAN_URLS = {
  "/dashboard": "/src/pages/dashboard.html",
  "/login": "/src/pages/login.html",
  "/register": "/src/pages/register.html",
  "/team": "/src/pages/team.html",
  "/level-designer": "/src/pages/level-designer.html",
  "/quest-generator": "/src/pages/quest-generator.html",
  "/texture-upscaler": "/src/pages/texture-upscaler.html",
  "/character-creator": "/src/pages/character-creator.html",
  "/sound-designer": "/src/pages/sound-designer.html",
  "/playtester": "/src/pages/playtester.html",
  "/localization": "/src/pages/localization.html",
  "/reset-password": "/src/pages/reset-password.html",
  "/accept-invite": "/src/pages/accept-invite.html",
  "/ru": "/src/pages/ru/index.html",
  "/ru/": "/src/pages/ru/index.html",
  "/tools/level-designer": "/src/pages/tools/level-designer.html",
  "/tools/quest-generator": "/src/pages/tools/quest-generator.html",
  "/tools/texture-upscaler": "/src/pages/tools/texture-upscaler.html",
  "/tools/character-creator": "/src/pages/tools/character-creator.html",
  "/tools/sound-designer": "/src/pages/tools/sound-designer.html",
  "/tools/playtester": "/src/pages/tools/playtester.html",
  "/tools/localization": "/src/pages/tools/localization.html",
  "/ru/tools/level-designer": "/src/pages/ru/tools/level-designer.html",
  "/ru/tools/quest-generator": "/src/pages/ru/tools/quest-generator.html",
  "/ru/tools/texture-upscaler": "/src/pages/ru/tools/texture-upscaler.html",
  "/ru/tools/character-creator": "/src/pages/ru/tools/character-creator.html",
  "/ru/tools/sound-designer": "/src/pages/ru/tools/sound-designer.html",
  "/ru/tools/playtester": "/src/pages/ru/tools/playtester.html",
  "/ru/tools/localization": "/src/pages/ru/tools/localization.html",
};

function cleanUrlsPlugin() {
  return {
    name: "gameforge-clean-urls",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        const path = req.url?.split("?")[0];
        if (path && CLEAN_URLS[path]) {
          const qs = req.url.includes("?") ? req.url.slice(req.url.indexOf("?")) : "";
          req.url = CLEAN_URLS[path] + qs;
        }
        next();
      });
    },
  };
}

export default defineConfig({
  root: ".",
  publicDir: "public",
  plugins: [cleanUrlsPlugin()],
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
        ruLand: resolve(__dirname, "src/pages/ru/index.html"),
        toolLevel: resolve(__dirname, "src/pages/tools/level-designer.html"),
        toolQuest: resolve(__dirname, "src/pages/tools/quest-generator.html"),
        toolTexture: resolve(__dirname, "src/pages/tools/texture-upscaler.html"),
        toolCharacter: resolve(__dirname, "src/pages/tools/character-creator.html"),
        toolSound: resolve(__dirname, "src/pages/tools/sound-designer.html"),
        toolPlaytester: resolve(__dirname, "src/pages/tools/playtester.html"),
        toolLocalization: resolve(__dirname, "src/pages/tools/localization.html"),
        ruToolLevel: resolve(__dirname, "src/pages/ru/tools/level-designer.html"),
        ruToolQuest: resolve(__dirname, "src/pages/ru/tools/quest-generator.html"),
        ruToolTexture: resolve(__dirname, "src/pages/ru/tools/texture-upscaler.html"),
        ruToolCharacter: resolve(__dirname, "src/pages/ru/tools/character-creator.html"),
        ruToolSound: resolve(__dirname, "src/pages/ru/tools/sound-designer.html"),
        ruToolPlaytester: resolve(__dirname, "src/pages/ru/tools/playtester.html"),
        ruToolLocalization: resolve(__dirname, "src/pages/ru/tools/localization.html"),
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
    },
  },
});
