<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/pub-types.yaml"></i18n>

<i18n lang="yaml">
en:
  pub_type_filter: Publication type filter
  no_records: No matching items were found
cs:
  pub_type_filter: Filtr typu publikace
  no_records: Nebyly nalezeny žádné odpovídající položky
</i18n>

<template>
  <v-card>
    <v-card-title>
      <v-row>
        <v-col cols="auto">
          <v-select
            :label="$t('pub_type_filter')"
            :items="pubTypes"
            v-model="selectedPubType"
            item-title="text"
            item-value="value"
            min-width="245px"
            density="comfortable"
          >
            <template v-slot:item="{ props, item }">
              <v-list-item v-bind="props">
                <template v-slot:prepend>
                  <v-icon size="small" class="mr-2"
                    >{{ item.raw.icon }} fa-fw</v-icon
                  >
                </template>
              </v-list-item>
            </template>
            <template v-slot:selection="{ item }">
              <v-icon size="small" class="mr-2"
                >{{ item.raw.icon }} fa-fw</v-icon
              >
              {{ item.raw.text }}
            </template>
          </v-select>
        </v-col>
        <v-spacer></v-spacer>
        <v-col cols="auto">
          <v-text-field
            v-model="searchDebounced"
            :label="$t('labels.search')"
            single-line
            hide-details
            clearable
            clear-icon="fa-times"
            min-width="245px"
            density="comfortable"
          >
            <template v-slot:append-inner>
              <v-icon size="small">fa fa-search</v-icon>
            </template>
          </v-text-field>
        </v-col>
      </v-row>
    </v-card-title>
    <v-skeleton-loader
      v-if="loading && items.length === 0"
      type="table"
    ></v-skeleton-loader>
    <v-data-table-server
      v-else
      :items="filteredItems"
      :loading="loading"
      :headers="headers"
      :items-per-page-options="[10, 25, 50, 100]"
      :items-length="totalItemCount"
      :must-sort="true"
      v-model:items-per-page="itemsPerPage"
      v-model:sort-by="orderBy"
      v-model:page="page"
      :no-data-text="$t('no_records')"
      density="default"
    >
      <template #headers="{ columns }">
        <TableCustomSort :columns="columns" v-model:externalOrderBy="orderBy" />
      </template>
      <template #item.name="{ item }">
        <router-link
          v-if="platformId"
          :to="{
            name: 'platform-title-item-detail',
            params: {
              platformId: platformId,
              titleId: titleId,
              itemId: item.pk,
            },
          }"
        >
          <ShortenText :text="item.name" :length="50"></ShortenText>
        </router-link>
        <router-link
          v-else
          :to="{
            name: 'title-item-detail',
            params: { titleId: titleId, itemId: item.pk },
          }"
        >
          <ShortenText :text="item.name"></ShortenText>
        </router-link>
      </template>
      <template #item.pub_type="{ item }">
        <v-tooltip location="bottom">
          <template v-slot:activator="{ props }">
            <v-icon size="small" v-bind="props">{{
              iconForPubType(item.pub_type)
            }}</v-icon>
          </template>
          <span>{{ $t(titleForPubType(item.pub_type)) }}</span>
        </v-tooltip>
      </template>
      <template #item.doi="{ item }">
        <DoiLink :doi="item.doi" small></DoiLink>
      </template>
      <template
        v-for="ig in activeInterestGroups"
        v-slot:[slotName(ig)]="{ item }"
      >
        <span
          v-if="item.interests && item.interests.loading"
          class="fas fa-spinner fa-spin subdued"
          :key="`loading-${ig.pk}`"
        ></span>
        <span v-else-if="item.interests" :key="`value-${ig.pk}`">
          {{ formatInteger(item.interests[ig.short_name]) }}
        </span>
        <span v-else :key="`empty-${ig.pk}`">-</span>
      </template>
    </v-data-table-server>
  </v-card>
</template>

<script>
import axios from "axios";
import { mapActions, mapGetters } from "vuex";
import debounce from "lodash/debounce";
import { formatInteger } from "@/libs/numbers";
import { iconForPubType, pubTypes, titleForPubType } from "@/libs/pub-types";
import ShortenText from "@/components/ShortenText";
import cancellation from "@/mixins/cancellation";
import stateTracking from "@/mixins/stateTracking";
import DoiLink from "@/components/util/DoiLink.vue";
import TableCustomSort from "@/components/tables/TableCustomSort";

