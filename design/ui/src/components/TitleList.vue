<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml" src="@/locales/pub-types.yaml"></i18n>

<i18n lang="yaml">
en:
  columns:
    interest: Interest
  show_doi: Show DOI
  pub_type_filter: Publication type filter
  no_records: No matching titles were found
  platforms_tt: Title interest for platform "{platform}" is {interest}.
  yops_tt: Years of publication extracted from the TR report span from {min} to {max}.
  no_yops_tt: No years of publication were extracted from the TR report.
cs:
  columns:
    interest: Zájem
  show_doi: Zobrazit DOI
  pub_type_filter: Filtr typu publikace
  no_records: Nebyly nalezeny žádné odpovídající tituly
  platforms_tt: Zájem o platformu "{platform}" je {interest}.
  yops_tt: Roky publikace extrahované z TR reportu jsou od {min} do {max}.
  no_yops_tt: Nebyly nalezeny žádné roky publikace.
</i18n>

<template>
  <v-card>
    <v-card-title>
      <v-row fluid>
        <v-col cols="auto">
          <v-sheet>
            <v-select
              :label="$t('pub_type_filter')"
              :items="pubTypes"
              v-model="selectedPubType"
              :search="selectedTags"
              style="min-width: 245px"
              density="comfortable"
            >
              <template v-slot:item="{ item, props }">
                <v-list-item v-bind="props">
                  <template v-slot:prepend>
                    <v-icon size="x-small" class="mr-0"
                      >{{ item.raw.icon }} "fa-fw"</v-icon
                    >
                  </template>
                </v-list-item>
              </template>
              <template v-slot:selection="{ item }">
                <v-icon size="small" class="mr-2"
                  >{{ item.raw.icon }} "fa-fw"</v-icon
                >
                {{ item.raw.title }}
              </template>
            </v-select>
          </v-sheet>
        </v-col>
        <v-col cols="auto">
          <v-sheet>
            <TagSelector
              v-model="selectedTags"
              scope="title"
              dont-check-exclusive
              density="comfortable"
              color="primary"
              min-width="200px"
            ></TagSelector>
          </v-sheet>
        </v-col>
        <v-col>
          <v-sheet>
            <v-switch
              style="min-width: 115px"
              v-model="showDOI"
              hide-details="auto"
              color="primary"
              density="comfortable"
              :label="$t('show_doi')"
            ></v-switch>
          </v-sheet>
        </v-col>
        <v-spacer></v-spacer>
        <v-col>
          <v-sheet>
            <v-text-field
              style="min-width: 200px"
              v-model="searchDebounced"
              append-inner-icon="fa fa-search"
              :label="$t('labels.search')"
              single-line
              hide-details
              clearable
              density="comfortable"
              clear-icon="fa fa-times"
            ></v-text-field>
          </v-sheet>
        </v-col>
      </v-row>
    </v-card-title>
    <v-skeleton-loader
      v-if="loading && titles.length === 0"
      type="table"
    ></v-skeleton-loader>
    <v-data-table-server
      v-else
      v-model:items-per-page="itemsPerPage"
      :headers="headers"
      :items="filteredTitles"
      :items-length="totalTitleCount"
      :loading="loading"
      :must-sort="true"
      v-model:sort-by="orderBy"
      v-model:page="page"
      :no-data-text="emptyDataText"
      class="auto-table"
      variant="comfortable"
    >
      <template #item.name="{ item }">
        <router-link
          v-if="platformId"
          :to="{
            name: 'platform-title-detail',
            params: { platformId: platformId, titleId: item.pk },
          }"
        >
          <ShortenText :text="item.name" :length="50"></ShortenText>
        </router-link>
        <router-link
          v-else
          :to="{
            name: 'title-detail',
            params: { platformId: null, titleId: item.pk },
          }"
        >
          <ShortenText :text="item.name"></ShortenText>
        </router-link>
      </template>
      <template #item.pub_type="{ item }">
        <v-tooltip location="bottom">
          <template v-slot:activator="{ props }">
            <v-icon size="small" v-bind="props" color="lighterIcons">{{
              iconForPubType(item.pub_type)
            }}</v-icon>
          </template>
          <span>{{ $t(titleForPubType(item.pub_type)) }}</span>
        </v-tooltip>
      </template>
      <template
        v-for="ig in activeInterestGroups"
        :key="ig.pk"
        v-slot:[slotName(ig)]="{ item }"
      >
        <span
          v-if="item.interests.loading"
          class="fas fa-spinner fa-spin subdued"
        ></span>
        <span v-else>
          {{ formatInteger(item.interests[ig.short_name]) }}
        </span>
      </template>
      <template #item.ratios="{ item }">
        <SimplePie
          size="32"
          :parts="
            Object.values(item.interests).map((item, index) => {
              return { size: item, color: color(index) };
            })
          "
        ></SimplePie>
      </template>
      <template #item.platforms="{ item }">
        <v-tooltip
          v-for="([platform_id, interest], index) of Object.entries(
            item.interests,
          )"
          :key="index"
          location="bottom"
          max-width="600px"
        >
          <template #activator="{ props }">
            <div v-bind="props">
              <span :style="{ color: color(index) }">{{
                translatePlatformId(platform_id)
              }}</span>
              <span class="interest ml-1">{{ interest }}</span>
              <span v-if="item.yops && item.yops[platform_id]" class="yops">
                ({{ item.yops[platform_id].min }} -
                {{ item.yops[platform_id].max }})
              </span>
            </div>
          </template>
          <div>
            {{
              $t("platforms_tt", {
                platform: translatePlatformId(platform_id),
                interest: interest,
              })
            }}
          </div>
          <div v-if="item.yops && item.yops[platform_id]">
            {{ $t("yops_tt", { ...item.yops[platform_id] }) }}
          </div>
          <div v-else>
            {{ $t("no_yops_tt") }}
          </div>
        </v-tooltip>
      </template>
      <template #item.tags="{ props, item }">
        <TagChip
          v-bind="props"
          v-for="tag in objIdToTags.get(item.pk)"
          :key="tag.pk"
          :tag="tag"
          size="small"
          show-class
        ></TagChip>
      </template>

      <template #no-data v-if="!filtersApplied && !noDataText">
        <NoDataInTableWidget
          scope="title"
          :platform-id="platformId"
          @goto-sushi="$emit('goto-sushi')"
        />
      </template>
    </v-data-table-server>
  </v-card>
