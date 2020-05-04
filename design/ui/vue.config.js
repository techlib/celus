let devURLBase = 'http://localhost:8015/'

const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;
const webpack = require('webpack')
const GitRevisionPlugin = require('git-revision-webpack-plugin')
const gitRevisionPlugin = new GitRevisionPlugin({branch: true})

module.exports = {
  runtimeCompiler: true,

  devServer: {
    proxy: {
      '/api/': {
        target: devURLBase,
        changeOrigin: true,
        ws: true,
      },
      '/static/': {
        target: devURLBase,
        changeOrigin: true,
        ws: true
      },
    },
    overlay: {
      errors: false,
    }
  },

  //filenameHashing: false,
  outputDir: '../../apps/core/static/',

  pluginOptions: {
    i18n: {
      locale: 'en',
      fallbackLocale: 'en',
      localeDir: 'locales',
      enableInSFC: true
    }
  },

  configureWebpack: {
    plugins: [
      new BundleAnalyzerPlugin(),
      gitRevisionPlugin,
      new webpack.DefinePlugin({
        'GIT_VERSION': JSON.stringify(gitRevisionPlugin.version()),
        'GIT_COMMITHASH': JSON.stringify(gitRevisionPlugin.commithash()),
        'GIT_BRANCH': JSON.stringify(gitRevisionPlugin.branch()),
      })
    ]
  },

  chainWebpack: config => {
    config.module
      .rule("i18n")
      .resourceQuery(/blockType=i18n/)
      .type('javascript/auto')
      .use("i18n")
        .loader("@kazupon/vue-i18n-loader")
        .end()
      .use('yaml')
        .loader('yaml-loader')
        .end()
  },

  transpileDependencies: ['vuex-persist', 'vuetify'], //'lodash', 'lodash.*'],

  lintOnSave: false,
}
