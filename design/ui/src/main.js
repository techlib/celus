// the following two imports are here to provide polyfills and replace @babel/polyfill
import "core-js/stable";
import "regenerator-runtime/runtime";
import Vue from "vue";
import App from "./pages/Main";
import store from "./store";
import router from "./router";
import i18n from "./i18n";
import vuetify from "./plugins/vuetify";
import VueTour from "vue-tour";
import * as Sentry from "@sentry/browser";
import { Vue as VueIntegration } from "@sentry/integrations";
import VuetifyConfirm from "vuetify-confirm";

Sentry.init({
  dsn: SENTRY_URL,
  integrations: [
    new VueIntegration({ Vue, attachProps: true, logErrors: true }),
  ],
  release: GIT_COMMITHASH ? `celus-${GIT_COMMITHASH}` : "",
  environment: SENTRY_ENVIRONMENT ? SENTRY_ENVIRONMENT : "",
});

// This should be the same as server_name from python part of sentry
Sentry.setTag("server_name", location.hostname.replace(/\./g, "-"));

require("vue-tour/dist/vue-tour.css");

Vue.use(VueTour);

Vue.use(VuetifyConfirm, {
  vuetify,
  buttonTrueText: "Accept",
  buttonFalseText: "Cancel",
  color: "warning",
  icon: "fa fa-exclamation-triangle",
  title: "Warning",
  width: 350,
  property: "$confirm",
});

Vue.config.productionTip = false;

const titleBase = "Celus";
router.afterEach((to, from) => {
  document.title = titleBase;
  if (to.meta && to.meta.title) {
    document.title += ": " + i18n.t(to.meta.title);
  }
});

new Vue({
  el: "#app",
  render: (h) => h(App),
  store,
  i18n,
  router,
  vuetify,
});
