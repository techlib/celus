<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  mark_all_read_error: There was an error marking all events as read.
  mark_all_read_success: "{count} event was marked as read | {count} events were marked as read"

cs:
  mark_all_read_error: Při označení všech událostí jako přečtené došlo k chybě.
  mark_all_read_success: "{count} událost byla označena jako přečtená | {count} události byly označeny jako přečtené | {count} událostí bylo označeno jako přečtených"
</i18n>

<template>
  <v-data-table
    v-model="selectedEvents"
    :items="events"
    item-key="pk"
    :headers="headers"
    :expanded.sync="expanded"
    show-expand
    expand-icon="fa fa-caret-down"
    :loading="loading"
    :sort-by.sync="sortBy"
    :sort-desc.sync="sortDesc"
    :footer-props="{ itemsPerPageOptions: [10, 25, 50, 100] }"
    :server-items-length="eventCount"
    :page.sync="page"
    :items-per-page.sync="pageSize"
    :search="searchDebounced"
    show-select
    @item-expanded="markRead"
  >
    <template #item.read="{ item }">
      <v-icon
        v-if="item.read"
        small
        @click="markRead({ item, read: false, refresh: true })"
        >far fa-envelope-open</v-icon
      >
      <v-icon
        v-else
        small
        @click="markRead({ item, read: true, refresh: true })"
        >far fa-envelope</v-icon
      >
    </template>

    <template #item.created="{ item }">
      <span
        :class="item.read ? '' : 'font-weight-bold'"
        v-html="isoDateTimeFormatSpans(item.created)"
      ></span>
    </template>

    <template #item.title="{ item }">
      <a
        @click="toggleExpanded(item)"
        class="text-decoration-underline"
        :class="item.read ? '' : 'font-weight-bold'"
        >{{ item.title }}</a
      >
    </template>

    <template #item.category="{ item }">
      <EventCategoryMark :item="item" :bold="!item.read" />
    </template>

    <template #item.importance="{ item }">
      <EventImportanceIcon :importance="item.importance" small />
      <span class="ml-2">{{ $t("event_importance." + item.importance) }}</span>
    </template>

    <template #item.expiration_date="{ item }">
      <span v-if="item.expiration_date">{{
        isoDateFormat(parseDateTime(item.expiration_date))
      }}</span>
    </template>

    <template #expanded-item="{ item, headers }">
      <td :colspan="headers.length" class="px-2 py-2">
        <v-sheet class="pa-3">
          <v-tooltip bottom max-width="600px" v-if="item.expiration_date">
            <template #activator="{ on }">
              <div class="caption float-right" v-on="on">
                {{ $t("events.expires") }}:
                <span
                  v-html="isoDateTimeFormatSpans(item.expiration_date)"
                ></span>
              </div>
            </template>
            {{ $t("events.expires_tt") }}
          </v-tooltip>
          <div class="caption pb-3">{{ $t("labels.description") }}</div>
          <div
            class="event-text"
            v-html="markdownToHtml(item.description)"
          ></div>
        </v-sheet>
      </td>
    </template>

    <template #top>
      <v-row>
        <v-col cols="12" md="4" lg="3" xl="2">
          <EventCategorySelect
            v-model="filterCategory"
            show-all
            :categories="availableCategoriesAndCounts"
          />
        </v-col>
        <v-col cols="6" md="2" lg="2" xl="1">
          <EventImportanceSelect
            v-model="filterImportance"
            show-all
            :importancies="availableImportanciesAndCounts"
          />
        </v-col>
        <v-col cols="6" md="2" lg="2" xl="1">
          <v-select
            v-model="filterRead"
            :items="[
              { text: $t('options.all'), value: null },
              {
                text: $t('event_read.read'),
                value: true,
                count: availableReadAndCounts.get(true),
              },
              {
                text: $t('event_read.unread'),
                value: false,
                count: availableReadAndCounts.get(false),
              },
            ]"
            :label="$t('events.read')"
          >
            <template #item="{ item }">
              <v-list-item-content>
                <v-list-item-title>
                  {{ item.text }}
                  <span v-if="item.count" class="float-right text-caption">{{
                    item.count
                  }}</span>
                </v-list-item-title>
              </v-list-item-content>
            </template>
          </v-select>
        </v-col>
        <v-spacer />
        <v-col cols="12" md="4" lg="3" xl="2">
          <v-text-field
            v-model="searchDebounced"
            append-icon="fa-search"
            :label="$t('labels.search')"
            single-line
            hide-details
            clearable
            clear-icon="fas fa-times"
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row class="pb-3">
        <v-col>
          <v-btn
            @click="markSelectedRead(true)"
            :disabled="selectedEvents.length === 0"
          >
            <v-icon small class="mr-2">far fa-envelope-open</v-icon>
            {{ $t("events.mark_as_read") }}
          </v-btn>
        </v-col>
      </v-row>
    </template>
  </v-data-table>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import {
  isoDateFormat,
  isoDateTimeFormatSpans,
  parseDateTime,
} from "@/libs/dates";
import EventImportanceIcon from "@/components/events/EventImportanceIcon.vue";
import EventCategoryMark from "@/components/events/EventCategoryMark.vue";
import debounce from "lodash/debounce";
import EventCategorySelect from "@/components/events/EventCategorySelect.vue";
import EventImportanceSelect from "@/components/events/EventImportanceSelect.vue";
import stateTracking from "@/mixins/stateTracking";
import { mapActions, mapState } from "vuex";
import { marked } from "marked";

