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
  <v-data-table-server
    v-model="selectedEvents"
    :items="events"
    item-key="pk"
    :headers="headers"
    v-model:expanded="expanded"
    expand-icon="fa fa-caret-down"
    :loading="loading"
    v-model:sort-by="sortBy"
    :items-length="eventCount"
    v-model:page="page"
    v-model:items-per-page="pageSize"
    :search="searchDebounced"
    return-object
    density="default"
  >
    <template #headers="{ columns }">
      <TableCustomSort
        :columns="columns"
        v-model:externalOrderBy="sortBy"
        :show-select-all="true"
        :all-selected="allEventsSelected"
        :unsortable-column-values="['data-table-select', 'data-table-expand']"
        @toggle-select-all="toggleSelectAll"
      />
    </template>

    <template #item.data-table-expand="{ item }">
      <v-btn @click="toggleExpanded(item)" icon size="small" variant="text">
        <v-icon size="small">
          fa fa-angle-{{ expanded.includes(item) ? "down" : "right" }}
        </v-icon>
      </v-btn>
    </template>

    <template #item.read="{ item }">
      <v-icon
        v-if="item.read"
        @click="markRead({ item, read: false, refresh: false })"
        size="small"
        >far fa-envelope-open</v-icon
      >
      <v-icon
        v-else
        @click="markRead({ item, read: true, refresh: true })"
        size="small"
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
      <EventCategoryMark :item="item" :bold="!item.read"></EventCategoryMark>
    </template>
    <template #item.importance="{ item }">
      <EventImportanceIcon
        :importance="item.importance"
        small
      ></EventImportanceIcon>
      <span class="ml-2">{{ $t("event_importance." + item.importance) }}</span>
    </template>
    <template #item.expiration_date="{ item }">
      <span v-if="item.expiration_date">{{
        isoDateFormat(parseDateTime(item.expiration_date))
      }}</span>
    </template>
    <template #item.platform="{ item }">
      <span>{{ item.platform?.name || item.platform?.short_name || "" }}</span>
    </template>
    <template v-slot:expanded-row="{ columns, item }">
      <tr class="item_expanded_space">
        <td :colspan="columns.length" class="px-2 py-2">
          <v-sheet class="pa-3">
            <v-tooltip
              max-width="600px"
              v-if="item.expiration_date"
              location="bottom"
            >
              <template #activator="{ props }">
                <div class="caption float-right" v-bind="props">
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
      </tr>
    </template>
    <template #top>
      <v-row>
        <v-col cols="12" md="4" lg="3" xl="2">
          <EventCategorySelect
            v-model="filterCategory"
            show-all
            :categories="availableCategoriesAndCounts"
          ></EventCategorySelect>
        </v-col>
        <v-col cols="6" md="2" lg="2" xl="1">
          <EventImportanceSelect
            v-model="filterImportance"
            show-all
            :importancies="availableImportanciesAndCounts"
          ></EventImportanceSelect>
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
            item-title="text"
          >
            <template #item="{ item, props }">
              <v-list-item v-bind="props" title="">
                <v-list-item-title>
                  {{ item.raw.text }}
                  <span
                    v-if="item.raw.count"
                    class="float-right text-caption"
                    >{{ item.raw.count }}</span
                  >
                </v-list-item-title>
              </v-list-item>
            </template>
          </v-select>
        </v-col>
        <v-col cols="12" md="4" lg="3" xl="2">
          <PlatformSelector
            :platforms="platformList"
            v-model="filterPlatform"
            :loading="loadingPlatforms"
          >
          </PlatformSelector>
        </v-col>
        <v-spacer></v-spacer>
        <v-col cols="12" md="4" lg="3" xl="2">
          <v-text-field
            v-model="searchDebounced"
            append-inner-icon="fa fa-search"
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
            :disabled="
              selectedEvents.length === 0 || selectedUnreadEventsCount === 0
            "
          >
            <v-icon class="mr-2" size="small">far fa-envelope-open</v-icon>
            {{ $t("events.mark_as_read") }}
            <span v-if="selectedUnreadEventsCount > 0" class="ml-1"
              >({{ selectedUnreadEventsCount }})</span
            >
          </v-btn>
        </v-col>
      </v-row>
    </template>
  </v-data-table-server>
</template>

<script>
import EventCategoryMark from "@/components/events/EventCategoryMark.vue";
import EventCategorySelect from "@/components/events/EventCategorySelect.vue";
import EventImportanceIcon from "@/components/events/EventImportanceIcon.vue";
import EventImportanceSelect from "@/components/events/EventImportanceSelect.vue";
import PlatformSelector from "@/components/selectors/PlatformSelector.vue";
import TableCustomSort from "@/components/tables/TableCustomSort";
import {
  isoDateFormat,
  isoDateTimeFormatSpans,
  parseDateTime,
} from "@/libs/dates";
import cancellation from "@/mixins/cancellation";
import stateTracking from "@/mixins/stateTracking";
import debounce from "lodash/debounce";
import { marked } from "marked";
import { mapActions, mapState } from "vuex";

