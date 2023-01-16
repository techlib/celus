import Vue from "vue";
import Vuetify from "vuetify/lib";
import colors from "vuetify/es5/util/colors";

Vue.use(Vuetify);

export default new Vuetify({
  icons: {
    iconfont: "fa",
  },
  theme: {
    themes: {
      light: {
        primary: colors.teal.lighten2,
        secondary: colors.grey,
        accent: colors.orange.lighten2,
        counterRegistry: "#107da6",
      },
    },
  },
});
