// The `component` key represent a component name (eg. 'DashboardPage-ufjn4hl2wq7')
export default {
  namespaced: true,

  state: {
    controller: {}, // Function controller.abort() to be called on cancellation
    signal: {}, // Passed during the request to communicate with Axios
    ongoing: {}, // Prevents creation of new requests after cancellation
  },

  actions: {
    setup({ commit }, component) {
      const controller = new AbortController();
      commit("setController", { controller, component });
      commit("setSignal", { signal: controller.signal, component });
      commit("setOngoing", { value: false, component });
    },
    cancel({ state, commit, dispatch }, component) {
      commit("setOngoing", { value: true, component });
      const controller = state.controller[component];
      if (controller) {
        controller.abort();
      }
      // Clean up after some time
      setTimeout(() => dispatch("cleanup", component), 4000);
    },
    cleanup({ commit }, component) {
      commit("setOngoing", { component, value: false });
      commit("deleteComponent", component);
    },
  },

  mutations: {
    setController(state, { controller, component }) {
      state.controller[component] = controller;
    },
    setSignal(state, { signal, component }) {
      state.signal[component] = signal;
    },
    setOngoing(state, { value, component }) {
      state.ongoing[component] = value;
    },
    setCurrent(state, { component }) {
      state.current = component;
    },
    deleteComponent(state, component) {
      delete state.controller[component];
      delete state.signal[component];
      delete state.ongoing[component];
    },
  },
};
