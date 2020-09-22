import axios from "axios";
import Cookies from "js-cookie";

export default {
  state: {
    email: "",
    loginError: null,
    authenticated: false,
  },

  getters: {
    loginErrorText(state) {
      if (state.loginError) {
        if (state.loginError.response.data) {
          if ("non_field_errors" in state.loginError.response.data) {
            return state.loginError.response.data.non_field_errors[0];
          }
        }
        return state.loginError;
      }
      return null;
    },
    usesPasswordLogin(state, getters, rootState) {
      return !!rootState.basicInfo.ALLOW_EMAIL_LOGIN;
    },
    canLogout(state, getters) {
      return getters.usesPasswordLogin; // we only know how to log-out when password login is used
    },
  },

  actions: {
    async login({ commit, dispatch }, { email, password }) {
      commit("setLoginError", { error: null });
      let csrftoken = Cookies.get("csrftoken");

      try {
        await axios.post(
          "/api/rest-auth/login/",
          { email: email, password: password },
          { headers: { "X-CSRFToken": csrftoken }, privileged: true }
        );

        commit("setAuthenticated", true);
        dispatch("setShowLoginDialog", false);
        dispatch("loadUserData");
      } catch (error) {
        commit("setLoginError", { error: error });
      }
    },
    async logout({ dispatch }) {
      let csrftoken = Cookies.get("csrftoken");
      try {
        await axios.post(
          "/api/rest-auth/logout/",
          {},
          { headers: { "X-CSRFToken": csrftoken } }
        );
      } catch (error) {
        dispatch("showSnackbar", {
          content: "Error logging out:" + error,
          color: "error",
        });
        return;
      }
      await dispatch("cleanUserData");
      await dispatch("setShowLoginDialog", { show: true });
    },
    async signup({ commit, dispatch }, { email, password1, password2 }) {
      let result = await axios.post(
        "/api/rest-auth/registration/",
        {
          email: email,
          password1: password1,
          password2: password2,
        },
        { privileged: true }
      );
      console.log(result);
      commit("setAuthenticated", true);
      dispatch("setShowLoginDialog", false);
      dispatch("loadUserData");
    },
    async resetPassword({ commit, dispatch }, { email }) {
      let csrftoken = Cookies.get("csrftoken");
      await axios.post(
        "/api/rest-auth/password/reset/",
        { email: email },
        { headers: { "X-CSRFToken": csrftoken }, privileged: true }
      );
    },
  },

  mutations: {
    setLoginError(state, { error }) {
      state.loginError = error;
    },
    setAuthenticated(state, authenticated) {
      state.authenticated = authenticated;
    },
  },
};
