// The `component` key represent a component name (eg. 'DashboardPage-ufjn4hl2wq7')
export default {
  namespaced: true,

  state: {
    controllers: {}, // Function controllers[..].abort() to be called on cancellation
    ongoing: {}, // Prevents creation of new requests after cancellation
  },

  actions: {
    setup({ commit }, component) {
      commit("initControllers", { component });
      commit("setOngoing", { value: false, component });
    },
    cancel({ state, commit, dispatch }, component) {
      commit("setOngoing", { value: true, component });
      const controllers = state.controllers[component];
      Object.values(controllers).forEach((controller) => controller.abort());
      // Clean up after some time
      setTimeout(() => dispatch("cleanup", component), 4000);
    },
    cleanup({ commit }, component) {
      commit("setOngoing", { component, value: false });
      commit("deleteComponent", component);
    },
    set({ commit }, { component, group }) {
      commit("setController", { component, group });
    },
  },

  mutations: {
    initControllers(state, { component }) {
      state.controllers[component] = {};
    },
    setController(state, { component, group }) {
      state.controllers[component][group] = new AbortController();
    },
    setOngoing(state, { value, component }) {
      state.ongoing[component] = value;
    },
    setCurrent(state, { component }) {
      state.current = component;
    },
    deleteComponent(state, component) {
      delete state.controllers[component];
      delete state.ongoing[component];
    },
  },
};
