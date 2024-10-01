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
        primary: "#2d5854",
        secondary: colors.teal.lighten2,
        accent: colors.orange.lighten2,
        counterRegistry: "#107da6",
        anchor: "#35827b",
        tertiary: "#666666",
      },
    },
  },
});
