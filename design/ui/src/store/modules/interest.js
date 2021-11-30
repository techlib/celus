import http from "@/libs/http";

export default {
  namespaced: true,

  state: {
    interestGroups: [],
    selectedGroups: [],
    totalInterestData: null,
    interestReportType: null
  },

  getters: {
    selectedGroupObjects: (state) =>
      state.interestGroups.filter(
        (item) => state.selectedGroups.indexOf(item.short_name) > -1
      )
  },

  actions: {
    async fetchInterestGroups({ commit }, component) {
      let {response} = await http({
        url: "/api/interest-groups/",
        label: "interest groups",
        component,
      });
      if (!response) return;
      commit("setInterestGroups", {
        interestGroups: response.data
      });
      commit("setSelectedGroups", {
        groups: response.data
          .filter((item) => item.important)
          .map((item) => item.short_name)
      });
    },
    changeSelectedGroups({ commit }, groups) {
      commit("setSelectedGroups", { groups: groups });
    },

    async fetchInterestReportType({ commit }, component) {
      const { response } = await http({
        url: "/api/report-type/",
        label: "interest report type",
        component,
      });
      if (response === null) return;

      for (let rt of response.data) {
        if (rt.short_name === "interest") {
          commit("setInterestReportType", { rt });
          break;
        }
      }
    },

    async fetchTotalInterest({ commit }, config) {
      if (!config) return;
      const { response } = await http({
        label: "total interest data",
        ...config
      });
      if (!response) return;
      commit("setTotalInterestData", response.data);
    }
  },

  mutations: {
    setInterestGroups(state, { interestGroups }) {
      state.interestGroups = interestGroups;
    },
    setSelectedGroups(state, { groups }) {
      state.selectedGroups = groups;
    },
    setTotalInterestData(state, data) {
      state.totalInterestData = data;
    },
    setInterestReportType(state, { rt }) {
      state.interestReportType = rt;
    }
  }
};