</template>

<script>
import axios from "axios";
import { mapActions, mapGetters } from "vuex";
import debounce from "lodash/debounce";
import { formatInteger } from "../libs/numbers";
import { iconForPubType, pubTypes, titleForPubType } from "../libs/pub-types";
import ShortenText from "./ShortenText";
import SimplePie from "@/components/util/SimplePie";
import { echartPalette } from "@/libs/palettes";
import TagSelector from "@/components/tags/TagSelector";
import cancellation from "@/mixins/cancellation";
import tags from "@/mixins/tags";
import TagChip from "@/components/tags/TagChip";
import stateTracking from "@/mixins/stateTracking";
import NoDataInTableWidget from "@/components/NoDataInTableWidget.vue";

export default {
  name: "TitleList",

  mixins: [cancellation, tags, stateTracking],

  components: {
    TagChip,
    TagSelector,
    ShortenText,
    SimplePie,
    NoDataInTableWidget,
  },

  props: {
    url: { required: true },
    platformId: { required: false },
    orderInterest: { required: false, default: null, type: String },
    titlesOnMultiplePlatforms: { default: false, type: Boolean },
    noDataText: { default: null, type: String },
  },

  data() {
    return {
      titles: [],
      search: "",
      totalTitleCount: 0,
      loading: false,
      showDOI: false,
      selectedPubType: null,
      searchString: "",
      cancelTokenSource: null,
      platforms: {},
      // table state
      orderBy: [
        {
          key: this.orderInterest ? this.orderInterest : "name",
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
        { name: "selectedTags", type: Object },
        {
          name: "showDOI",
          type: Boolean,
        },
        {
          name: "orderBy",
          type: Object,
        },
        {
          name: "orderDesc",
          type: Boolean,
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
    searchDebounced: {
      get() {
        return this.search;
      },
      set: debounce(function (value) {
        this.search = value;
      }, 500),
    },
    emptyDataText() {
      return this.noDataText ?? this.$t("no_records");
    },
    headers() {
      let base = [
        {
          title: this.$i18n.t("title_fields.name"),
          value: "name",
          key: "name",
          // class: "auto-width",
          // cellClass: "auto-width",
        },
        {
          title: this.$i18n.t("title_fields.type"),
          value: "pub_type",
          key: "pub_type",
          // class: "auto-width",
          // cellClass: "auto-width",
        },
        {
          title: this.$i18n.t("title_fields.isbn"),
          value: "isbn",
          key: "isbn",
          // class: "auto-width",
          // cellClass: "auto-width",
        },
        {
          title: this.$i18n.t("title_fields.issn"),
          value: "issn",
          key: "issn",
          // class: "auto-width",
          // cellClass: "auto-width",
        },
        {
          title: this.$i18n.t("title_fields.eissn"),
          value: "eissn",
          key: "eissn",
          // class: "auto-width",
          // cellClass: "auto-width",
        },
      ];
      if (this.showDOI) {
        base.push({
          title: this.$i18n.t("title_fields.doi"),
          value: "doi",
          key: "doi",
          // class: "auto-width",
          // cellClass: "auto-width",
        });
      }
      if (this.titlesOnMultiplePlatforms) {
        base.push({
          title: this.$i18n.t("title_fields.ratios"),
          value: "ratios",
          sortable: false,
          // class: "auto-width",
          // cellClass: "auto-width",
        });
        base.push({
          title: this.$i18n.t("title_fields.platforms"),
          value: "platforms",
          sortable: false,
        });
        base.push({
          title: this.$i18n.t("title_fields.platform_count"),
          value: "platform_count",
          key: "platform_count",
        });
        base.push({
          title: this.$i18n.t("title_fields.total_interest"),
          value: "total_interest",
          align: "end",
          key: "total_interest",
        });
      } else {
        for (let ig of this.activeInterestGroups) {
          base.push({
            title: ig.name,
            value: "interests." + ig.short_name,
            class: "wrap text-xs-right",
            align: "end",
            key: "interests." + ig.short_name,
          });
        }
        base.push({
          title: this.$t("labels.tags"),
          value: "tags",
          sortable: false,
        });
      }
      return base;
    },
    filteredTitles() {
      return this.titles;
    },
    fullUrl() {
      if (this.url) {
        let sortBy = this.orderBy[0].key;
        let orderBy = this.orderBy[0].order;
        let sort = "";
        if (sortBy) {
          if (sortBy.startsWith("interests.")) {
            sortBy = sortBy.replace("interests.", "");
          }
          sort = `&order_by=${sortBy}&desc=${
            orderBy === "desc" ? true : false
          }`;
        }
        let tags = "";
        if (this.selectedTags.length) {
          tags = "&tags=" + this.selectedTags.join(",");
        }
        return (
          this.url +
          `&page_size=${this.itemsPerPage}&page=${this.page}&q=${
            this.search ?? ""
          }&pub_type=${this.selectedPubType || ""}${tags}${sort}`
        );
      }
      return this.url;
    },
    pubTypes() {
      let all = {
        title: this.$t("pub_type.all"),
        value: null,
        icon: "fas fa-expand",
      };
      return [
        all,
        ...pubTypes.map((item) => {
          return {
            title: this.$t(item.title),
            icon: item.icon,
            value: item.code,
          };
        }),
      ];
    },
    filtersApplied() {
      // boolean, whether any filters are applied
      return this.search || this.selectedPubType || this.selectedTags.length;
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
          this.titles = response.data.results;
          this.totalTitleCount = response.data.count;
          this.postprocessData();
        } catch (error) {
          if (axios.isCancel(error)) {
            console.debug("Request cancelled");
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

        if (this.titles.length) {
          await this.getTagsForObjectsById(
            "title",
            this.titles.map((item) => item.pk),
          );
        }
        this.loading = false;
      }
    },
    async loadPlatforms() {
      const reply = await this.http({
        method: "GET",
        url: "/api/platform/",
      });
      if (!reply.error) {
        this.platforms = {};
        for (let platform of reply.response.data) {
          this.platforms[platform.pk.toString()] = platform;
        }
      }
    },
    postprocessData() {},
    slotName: (ig) => "item.interests." + ig.short_name,
    color: (index) => echartPalette[index % echartPalette.length],
    translatePlatformId(id) {
      if (this.platforms && this.platforms[id]) {
        return this.platforms[id].short_name;
      }
      return id;
    },
  },

  mounted() {
    this.loadData();
    if (this.titlesOnMultiplePlatforms) {
      this.loadPlatforms();
    }
  },

  watch: {
    fullUrl() {
      this.loadData();
    },
    itemsPerPage() {
      this.page = 1;
    },
    orderBy() {
      this.page = 1;
    },
    orderDesc() {
      this.page = 1;
    },
    selectedTags() {
      this.page = 1;
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

<style scoped lang="scss">
span.interest {
  font-weight: bold;
  color: #555555;
  font-size: 85%;
}

span.yops {
  font-weight: 300;
  color: #777777;
  font-size: 75%;
}
span.coma {
  color: #999999;
}
div.ddd {
  vertical-align: top;
  //height: 100%;
}

div.ttt {
  div {
    table {
      table-layout: fixed !important;
      color: red !important;
    }
  }
}
</style>