export default {
  name: "EventList",
  components: {
    EventCategorySelect,
    EventImportanceSelect,
    EventCategoryMark,
    EventImportanceIcon,
    TableCustomSort,
    PlatformSelector,
  },

  mixins: [cancellation, stateTracking],

  data() {
    return {
      events: [],
      selectedEvents: [],
      platformList: [],
      eventCount: 0,
      loading: false,
      loadingPlatforms: false,
      expanded: [],
      search: "",
      filterCategory: null,
      filterImportance: null,
      filterRead: null,
      filterPlatform: null,
      sortBy: [{ key: "created", order: "desc" }],
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
          type: Object,
        },
        {
          name: "filterPlatform",
          type: Number,
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
          title: "",
          value: "data-table-expand",
          sortable: false,
          align: "start",
        },
        {
          title: "",
          value: "data-table-select",
          sortable: false,
          align: "start",
        },
        {
          title: this.$t("events.read"),
          value: "read",
          width: "5rem",
          key: "read",
          sortable: true,
        },
        {
          title: this.$t("events.date"),
          value: "created",
          width: "10rem",
          sortable: true,
          order: "reverse",
        },
        {
          title: this.$t("platform"),
          value: "platform",
          key: "platform",
          sortable: true,
        },
        {
          title: this.$t("events.title"),
          value: "title",
          key: "title",
          sortable: true,
        },
        {
          title: this.$t("events.category"),
          value: "category",
          sortable: false,
          width: "8rem",
        },
        {
          title: this.$t("events.importance"),
          value: "importance",
          width: "8rem",
          key: "importance",
          sortable: true,
        },
        {
          title: this.$t("events.expires"),
          value: "expiration_date",
          key: "expiration_date",
          sortable: true,
          order: "reverse",
        },
      ];
    },
    urlFilters() {
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
      if (this.filterPlatform != null) {
        params.push(`platform=${this.filterPlatform}`);
      }
      if (this.sortBy != null && Array.isArray(this.sortBy) && this.sortBy[0]) {
        params.push(`order_by=${this.sortBy[0].key}`);
        params.push(
          `desc=${this.sortBy[0].order === "desc" ? "true" : "false"}`,
        );
      }
      if (this.searchDebounced) {
        params.push(`search=${this.searchDebounced}`);
      }
      if (this.pageSize) {
        params.push(`page_size=${this.pageSize}`);
      }
      return params;
    },
    url() {
      let url = "/api/events/user-events/";
      let params = this.urlFilters;
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
    availableCategoriesAndCounts() {
      return new Map(
        this.storeCounts.category.map((e) => [e.category, e.count]),
      );
    },
    availableImportanciesAndCounts() {
      return new Map(
        this.storeCounts.importance.map((e) => [e.importance, e.count]),
      );
    },
    availableReadAndCounts() {
      return new Map(this.storeCounts.read.map((e) => [e.read, e.count]));
    },
    allEventsSelected() {
      return (
        this.eventCount > 0 && this.selectedEvents.length === this.eventCount
      );
    },
    selectedUnreadEventsCount() {
      return this.selectedEvents.filter((item) => !item.read).length;
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
      const eventIds = this.selectedEvents
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
            reply.response.data.updated,
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
    async toggleSelectAll(value) {
      if (value) {
        let params = this.urlFilters.filter(
          (e) => !e.startsWith("page=") && !e.startsWith("page_size="),
        );
        params.push(`page_size=${this.eventCount}`);
        const url = "/api/events/user-events/?" + params.join("&");
        const response = await this.http({
          url: url,
          method: "GET",
        });
        if (!response.error) {
          this.selectedEvents = response.response.data.results;
        }
      } else {
        this.selectedEvents = [];
      }
    },
    async fetchPlatforms() {
      this.platformList = [];
      this.loadingPlatforms = true;
      let result = await this.http({
        url: "/api/organization/-1/all-platform/?has_event=true",
      });
      this.loadingPlatforms = false;
      if (!result.error) {
        this.platformList = result.response.data;
        this.platformList.sort((a, b) => {
          let atext = a.name || a.short_name;
          let btext = b.name || b.short_name;
          return atext.localeCompare(btext);
        });
      }
    },
  },

  created() {
    this.fetchEvents();
  },

  mounted() {
    this.fetchPlatforms();
  },

  watch: {
    url() {
      this.fetchEvents();
    },
    urlFilters() {
      this.page = 1; // reset pagination when filter changes
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

<style lang="scss">
div.event-text {
  p {
    margin-bottom: 0.5rem;
  }

  hr {
    margin: 1rem 0;
    border: none;
    background-color: #ddd;
    height: 1px;
  }
}
</style>
