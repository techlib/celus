let devURLBase = 'http://localhost:8019/'

module.exports = {
  runtimeCompiler: true,

  devServer: {
    proxy: {
      '/logs/api': {
        target: devURLBase,
        changeOrigin: true,
        ws: true
      },
      '/organizations/api': {
        target: devURLBase,
        changeOrigin: true,
        ws: true
      },
      '/publications/api': {
        target: devURLBase,
        changeOrigin: true,
        ws: true
      },
      '/static/': {
        target: devURLBase,
        changeOrigin: true,
        ws: true
      },
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
  }
}