export default {
  name: "ItemList",

  mixins: [cancellation, stateTracking],

  components: { DoiLink, ShortenText, TableCustomSort },

  props: {
    platformId: { required: false },
    organizationId: { required: false },
    titleId: { required: false },
    orderInterest: { required: false, default: null, type: String },
  },

  data() {
    return {
      items: [],
      search: "",
      totalItemCount: 0,
      loading: false,
      selectedPubType: null,
      searchString: "",
      cancelTokenSource: null,
      // table state
      orderBy: [
        {
          key: this.orderInterest || "name",
          order: !this.orderInterest ? "asc" : "desc",
        },
      ],
      page: 1,
      itemsPerPage: 25,
      // state tracking support
      watchedAttrs: [
        {
          name: "search",
          type: String,
        },
        {
          name: "selectedPubType",
          type: String,
        },
        {
          name: "orderBy",
          type: Object,
        },
        {
          name: "page",
          type: Number,
        },
        {
          name: "itemsPerPage",
          type: Number,
          var: "ipp",
        },
      ],
    };
  },

  computed: {
    ...mapGetters("interest", {
      activeInterestGroups: "selectedGroupObjects",
    }),
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
    }),
    searchDebounced: {
      get() {
        return this.search;
      },
      set: debounce(function (value) {
        this.search = value;
      }, 500),
    },
    headers() {
      let base = [
        {
          title: this.$i18n.t("title_fields.name"),
          value: "name",
          sortable: true,
        },
        {
          title: this.$i18n.t("title_fields.type"),
          value: "pub_type",
          sortable: true,
        },
        {
          title: this.$i18n.t("title_fields.isbn"),
          value: "isbn",
          sortable: true,
        },
        {
          title: this.$i18n.t("title_fields.issn"),
          value: "issn",
          sortable: true,
        },
        {
          title: this.$i18n.t("title_fields.eissn"),
          value: "eissn",
          sortable: true,
        },
        {
          title: this.$i18n.t("title_fields.doi"),
          value: "doi",
          sortable: true,
        },
      ];

      for (let ig of this.activeInterestGroups) {
        base.push({
          title: ig.name,
          value: "interests." + ig.short_name,
          class: "wrap text-xs-right",
          align: "right",
          order: "reverse",
          sortable: true,
        });
      }
      return base;
    },
    filteredItems() {
      return this.items;
    },
    url() {
      let base = "/api/";
      if (this.organizationId)
        base = `/api/organization/${this.organizationId}/`;
      if (this.platformId) base += `platform/${this.platformId}/`;
      if (this.titleId) base += `title/${this.titleId}/`;
      return base + "item/";
    },
    fullUrl() {
      let sortBy =
        this.orderBy[0]?.key ||
        (this.orderInterest ? this.orderInterest : "name");
      let orderBy =
        this.orderBy[0]?.order || (!this.orderInterest ? "asc" : "desc");
      if (sortBy) {
        if (sortBy.startsWith("interests.")) {
          sortBy = sortBy.replace("interests.", "");
        }
      }
      return this.$router.resolve({
        path: this.url,
        query: {
          page_size: this.itemsPerPage,
          order_by: sortBy,
          desc: orderBy === "desc" ? "true" : "false",
          page: this.page,
          search: this.search ?? "",
          pub_type: this.selectedPubType || "",
          start: this.dateRangeStart,
          end: this.dateRangeEnd,
        },
      }).href;
    },
    pubTypes() {
      let all = {
        text: this.$t("pub_type.all"),
        value: null,
        icon: "fa fa-expand",
      };
      return [
        all,
        ...pubTypes.map((item) => {
          return {
            text: this.$t(item.title),
            icon: item.icon,
            value: item.code,
          };
        }),
      ];
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    formatInteger: formatInteger,
    iconForPubType: iconForPubType,
    titleForPubType: titleForPubType,
    async loadData() {
      // we must cancel previous request in order to prevent stale long-loading data to be
      // pulled in
      if (this.cancelTokenSource) {
        this.cancelTokenSource.cancel("new data requested");
        this.cancelTokenSource = null;
      }
      if (this.fullUrl) {
        this.loading = true;
        this.cancelTokenSource = axios.CancelToken.source();
        try {
          let response = await axios.get(this.fullUrl, {
            cancelToken: this.cancelTokenSource.token,
          });
          this.items = response.data.results;
          this.totalItemCount = response.data.count;
          this.postprocessData();
        } catch (error) {
          if (axios.isCancel(error)) {
            console.debug("Request cancelled");
            return;
          } else if (error.response.status === 404 && this.page > 1) {
            // try reloading the first page
            console.debug("Invalid page, reloading first page");
            this.page = 1;
            return;
          } else {
            this.showSnackbar({
              content: "Error loading title list: " + error,
            });
            this.loading = false;
            return;
          }
        } finally {
          // normally, we would do this.loading = false here, but we do not want to do it
          // in case the request was cancelled, as it means there are more data arriving later
          // and this is not the most recent request
        }
        this.loading = false;
      }
    },
    postprocessData() {},
    slotName: (ig) => "item.interests." + ig.short_name,
  },

  mounted() {
    this.loadData();
  },

  watch: {
    fullUrl() {
      this.loadData();
    },
    itemsPerPage() {
      this.page = 1;
    },
    orderBy: {
      handler(newOrderBy) {
        if (!newOrderBy || newOrderBy.length === 0) {
          this.orderBy = [
            {
              key: this.orderInterest ? this.orderInterest : "name",
              order: !this.orderInterest ? "asc" : "desc",
            },
          ];
        }
        this.page = 1;
      },
      deep: true,
    },
    selectedPubType() {
      this.page = 1;
    },
    searchDebounced() {
      this.page = 1;
    },
    url() {
      // if the base url has changed, it means that either the date range or the
      // platform has changed, so we need to reset the page
      this.page = 1;
    },
  },
};
</script>