export default {
  name: "EventList",
  components: {
    EventCategorySelect,
    EventImportanceSelect,
    EventCategoryMark,
    EventImportanceIcon,
  },

  mixins: [cancellation, stateTracking],

  data() {
    return {
      events: [],
      selectedEvents: [],
      eventCount: 0,
      loading: false,
      expanded: [],
      search: "",
      filterCategory: null,
      filterImportance: null,
      filterRead: null,
      sortBy: "created",
      sortDesc: true,
      page: 1,
      pageSize: 10,
      watchedAttrs: [
        {
          name: "search",
          type: String,
        },
        {
          name: "filterCategory",
          type: String,
        },
        {
          name: "filterImportance",
          type: String,
        },
        {
          name: "filterRead",
          type: Boolean,
          alwaysTrack: true,
        },
        {
          name: "sortBy",
          type: String,
        },
        {
          name: "sortDesc",
          type: Boolean,
          alwaysTrack: true,
        },
      ],
    };
  },

  computed: {
    ...mapState({
      storeNewestEventId: (state) => state.events.newestEventId,
      storeUnreadEventCount: (state) => state.events.unreadCount,
      storeCounts: (state) => state.events.counts,
    }),
    headers() {
      return [
        {
          text: this.$t("events.read"),
          value: "read",
          width: "5rem",
        },
        {
          text: this.$t("events.date"),
          value: "created",
          width: "10rem",
        },
        {
          text: this.$t("events.title"),
          value: "title",
        },
        {
          text: this.$t("events.category"),
          value: "category",
          sortable: false,
          width: "8rem",
        },
        {
          text: this.$t("events.importance"),
          value: "importance",
          width: "8rem",
        },
        {
          text: this.$t("events.expires"),
          value: "expiration_date",
        },
      ];
    },
    url() {
      let url = "/api/events/user-events/";
      let params = [];
      if (this.filterImportance != null) {
        params.push(`importance=${this.filterImportance}`);
      }
      if (this.filterCategory != null) {
        params.push(`category=${this.filterCategory}`);
      }
      if (this.filterRead != null) {
        params.push(`read=${this.filterRead}`);
      }
      if (this.sortBy != null) {
        params.push(`order_by=${this.sortBy}`);
        params.push(`desc=${this.sortDesc ? "true" : "false"}`);
      }
      if (this.searchDebounced) {
        params.push(`search=${this.searchDebounced}`);
      }
      if (this.pageSize) {
        params.push(`page_size=${this.pageSize}`);
      }
      if (this.page) {
        params.push(`page=${this.page}`);
      }
      url = params.length > 0 ? `${url}?` : url;
      return url + params.join("&");
    },
    searchDebounced: {
      get() {
        return this.search;
      },
      set: debounce(function (value) {
        this.search = value;
      }, 500),
    },
    selectedEventsLive() {
      // this.selectedEvents contains whole objects, but those may not be
      // in sync with this.events - most importantly, their read status
      // may be different.
      // Here we return the selected events from this.events
      return this.events.filter((item) =>
        this.selectedEvents.find((rec) => rec.pk === item.pk)
      );
    },
    availableCategoriesAndCounts() {
      return new Map(
        this.storeCounts.category.map((e) => [e.category, e.count])
      );
    },
    availableImportanciesAndCounts() {
      return new Map(
        this.storeCounts.importance.map((e) => [e.importance, e.count])
      );
    },
    availableReadAndCounts() {
      return new Map(this.storeCounts.read.map((e) => [e.read, e.count]));
    },
  },

  methods: {
    parseDateTime,
    isoDateFormat,
    isoDateTimeFormatSpans,
    ...mapActions({ loadEvents: "loadEvents", showSnackbar: "showSnackbar" }),
    fetchEvents: debounce(async function () {
      // we debounce here because we want to wait for all the computed
      // to get recomputed before we fetch the events
      this.loading = true;
      const reply = await this.http({ url: this.url, method: "GET" });
      if (!reply.error) {
        let replyLES = this.loadEventsStat();
        if (replyLES != null) {
          this.eventCount = reply.response.data.count;
          this.events = reply.response.data.results;
        }
      }
      this.loading = false;
    }, 100),
    toggleExpanded(item) {
      if (this.expanded.find((rec) => rec.pk === item.pk)) {
        this.expanded = this.expanded.filter((rec) => rec.pk !== item.pk);
      } else {
        this.expanded.push(item);
        // mark as read when expanding - we need to do this explicitly because
        // the expanded event is not triggered when doing it by manipulating
        // the expanded array
        this.markRead({ item, read: true, value: true, refresh: false });
      }
    },
    async markReadLowLevel({ item, read }) {
      return await this.http({
        url: `/api/events/user-events/${item.pk}/mark-read/`,
        method: "POST",
        data: { read },
      });
    },
    async markRead({ item, read, value, refresh }) {
      if (value === false) {
        // value is false when markRead is called from the expanded event when
        // collapsing - we try to refetch when filter read is set to false to update
        // the list
        if (this.filterRead === false) {
          this.fetchEvents();
        }
        return;
      }
      if (item.read !== read) {
        const reply = await this.markReadLowLevel({ item, read });
        if (!reply.error) {
          item.read = reply.response.data.read;
          if (refresh) {
            await this.fetchEvents();
          } else {
            await this.loadEventsStat(); // update the badge, etc.
          }
        }
      }
    },
    async markSelectedRead(read) {
      const eventIds = this.selectedEventsLive
        .filter((item) => item.read != read)
        .map((item) => item.pk);
      const reply = await this.http({
        url: "/api/events/user-events/mark-read/",
        method: "POST",
        data: { event_ids: eventIds, read },
      });
      if (reply.error) {
        await this.showSnackbar({
          content: this.$t("mark_all_read_error"),
          color: "error",
        });
      } else {
        await this.showSnackbar({
          content: this.$tc(
            "mark_all_read_success",
            reply.response.data.updated
          ),
          color: "success",
        });
      }
      this.fetchEvents();
      this.selectedEvents = [];
    },
    markdownToHtml(content) {
      const renderer = new marked.Renderer();
      renderer.link = (href, title, text) =>
        `<a target="_blank" href="${href}" title="${title}">${text}</a>`;

      let html = marked.parse(content, {
        breaks: false,
        gfm: true,
        renderer: renderer,
      });
      return html;
    },
    async loadEventsStat() {
      return await this.loadEvents({
        read: this.filterRead,
        category: this.filterCategory,
        importance: this.filterImportance,
        search: this.searchDebounced,
      });
    },
  },

  created() {
    this.fetchEvents();
  },

  watch: {
    url() {
      this.fetchEvents();
    },
    storeNewestEventId() {
      console.debug("storeEventCount changed");
      this.fetchEvents();
    },
    storeUnreadEventCount() {
      console.debug("storeUnreadEventCount changed");
      this.loadEventsStat();
    },
  },
};
</script>

<style scoped lang="scss">
div.event-text {
  p {
    margin-bottom: 0.25rem;
  }
}
</style>
