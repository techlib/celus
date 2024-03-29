let devURLBase = "http://localhost:8015/";

const BundleAnalyzerPlugin = require("webpack-bundle-analyzer")
  .BundleAnalyzerPlugin;
const webpack = require("webpack");

// stuff beginning with VUE_APP_ gets automatically exported into the environment
// and thus can be used elsewhere in the code
process.env.VUE_APP_VERSION = require("./package.json").version;

module.exports = {
  runtimeCompiler: true,

  devServer: {
    proxy: {
      "/api/": {
        target: devURLBase,
        changeOrigin: true,
        ws: true
      },
      "/static/": {
        target: devURLBase,
        changeOrigin: true,
        ws: true
      },
      "/media/": {
        target: devURLBase,
        changeOrigin: true,
        ws: true
      }
    },
    overlay: process.env.BUILD == "yes" ? false : { errors: false },
    port: process.env.DEV_SERVER_PORT
  },

  //filenameHashing: false,
  outputDir: process.env.OUTPUT_DIR || "../../apps/core/static/",

  pluginOptions: {
    i18n: {
      locale: "en",
      fallbackLocale: "en",
      localeDir: "locales",
      enableInSFC: true
    }
  },

  configureWebpack: {
    plugins: [
      new BundleAnalyzerPlugin(
        process.env.BUILD == "yes" ? { analyzerMode: "disabled" } : {}
      ),
      new webpack.DefinePlugin({
        GIT_VERSION: JSON.stringify(`${process.env.GIT_VERSION || ""}`),
        GIT_COMMITHASH: JSON.stringify(`${process.env.GIT_COMMITHASH || ""}`),
        GIT_BRANCH: JSON.stringify(`${process.env.GIT_BRANCH || ""}`),
        SENTRY_URL: JSON.stringify(`${process.env.SENTRY_URL_JS || ""}`),
        SENTRY_ENVIRONMENT: JSON.stringify(
          `${process.env.SENTRY_ENVIRONMENT || ""}`
        )
      })
    ]
  },

  chainWebpack: config => {
    config.module
      .rule("i18n")
      .resourceQuery(/blockType=i18n/)
      .type("javascript/auto")
      .use("i18n")
      .loader("@kazupon/vue-i18n-loader")
      .end()
      .use("yaml")
      .loader("yaml-loader")
      .end();
  },

  transpileDependencies: ["vuex-persist", "vuetify"], //'lodash', 'lodash.*'],

  lintOnSave: false
};
