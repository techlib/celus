import Vue from "vue";
import Vuex from "vuex";
import axios from "axios";
import Cookies from "js-cookie";
import addMonths from "date-fns/addMonths";
import addYears from "date-fns/addYears";
import endOfYear from "date-fns/endOfYear";
import startOfYear from "date-fns/startOfYear";
import { ymDateFormat, parseDateTime } from "@/libs/dates";
import { format as formatNumber } from "mathjs/lib/function/string/format";
import VuexPersistence from "vuex-persist";
import { sortOrganizations } from "@/libs/organizations";
import interest from "./modules/interest";
import maintenance from "./modules/maintenance";
import tour from "./modules/tour";
import login from "./modules/login";
import siteConfig from "./modules/site-config";
import { ConcurrencyManager } from "axios-concurrency";
import isEqual from "lodash/isEqual";
import sleep from "@/libs/sleep";
import { cs } from "date-fns/locale";

Vue.use(Vuex);

const MAX_CONCURRENT_REQUESTS_DEFAULT = 2;
let concurrencyManager = null;

const vuexLocal = new VuexPersistence({
  storage: window.localStorage,
  reducer: (state) => ({
    selectedOrganizationId: state.selectedOrganizationId,
    dateRangeIndex: state.dateRangeIndex,
    dateRangeStart: state.dateRangeStart,
    dateRangeEnd: state.dateRangeEnd,
  }),
  restoreState(key, storage) {
    const value = JSON.parse(storage.getItem(key));
    if (value) {
      if (key === "vuex") {
        if (value.dateRangeEnd) {
          value.dateRangeEnd = parseDateTime(value.dateRangeEnd);
        }
        if (value.dateRangeStart) {
          value.dateRangeStart = parseDateTime(value.dateRangeStart);
        }
      }
    }
    return value;
  },
});

