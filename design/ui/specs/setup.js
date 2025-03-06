// this file is a helper used to setup the testing environment for the Vue components

import { mount, config } from "@vue/test-utils";
import { createI18n } from "vue-i18n";
import vuetify from "@/plugins/vuetify";

const i18n = createI18n();
config.global.plugins = [vuetify, i18n];

export { mount };
