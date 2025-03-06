// Plugins
import vue from "@vitejs/plugin-vue";
import vuetify, { transformAssetUrls } from "vite-plugin-vuetify";
import ViteFonts from "unplugin-fonts/vite";

// Utilities
import { defineConfig } from "vite";
import { fileURLToPath, URL } from "node:url";

import { resolve, dirname } from "node:path";
import VueI18nPlugin from "@intlify/unplugin-vue-i18n/vite";

process.env.VITE_APP_VERSION = require("./package.json").version;

const devURLBase = "http://127.0.0.1:8015/";

// https://vitejs.dev/config/
export default defineConfig({
  build: {
    outDir: process.env.OUTPUT_DIR || "../../apps/core/static/",
  },
  plugins: [
    vue({
      template: { transformAssetUrls },
    }),
    // https://github.com/vuetifyjs/vuetify-loader/tree/next/packages/vite-plugin
    vuetify({
      autoImport: true,
      styles: {
        configFile: "src/styles/settings.scss",
      },
    }),
    ViteFonts({
      google: {
        families: [
          {
            name: "Roboto",
            styles: "wght@100;300;400;500;700;900",
          },
        ],
      },
    }),
    VueI18nPlugin({
      compositionOnly: false,
      strictMessage: false,
      include: resolve(dirname(fileURLToPath(import.meta.url)), "locales/**"),
    }),
  ],
  define: { "process.env": {} },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
    extensions: [".js", ".json", ".jsx", ".mjs", ".ts", ".tsx", ".vue"],
  },
  server: {
    port: 3000,
    proxy: {
      "/api/": {
        target: devURLBase,
        // changeOrigin: true,
        ws: true,
      },
      "/static/": {
        target: devURLBase,
        changeOrigin: true,
        ws: true,
      },
      "/media/": {
        target: devURLBase,
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
