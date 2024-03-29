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
import cancellation from "./modules/cancellation";
import interest from "./modules/interest";
import maintenance from "./modules/maintenance";
import tour from "./modules/tour";
import login from "./modules/login";
import pageSettings from "./modules/page-settings";
import siteConfig from "./modules/site-config";
import isEqual from "lodash/isEqual";
import sleep from "@/libs/sleep";
import { cs } from "date-fns/locale";
import startOfMonth from "date-fns/startOfMonth";

Vue.use(Vuex);

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
    cancellation,
    interest,
    login,
    maintenance,
    siteConfig,
    tour,
    pageSettings,
  },
  state: {
    latestPublishedRelease: null,
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
      {
        name: "date_range.current_plus_2y_back",
        start: startOfYear(addYears(new Date(), -2)),
        end: null,
        desc: "date_range_desc.current_plus_2y_back",
      },
      {
        name: "date_range.current_plus_1y_back",
        start: startOfYear(addYears(new Date(), -1)),
        end: null,
      },
      {
        name: "date_range.previous_year",
        start: startOfYear(addYears(new Date(), -1)),
        end: endOfYear(addYears(new Date(), -1)),
      },
      {
        name: "date_range.previous_2_years",
        start: startOfYear(addYears(new Date(), -2)),
        end: endOfYear(addYears(new Date(), -1)),
      },
      {
        name: "date_range.last_12_mo",
        start: addMonths(new Date(), -12),
        end: null,
      },
      { name: "date_range.all_available", start: null, end: null },
      {
        name: "date_range.custom",
        custom: true,
        desc: "date_range_desc.custom",
      },
    ],
    numberFormat: {
      notation: "fixed",
      precision: 1,
    },
    showLoginDialog: false,
    newCelusVersion: null,
    appLanguage: "en",
    basicInfo: {},
    backendReady: false,
    bootUpMessage: "loading_basic_data",
    et: false,
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
    dateRangeExplicitEndText(state, getters) {
      // if the end date is not set, it is the last finished month
      return (
        getters.dateRangeEndText ||
        ymDateFormat(addMonths(startOfMonth(new Date()), -1))
      );
    },
    formatNumber(state) {
      return (number) =>
        number === null ? "-" : formatNumber(number, state.numberFormat);
    },
    showAdminStuff(state, getters) {
      // can the user admin the organization that is selected?
      return (
        (state.user &&
          (state.user.is_admin_of_master_organization ||
            state.user.is_superuser)) ||
        (getters.selectedOrganization && getters.selectedOrganization.is_admin)
      );
    },
    showManagementStuff(state) {
      // can the user manage the system?
      return (
        state.user &&
        (state.user.is_admin_of_master_organization || state.user.is_superuser)
      );
    },
    showConsortialStuff(state) {
      return (
        state.user &&
        (state.user.is_user_of_master_organization || state.user.is_superuser)
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
    enableRawDataImport(state) {
      return state.basicInfo.ENABLE_RAW_DATA_IMPORT || "None";
    },
    automaticallyCreateMetrics(state) {
      if ("AUTOMATICALLY_CREATE_METRICS" in state.basicInfo) {
        return state.basicInfo["AUTOMATICALLY_CREATE_METRICS"];
      }
      return true;
    },
    enableTags(state) {
      return state.basicInfo.ENABLE_TAGS ?? false;
    },
    enableDataCoverage(state) {
      return state.basicInfo.ENABLE_DATA_COVERAGE ?? false;
    },
    celusAdminSitePath(state) {
      if ("CELUS_ADMIN_SITE_PATH" in state.basicInfo) {
        return state.basicInfo.CELUS_ADMIN_SITE_PATH;
      }
      return "wsEc67YNV2sq/";
    },
    harvesterIPv4Addresses(state) {
      return state.basicInfo.HARVESTER_IPV4_ADDRESSES || [];
    },
    harvesterIPv6Addresses(state) {
      return state.basicInfo.HARVESTER_IPV6_ADDRESSES || [];
    },
    exportDeletingPeriodInSec(state) {
      return state.basicInfo.EXPORT_DELETING_PERIOD;
    },
    letAxiosThrough(state) {
      /*
        when true, all requests by axios will be put through,
        otherwise only requests with privileged=true in config will be let through and
        others will have to wait for this to become true
      */
      if (state.user !== null && state.organizations !== null) {
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
    impersonator(state) {
      return state.user && state.user.impersonator;
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
    isRawImportEnabled(state, getters) {
      let org_id = parseInt(state.selectedOrganizationId);
      if (org_id < 0) {
        // No organization selected -> check global flag
        return ["All", "PerOrg"].includes(getters.enableRawDataImport);
      } else {
        // Check selected organization
        return !!getters.selectedOrganization?.is_raw_data_import_enabled;
      }
    },
  },

  actions: {
    async start({ dispatch }) {
      await dispatch("loadBasicInfo"); // load basic info - this can be done without logging in
      await dispatch("loadSiteConfig"); // site config - name, images, etc.
      await dispatch("fetchLatestPublishedRelease");
      await dispatch("loadUserData"); // we need user data first
    },
    afterAuthentication({ dispatch, state, getters }) {
      dispatch("loadOrganizations");
      // store current version as last seen if user value is undefined
      // this should only happen for new users, for whom we do not want to show the release notes
      if (
        state.user.extra_data?.last_seen_release === undefined ||
        state.user.extra_data?.last_dismissed_release === undefined
      ) {
        dispatch("dismissLastRelease", true);
      }
      dispatch("changeDateRangeObject", state.dateRangeIndex);
      dispatch("interest/fetchInterestGroups");
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
    showError({ dispatch }, { label, error }) {
      dispatch("showSnackbar", {
        content: `Error loading ${label ? label : "data"}: ${error}`,
        color: "error",
      });
    },
    selectOrganization(context, { id }) {
      context.commit("setSelectedOrganizationId", { id });
    },
    async fetchLatestPublishedRelease(context) {
      try {
        let response = await axios.get("/api/releases/latest/", {
          privileged: true,
        });
        context.commit("setLatestPublishedRelease", response.data);
      } catch (error) {
        console.warn("Could not fetch or set the latest published release");
      }
    },
    async loadUserData({ commit, dispatch }) {
      try {
        let response = await axios.get("/api/user/", { privileged: true });
        commit("setUserData", response.data);
        commit("setAppLanguage", { lang: response.data.language });
        dispatch("afterAuthentication");
      } catch (error) {
        if (error.response?.status === 403) {
          // we could not get user data because of 403 Forbidden error
          // thus we must inform the user that he will not see anything
          commit("setInvalidUser", { value: true });
        } else if (
          error.response?.status === 401 &&
          error.response?.headers?.["www-authenticate"] === "Session"
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
    async dismissLastRelease({ state, commit }, markSeen) {
      if (state.latestPublishedRelease?.version) {
        try {
          let data = {
            last_dismissed_release: state.latestPublishedRelease.version,
            last_seen_release: markSeen
              ? state.latestPublishedRelease.version
              : undefined,
          };
          const ed = state.user.extra_data;
          let existing = {
            last_dismissed_release: ed.last_dismissed_release,
            last_seen_release: markSeen ? ed.last_seen_release : undefined,
          };
          if (!isEqual(existing, data)) {
            // only update if necessary
            let response = await axios.post("/api/user/extra-data", data);
            commit("storeUserExtraData", { extraData: response.data });
          }
        } catch (error) {
          let warnSeen = markSeen ? " and last_seen_release" : "";
          console.warn(
            `Could not update last_dismissed_release${warnSeen} in user.extra_data`
          );
          throw error;
        }
      }
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
        if (getters.showConsortialStuff) {
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
        // vuex-persist stores selectedOrganizationId in window.localStorage,
        // therefore on app start the state.selectedOrganizationId is not necessary `null`.
        if (Object.keys(state.organizations).length > 0) {
          commit("setSelectedOrganizationId", {
            id:
              -1 in state.organizations
                ? -1 // preselect organization All for consortial users logging in for the first time
                : Number.parseInt(Object.keys(state.organizations)[0], 10),
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
    setNewCelusVersion(context, { new_version }) {
      context.commit("setNewCelusVersion", { new_version });
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
    setLatestPublishedRelease(state, release) {
      state.latestPublishedRelease = release;
    },
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
    setNewCelusVersion(state, { new_version }) {
      state.newCelusVersion = new_version;
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
