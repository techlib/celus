import store from "@/store";
import axios from "axios";
import { ConcurrencyManager } from "axios-concurrency";

const MAX_CONCURRENT_REQUESTS_DEFAULT = 2;
let concurrencyManager = null;

axios.defaults.xsrfCookieName = "csrftoken";
axios.defaults.xsrfHeaderName = "X-CSRFToken";

axios.interceptors.request.use(
  function(config) {
    config.headers["celus-version"] = store.getters.celusVersion;
    return config;
  },
  function(error) {
    return Promise.reject(error);
  }
);

axios.interceptors.response.use(
  function(response) {
    // Clear the version diaolog when no error is returned
    store.dispatch("setNewCelusVersion", { new_version: null });
    // Do something with response data
    return response;
  },
  function(error) {
    // Do something with response error
    if (axios.isCancel(error)) {
      // we ignore this
    } else if (
      error.response &&
      (error.response.status === 401 || error.response.status === 403)
    ) {
      // if there is 401 error, try to (re)authenticate
      store.dispatch("setShowLoginDialog", { show: true });
    } else if (typeof error.response && error.response.status === 409) {
      // Display new celus version dialog
      store.dispatch("setNewCelusVersion", {
        new_version: error.response.headers["celus-version"],
      });
    } else if (typeof error.response === "undefined") {
      // we are getting redirected to the EduID login page, but 302 is transparent for us
      // (the browser handles it on its own) and the error we get does not have any response
      // because it is caused by CORS violation when we try to get the eduid login page
      store.dispatch("setShowLoginDialog", { show: true });
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
console.debug("max_concurrent_requests", max_concurrent_requests);
concurrencyManager = ConcurrencyManager(axios, max_concurrent_requests);

axios.interceptors.request.use(async (config) => {
  // only let requests marked as privileged unless state.letAxiosThrough is true
  // this helps to let requests wait until all the required setup is done (user is logged
  // in, some basic data is loaded, etc.)
  if (store.getters.letAxiosThrough || config.privileged) {
    return config;
  }
  const watcher = new Promise((resolve) => {
    console.debug(`delaying request for ${config.url}`);
    store.watch(
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

/**
 * Wrapper for Axios with error handling.
 * @param {string} url - (axios) URL
 * @param {Object} [params] - (axios) GET query parameters
 * @param {string} [method] - (axios) HTTP method "get" by default
 * @param {string} [label] - Description of resource in case of error
 */
const http = async (configuration) => {
  const { label, ...config } = configuration;

  try {
    return await axios(config);
  } catch (error) {
    if (axios.isCancel(error)) {
      return null;
    }

    store.dispatch("showSnackbar", {
      content: `Error loading ${label ? label : "data"}: ${error}`,
      color: "error",
    });
  }
  return null;
};

export default http;
