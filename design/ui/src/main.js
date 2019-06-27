import Vue from 'vue'
import App from './pages/Main'
import store from './store'
import router from './router'
import Vuetify from 'vuetify'
import 'vuetify/dist/vuetify.min.css'
import i18n from './i18n'
import colors from 'vuetify/es5/util/colors'

Vue.config.productionTip = false
Vue.use(Vuetify, {
  iconfont: 'fa',
  theme: {
    primary: colors.teal.lighten2,
    secondary: colors.teal,
    accent: colors.orange.lighten2,
  }
})

new Vue({
  el: "#app",
  render: h => h(App),
  store,
  i18n,
  router,
})
