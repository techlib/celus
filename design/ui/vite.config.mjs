// Plugins
import vue from "@vitejs/plugin-vue";
import vuetify, { transformAssetUrls } from "vite-plugin-vuetify";
import ViteFonts from "unplugin-fonts/vite";
import vueDevTools from "vite-plugin-vue-devtools";

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
    sourcemap: true,
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
    vueDevTools({ componentInspector: false }),
  ],
  define: { "process.env": {} },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
    extensions: [".js", ".json", ".jsx", ".mjs", ".ts", ".tsx", ".vue"],
  },
  // the following should make is faster and get rid of unwanted reloads due
  // to code optimization
  optimizeDeps: { exclude: ["vuetify"] },
  css: {
    preprocessorOptions: {
      scss: {
        api: "modern",
      },
      sass: {
        api: "modern",
      },
    },
    preprocessorMaxWorkers: true,
  },
  server: {
    port: 8080,
    proxy: {
      "/api/": {
        target: devURLBase,
      },
      "/static/": {
        target: devURLBase,
      },
      "/media/": {
        target: devURLBase,
      },
      "/ws/": {
        target: "http://localhost:8077/",
        ws: true,
      },
    },
  },
});
