// basic imports
import Vue from "vue";
import Vuetify from "vuetify";
import VueI18n from "vue-i18n";
import { createLocalVue, mount } from "@vue/test-utils";

// stuff to check
import CheckMark from "@/components/util/CheckMark";

// basic setup
Vue.use(Vuetify);
Vue.use(VueI18n);
const localVue = createLocalVue();

describe("CheckMark", () => {
  // vuetify setup before each test
  let vuetify;
  beforeEach(() => {
    vuetify = new Vuetify();
  });

  // the tests themselves
  test("check error color", () => {
    const wrapper = mount(CheckMark, {
      localVue,
      vuetify,
      propsData: {
        value: false,
      },
    });
    expect(wrapper.html()).toContain("fa-square");
    expect(wrapper.html()).not.toContain("fa-check-square");
  }),
    test("check success color", () => {
      const wrapper = mount(CheckMark, {
        localVue,
        vuetify,
        propsData: {
          value: true,
        },
      });
      expect(wrapper.html()).toContain("fa-check-square");
      expect(wrapper.html()).not.toContain("fa-square");
    });
});
