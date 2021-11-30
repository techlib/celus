import http from "@/libs/http";

export default {
  state: {
    noInterestPlatformsCount: 0,
    noInterestPlatformsWithDataCount: 0,
    sushiCredentialsCount: 0,
    sushiCredentialsBrokenCount: 0,
    sushiCredentialsBrokenReportCount: 0
  },

  getters: {
    getNotifications(state) {
      // returns an object mapping URL name to an object describing the notifications to show
      let ret = {};
      if (state.noInterestPlatformsWithDataCount > 0) {
        ret["maintenance"] = {
          tooltip: "no_interest_platforms_with_data_present",
          level: "warning"
        };
      } else if (state.noInterestPlatformsCount > 0) {
        ret["maintenance"] = {
          tooltip: "no_interest_platforms_present",
          level: "info"
        };
      }
      if (
        state.sushiCredentialsBrokenCount > 0 ||
        state.sushiCredentialsBrokenReportCount > 0
      ) {
        ret["sushi-credentials-list"] = {
          tooltip: "broken_credentials_present",
          level: "warning"
        };
      }
      return ret;
    }
  },

  actions: {
    async fetchNoInterestPlatforms({ commit }) {
      const { response } = await http({
        url: "/api/organization/-1/platform/no-interest-defined/"
      });
      if (!response) return [];
      commit("setNoInterestPlatformsCount", { count: response.data.length });
      commit("setNoInterestPlatformsWithDataCount", {
        count: response.data.filter((item) => item.has_data).length
      });
      return response.data;
    },
    async loadSushiCredentialsCount({ commit }, component) {
      const { response } = await http({
        url: "/api/sushi-credentials/count/",
        label: "sushi credentials count",
        component
      });
      if (!response) return;
      commit("setSushiCredentialsCount", response.data);
    }
  },

  mutations: {
    setNoInterestPlatformsCount(state, { count }) {
      state.noInterestPlatformsCount = count;
    },
    setNoInterestPlatformsWithDataCount(state, { count }) {
      state.noInterestPlatformsWithDataCount = count;
    },
    setSushiCredentialsCount(state, { count, broken, broken_reports }) {
      state.sushiCredentialsCount = count;
      state.sushiCredentialsBrokenCount = broken;
      state.sushiCredentialsBrokenReportCount = broken_reports;
    }
  }
};
