// basic imports
import Vue from "vue";
import { createVuetify } from "vuetify";
import { createI18n } from "vue-i18n";
import { createLocalVue, mount } from "@vue/test-utils";

// stuff to check
import CheckMark from "@/components/util/CheckMark";

// basic setup
// Vue.use(Vuetify);
// Vue.use(VueI18n);
const vuetify = createVuetify();
const i18n = createI18n({
  locale: "en",
  messages: {
    en: {
      checkmarkLabel: "This is a checkmark",
    },
  },
});
const localVue = createLocalVue();

describe("CheckMark", () => {
  // vuetify setup before each test
  // let vuetify;
  // beforeEach(() => {
  //   vuetify = new Vuetify();
  // });
  let wrapper;
  const mountComponent = (props) => {
    return mount(CheckMark, {
      global: {
        plugins: [vuetify, i18n],
      },
      props,
    });
  };

  // the tests themselves
  test("check error color", () => {
    wrapper = mountComponent({
      value: false,
    });
    expect(wrapper.html()).toContain("fa-square");
    expect(wrapper.html()).not.toContain("fa-check-square");
  }),
    test("check success color", () => {
      wrapper = mountComponent({
        value: true,
      });
      expect(wrapper.html()).toContain("fa-check-square");
      expect(wrapper.html()).not.toContain("fa-square");
    });
});
