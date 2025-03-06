/**
 * main.js
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

// Components
import App from "./pages/Main.vue";

// Composables
import { createApp } from "vue";
import { createI18n } from "vue-i18n";
import { Buffer } from "buffer";
import confirm from "vuetify3-confirm";
import vuetify from "./plugins/vuetify";
import VueDatePicker from "@vuepic/vue-datepicker";
import "@vuepic/vue-datepicker/dist/main.css";
import "@/styles/settings.scss";
import VueGravatar from "vue3-gravatar";

window.Buffer = Buffer;

const pluralizationRules = {
  cs: (choice) => {
    if (choice === 1) {
      return 0;
    }
    if (choice >= 2 && choice <= 4) {
      return 1;
    }
    return 2;
  },
};

const i18n = createI18n({
  locale: "en",
  fallbackLocale: "en",
  silentTranslationWarn: true,
  silentFallbackWarn: true,
  pluralizationRules,
});

// Plugins
import { registerPlugins } from "@/plugins";

const app = createApp(App);

registerPlugins(app);

app.use(i18n);
app.use(confirm, {
  vuetify,
});
app.use(VueGravatar);
app.component("VueDatePicker", VueDatePicker);
app.mount("#app");
