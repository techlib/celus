export default {
  state: {
    pageSettings: {},
  },

  actions: {
    getPageSetting({ state }, { page, key }) {
      if (state.pageSettings[page]) {
        return state.pageSettings[page][key];
      }
    },
    setPageSetting({ commit }, { page, key, value }) {
      commit("setPageSetting", { page, key, value });
    },
  },

  mutations: {
    setPageSetting(state, { page, key, value }) {
      if (!state.pageSettings[page]) {
        state.pageSettings[page] = {};
      }
      state.pageSettings[page][key] = value;
    },
  },
};