export default new Vuex.Store({
  plugins: [vuexLocal.plugin],
  modules: {
    interest,
    maintenance,
    login,
    siteConfig,
    tour,
  },
  state: {
    user: null,
    invalidUser: false,
    snackbarShow: false,
    snackbarContent: null,
    snackbarColor: null,
    loginError: null,
    organizations: null,
    selectedOrganizationId: null,
    dateRangeStart: null,
    dateRangeEnd: null,
    dateRangeIndex: 0,
    dateRanges: [
      { name: "date_range.all_available", start: null, end: null },
      { name: "date_range.last_12_mo", start: -12, end: 0 },
      {
        name: "date_range.previous_year",
        start: startOfYear(addYears(new Date(), -1)),
        end: endOfYear(addYears(new Date(), -1)),
      },
      { name: "date_range.custom", custom: true },
    ],
    numberFormat: {
      notation: "fixed",
      precision: 1,
    },
    showLoginDialog: false,
    appLanguage: "en",
    basicInfo: {},
    backendReady: false,
    bootUpMessage: "loading_basic_data",
  },

  getters: {
    avatarImg: (state) => {
      return null;
    },
    avatarText: (state) => {
      if (state.user) {
        if (state.user.email) {
          return state.user.email[0].toUpperCase();
        } else {
          return state.user.username[0].toUpperCase();
        }
      }
      return "A";
    },
    usernameText: (state) => {
      if (state.user) {
        if (state.user.first_name && state.user.last_name) {
          return `${state.user.first_name} ${state.user.last_name}`;
        } else if (state.user.email) {
          return state.user.email;
        } else {
          return state.user.username;
        }
      }
      return "not logged in";
    },
    loggedIn: (state) => state.user !== null,
    organizationItems: (state) =>
      sortOrganizations(state.organizations, state.appLanguage),
    selectedOrganization: (state) => {
      if (state.organizations && state.selectedOrganizationId !== null) {
        return state.organizations[state.selectedOrganizationId];
      } else {
        return null;
      }
    },
    selectedDateRange: (state) => state.dateRanges[state.dateRangeIndex],
    dateRangeStartText(state) {
      if (state.dateRangeStart) {
        return ymDateFormat(state.dateRangeStart);
      }
      return "";
    },
    dateRangeEndText(state) {
      if (state.dateRangeEnd) {
        return ymDateFormat(state.dateRangeEnd);
      }
      return "";
    },
    formatNumber(state) {
      return (number) =>
        number === null ? "-" : formatNumber(number, state.numberFormat);
    },
    showAdminStuff(state, getters) {
      // can the user admin the organization that is selected?
      return (
        (state.user &&
          (state.user.is_from_master_organization ||
            state.user.is_superuser)) ||
        (getters.selectedOrganization && getters.selectedOrganization.is_admin)
      );
    },
    showManagementStuff(state) {
      // can the user manage the system?
      return (
        state.user &&
        (state.user.is_from_master_organization || state.user.is_superuser)
      );
    },
    organizationSelected(state) {
      return state.selectedOrganizationId && state.selectedOrganizationId > 0;
    },
    referenceCurrency(state) {
      if ("REFERENCE_CURRENCY" in state.basicInfo) {
        return state.basicInfo["REFERENCE_CURRENCY"];
      }
      return null;
    },
    allowSignUp(state) {
      if ("ALLOW_USER_REGISTRATION" in state.basicInfo) {
        return state.basicInfo["ALLOW_USER_REGISTRATION"];
      }
      return false;
    },
    allowUserCreatePlatforms(state) {
      if ("ALLOW_USER_CREATED_PLATFORMS" in state.basicInfo) {
          return state.basicInfo["ALLOW_USER_CREATED_PLATFORMS"];
      }
    },
    consortialInstall(state) {
      if ("CONSORTIAL_INSTALLATION" in state.basicInfo) {
        return state.basicInfo["CONSORTIAL_INSTALLATION"];
      }
      return true;
    },
    allowManualDataUpload(state) {
      if ("ALLOW_MANUAL_UPLOAD" in state.basicInfo) {
        return state.basicInfo["ALLOW_MANUAL_UPLOAD"];
      }
      return true;
    },
    celusAdminSitePath(state) {
      if ("CELUS_ADMIN_SITE_PATH" in state.basicInfo) {
        return state.basicInfo.CELUS_ADMIN_SITE_PATH;
      }
      return "wsEc67YNV2sq/";
    },
    letAxiosThrough(state, getters) {
      /*
        when true, all requests by axios will be put through,
        otherwise only requests with privileged=true in config will be let through and
        others will have to wait for this to become true
      */
      if (state.user !== null && getters.selectedOrganization) {
        return true;
      }
      return false;
    },
    bootUpFinished(state) {
      /*
      true when all data necessary for startup are loaded, false if it is still in progress
       */
      // as for now, when organizations are loaded, we consider boot-up finished
      return state.organizations !== null && true;
    },
    showCreateOrganizationDialog(state, getters) {
      return (
        getters.bootUpFinished &&
        getters.allowSignUp &&
        isEqual(state.organizations, {})
      );
    },
    showIntro(state) {
      return state.maintenance.sushiCredentialsCount === 0;
    },
    emailVerified(state) {
      return state.user && state.user.email_verification_status === "verified";
    },
    activeLanguageCodes(state) {
      if ("LANGUAGES" in state.basicInfo) {
        return state.basicInfo["LANGUAGES"].map((item) => item[0]);
      }
      return ["en"];
    },
    celusVersion() {
      return process.env.VUE_APP_VERSION;
    },
    dateFnOptions(state) {
      let options = {};
      if (state.appLanguage === "cs") {
        options["locale"] = cs;
      }
      return options;
    },
  },

  actions: {
    async start({ dispatch, getters, state }) {
      axios.defaults.xsrfCookieName = "csrftoken";
      axios.defaults.xsrfHeaderName = "X-CSRFToken";
      axios.interceptors.response.use(
        function (response) {
          // Do something with response data
          return response;
        },
        function (error) {
          // Do something with response error
          if (axios.isCancel(error)) {
            // we ignore this
          } else if (
            error.response &&
            (error.response.status === 401 || error.response.status === 403)
          ) {
            // if there is 401 error, try to (re)authenticate
            dispatch("setShowLoginDialog", { show: true });
          } else if (typeof error.response === "undefined") {
            // we are getting redirected to the EduID login page, but 302 is transparent for us
            // (the browser handles it on its own) and the error we get does not have any response
            // because it is caused by CORS violation when we try to get the eduid login page
            dispatch("setShowLoginDialog", { show: true });
          }
          return Promise.reject(error);
        }
      );

      // install concurrency manager
      let max_concurrent_requests = parseInt(
        localStorage.getItem("max_concurrent_requests")
      );
      if (!max_concurrent_requests) {
        max_concurrent_requests = MAX_CONCURRENT_REQUESTS_DEFAULT;
      }
      console.log("max_concurrent_requests", max_concurrent_requests);
      concurrencyManager = ConcurrencyManager(axios, max_concurrent_requests);

      axios.interceptors.request.use(async (config) => {
        // only let requests marked as privileged unless state.letAxiosThrough is true
        // this helps to let requests wait until all the required setup is done (user is logged
        // in, some basic data is loaded, etc.)
        if (getters.letAxiosThrough || config.privileged) {
          return config;
        }
        const watcher = new Promise((resolve) => {
          console.log(`delaying request for ${config.url}`);
          this.watch(
            (state, getters) => getters.letAxiosThrough,
            (newVal) => {
              if (newVal) resolve();
            }
          );
        });
        try {
          await watcher;
          return config;
        } catch (e) {
          console.error("error waiting for permission to use axios", e);
        }
      });
      await dispatch("loadBasicInfo"); // load basic info - this can be done without logging in
      await dispatch("loadSiteConfig"); // site config - name, images, etc.
      await dispatch("loadUserData"); // we need user data first
    },
    afterAuthentication({ dispatch, state, getters }) {
      dispatch("loadOrganizations");
      dispatch("changeDateRangeObject", state.dateRangeIndex);
      dispatch("fetchInterestGroups");
      dispatch("loadSushiCredentialsCount");
      if (getters.showManagementStuff) {
        dispatch("fetchNoInterestPlatforms");
      }
    },
    showSnackbar(context, { content, color }) {
      context.commit("setSnackbarContent", { content: content });
      context.commit("setSnackbarShow", { show: true, color: color });
    },
    hideSnackbar(context) {
      context.commit("setSnackbarShow", { show: false });
    },
    selectOrganization(context, { id }) {
      context.commit("setSelectedOrganizationId", { id });
    },
    async loadUserData({ commit, dispatch }) {
      try {
        let response = await axios.get("/api/user/", { privileged: true });
        commit("setUserData", response.data);
        commit("setAppLanguage", { lang: response.data.language });
        dispatch("afterAuthentication");
      } catch (error) {
        if (error.response && error.response.status === 403) {
          // we could not get user data because of 403 Forbidden error
          // thus we must inform the user that he will not see anything
          commit("setInvalidUser", { value: true });
        } else if (
          error.response &&
          error.response.status === 401 &&
          error.response.headers["www-authenticate"] === "Session"
        ) {
          dispatch("setShowLoginDialog", { show: true });
        } else {
          dispatch("showSnackbar", {
            content: "Error loading user data: " + error,
          });
        }
      }
    },
    cleanUserData({ commit }) {
      commit("setUserData", null);
      commit("setAuthenticated", false);
      //commit('setSelectedOrganizationId', null)
      commit("setOrganizations", null);
    },
    async loadOrganizations({ dispatch, getters }) {
      try {
        let response = await axios.get("/api/organization/", {
          privileged: true,
        });
        let organizations = {};
        for (let rec of response.data) {
          if (rec["name_cs"] === null) {
            rec["name_cs"] = rec["name"];
          }
          organizations[rec.pk] = rec;
        }
        if (getters.showManagementStuff) {
          organizations[-1] = {
            name: "All",
            name_cs: "Všechny",
            name_en: "All",
            pk: -1,
            extra: true,
          };
        }
        await dispatch("setOrganizations", organizations);
        dispatch("selectFirstOrganization");
      } catch (error) {
        dispatch("showSnackbar", {
          content: "Error loading organizations: " + error,
        });
      }
    },
    async setOrganizations({ commit }, organizations) {
      commit("setOrganizations", organizations);
    },
    selectFirstOrganization({ state, commit }) {
      if (!state.organizations) return;
      if (!(state.selectedOrganizationId in state.organizations)) {
        if (Object.keys(state.organizations).length > 0) {
          commit("setSelectedOrganizationId", {
            id: Number.parseInt(Object.keys(state.organizations)[0], 10),
          });
        } else {
          commit("setSelectedOrganizationId", { id: null });
        }
      }
    },
    async loadBasicInfo({ commit }) {
      while (true) {
        try {
          let response = await axios.get("/api/info/", { privileged: true });
          commit("setBackendReady", true);
          commit("setBasicInfo", response.data);
          break;
        } catch (error) {
          // sleep and retry
          commit("setBackendReady", false);
          await sleep(2000);
        }
      }
    },
    changeDateRangeObject(context, dateRangeIndex) {
      let drObj = context.state.dateRanges[dateRangeIndex];
      let start = null;
      let end = null;
      if (!drObj.custom) {
        // for custom specified, we do not do anything with the start and end
        if (drObj.start !== null) {
          if (typeof drObj.start === "number") {
            start = addMonths(new Date(), drObj.start);
          } else {
            start = drObj.start;
          }
        }
        if (drObj.end !== null) {
          if (typeof drObj.end === "number") {
            end = addMonths(new Date(), drObj.end);
          } else {
            end = drObj.end;
          }
        }
        context.commit("changeDateRange", {
          index: dateRangeIndex,
          start: start,
          end: end,
        });
      } else {
        context.commit("changeDateRange", { index: dateRangeIndex });
        // if the end of the period is not specified, set it to current data,
        // because 'undefined' and null states are both used for special purposes
        // in the changeDateRange, we use the specific setters here
        if (context.state.dateRangeEnd === null) {
          context.commit("setDateRangeEnd", { date: new Date() });
        }
        if (context.state.dateRangeStart === null) {
          context.commit("setDateRangeStart", {
            date: addMonths(context.state.dateRangeEnd, -24),
          });
        }
      }
    },
    changeDateRangeStart(context, date) {
      context.commit("setDateRangeStart", { date });
    },
    changeDateRangeEnd(context, date) {
      context.commit("setDateRangeEnd", { date });
    },
    setShowLoginDialog(context, { show }) {
      context.commit("setShowLoginDialog", { show });
    },
    async setAppLanguage(context, { lang }) {
      context.commit("setAppLanguage", { lang });
      try {
        let csrftoken = Cookies.get("csrftoken");
        await axios.put(
          "/api/user/language",
          { language: lang },
          { headers: { "X-CSRFToken": csrftoken } }
        );
      } catch (error) {
        // ignore this error - it is not crucial
      }
    },
  },

  mutations: {
    setSnackbarShow(state, { show, color }) {
      Vue.set(state, "snackbarColor", color);
      Vue.set(state, "snackbarShow", show);
    },
    setSnackbarContent(state, { content }) {
      Vue.set(state, "snackbarContent", content);
    },
    setLoginError(state, { error }) {
      Vue.set(state, "loginError", error);
    },
    setAuthToken(state, { token }) {
      Vue.set(state, "authToken", token);
    },
    setUserData(state, user) {
      state.user = user;
    },
    setOrganizations(state, organizations) {
      Vue.set(state, "organizations", organizations);
    },
    setSelectedOrganizationId(state, { id }) {
      state.selectedOrganizationId = id;
    },
    changeDateRange(state, { index, start, end }) {
      state.dateRangeIndex = index;
      if (typeof start !== "undefined") {
        state.dateRangeStart = start;
      }
      if (typeof end !== "undefined") {
        state.dateRangeEnd = end;
      }
    },
    setDateRangeStart(state, { date }) {
      state.dateRangeStart = date;
    },
    setDateRangeEnd(state, { date }) {
      state.dateRangeEnd = date;
    },
    setShowLoginDialog(state, { show }) {
      state.showLoginDialog = show;
    },
    setAppLanguage(state, { lang }) {
      state.appLanguage = lang;
    },
    setInvalidUser(state, { value }) {
      state.invalidUser = value;
    },
    setBasicInfo(state, data) {
      state.basicInfo = data;
    },
    storeUserExtraData(state, { extraData }) {
      Vue.set(state.user, "extra_data", extraData);
    },
    modifyUserExtraData(state, { key, value }) {
      Vue.set(state.user.extra_data, key, value);
    },
    setBackendReady(state, ready) {
      state.backendReady = ready;
      if (ready) {
        state.bootUpMessage = "loading_basic_data";
      } else {
        state.bootUpMessage = "waiting_for_backend";
      }
    },
  },
});
