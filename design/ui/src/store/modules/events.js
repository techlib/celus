import axios from "axios";

export default {
  state: {
    totalCount: 0,
    unreadCount: 0,
    newestEventId: null,
    newestEvent: null,
    counts: {
      read: [],
      category: [],
      importance: [],
    },
  },

  actions: {
    async loadEvents({ dispatch }, { read, category, importance, search }) {
      try {
        let params = {};
        if (read != null) {
          params.read = read;
        }
        if (category != null) {
          params.category = category;
        }
        if (importance != null) {
          params.importance = importance;
        }
        if (search) {
          params.search = search;
        }

        let response = await axios.get("/api/events/user-events/stats/", {
          params: params,
        });
        dispatch("updateStats", response.data);
        console.log("Loaded events", response.data.total);
        return response.data;
      } catch (error) {
        console.log("Error loading events: " + error);
        return null;
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
    updateStats(state, { total, unread, newest_pk, newest_event, counts }) {
      if (total !== undefined) {
        state.totalCount = total; // sometimes this is not provided
      }
      state.unreadCount = unread;
      state.newestEventId = newest_pk;
      state.newestEvent = newest_event;
      state.counts.read = counts.read;
      state.counts.importance = counts.importance;
      state.counts.category = counts.category;
    },
  },
};
