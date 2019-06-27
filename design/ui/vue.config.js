let devURLBase = 'http://localhost:8015/'

module.exports = {
  runtimeCompiler: true,

  devServer: {
    proxy: {
      '/api/logs/': {
        target: devURLBase,
        changeOrigin: true,
        ws: true,
        pathRewrite: {
          '^/api/logs': '/logs' // remove base path
        },
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
