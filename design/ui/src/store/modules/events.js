import axios from "axios";

export default {
  state: {
    totalCount: 0,
    unreadCount: 0,
    newestEventId: null,
    newestEvent: null,
  },

  actions: {
    async loadEvents({ dispatch }) {
      try {
        let response = await axios.get("/api/events/user-events/stats/");
        dispatch("updateStats", response.data);
        console.log("Loaded events", response.data.total);
      } catch (error) {
        console.log("Error loading events: " + error);
      }
    },
    updateStats({ commit, state, dispatch }, stats) {
      if (
        stats.newest_pk !== state.newestEventId &&
        state.newestEventId !== null &&
        stats.newest_event
      ) {
        dispatch("showSnackbar", {
          content: "New notification: " + stats.newest_event.title,
          color: "success",
        });
      }
      commit("updateStats", stats);
    },
  },

  mutations: {
    updateStats(state, { total, unread, newest_pk, newest_event }) {
      if (total !== undefined) {
        state.totalCount = total; // sometimes this is not provided
      }
      state.unreadCount = unread;
      state.newestEventId = newest_pk;
      state.newestEvent = newest_event;
    },
  },
};
