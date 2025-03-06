/**
 * plugins/vuetify.js
 *
 * Framework documentation: https://vuetifyjs.com`
 */

// Styles
import "@mdi/font/css/materialdesignicons.css";
import "vuetify/styles";
import "@fortawesome/fontawesome-free/css/all.css";
import { fa } from "vuetify/iconsets/fa";
import { aliases, mdi } from "vuetify/iconsets/mdi-svg";
import colors from "vuetify/util/colors";

// Composables
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";
import { compact } from "lodash";

// https://vuetifyjs.com/en/introduction/why-vuetify/#feature-guides
export default createVuetify({
  icons: {
    aliases,
    defaultSet: "fa",
    sets: {
      mdi,
      fa,
    },
  },
  theme: {
    themes: {
      light: {
        colors: {
          primary: "#2d5854",
          secondary: colors.teal.lighten2,
          accent: colors.orange.lighten2,
          counterRegistry: "#107da6",
          anchor: "#35827b",
          tertiary: "#666666",
          defaultButton: "#f5f5f5",
          lighterIcons: "#757575",
          lighterGreyIcons: "#212121",
          error: "#ff5252",
          info: "#2196f3",
          tabs: "#5ab1ef",
        },
      },
    },
  },
  components,
  directives,
  defaults: {
    VDataTable: {
      sortAscIcon: "fas fa-sort-up",
      sortDescIcon: "fas fa-sort-down",
      density: "compact",
    },
    VDataTableServer: {
      sortAscIcon: "fas fa-sort-up",
      sortDescIcon: "fas fa-sort-down",
      density: "compact",
    },
    VCard: {
      elevation: "2",
    },
    VAutocomplete: {
      color: "primary",
      variant: "underlined",
    },
    VSelect: {
      color: "primary",
      variant: "underlined",
    },
    VTextField: {
      variant: "underlined",
      color: "primary",
    },
    VTextarea: {
      variant: "outlined",
      color: "primary",
    },
  },
});
