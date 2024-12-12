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
      <v-row>
        <v-col cols="auto">
          <v-select
            :label="$t('pub_type_filter')"
            :items="pubTypes"
            v-model="selectedPubType"
          >
            <template v-slot:item="{ item }">
              <v-icon small v-text="item.icon + ' fa-fw'" class="mr-2"></v-icon>
              {{ item.text }}
            </template>
            <template v-slot:selection="{ item }">
              <v-icon small v-text="item.icon + ' fa-fw'" class="mr-2"></v-icon>
              {{ item.text }}
            </template>
          </v-select>
        </v-col>
        <v-col cols="auto">
          <TagSelector
            v-model="selectedTags"
            scope="title"
            dont-check-exclusive
          />
        </v-col>
        <v-col cols="auto">
          <v-switch v-model="showDOI" :label="$t('show_doi')"></v-switch>
        </v-col>

        <v-spacer></v-spacer>
        <v-col cols="auto">
          <v-text-field
            v-model="searchDebounced"
            append-icon="fa-search"
            :label="$t('labels.search')"
            single-line
            hide-details
            clearable
            clear-icon="fa-times"
          ></v-text-field>
        </v-col>
      </v-row>
    </v-card-title>
    <v-skeleton-loader v-if="loading && titles.length === 0" type="table" />
    <v-data-table
      v-else
      :items="filteredTitles"
      :loading="loading"
      :headers="headers"
      :footer-props="{ itemsPerPageOptions: [10, 25, 50, 100] }"
      :server-items-length="totalTitleCount"
      :must-sort="true"
      :items-per-page.sync="itemsPerPage"
      :sort-by.sync="orderBy"
      :page.sync="page"
      :sort-desc.sync="orderDesc"
      :no-data-text="emptyDataText"
    >
      <template v-slot:item.name="{ item }">
        <router-link
          v-if="platformId"
          :to="{
            name: 'platform-title-detail',
            params: { platformId: platformId, titleId: item.pk },
          }"
        >
          <ShortenText :text="item.name" :length="50" />
        </router-link>
        <router-link
          v-else
          :to="{
            name: 'title-detail',
            params: { platformId: null, titleId: item.pk },
          }"
        >
          <ShortenText :text="item.name" />
        </router-link>
      </template>
      <template v-slot:item.pub_type="{ item }">
        <v-tooltip bottom>
          <template v-slot:activator="{ on }">
            <v-icon small v-on="on">{{ iconForPubType(item.pub_type) }}</v-icon>
          </template>

          <span>{{ $t(titleForPubType(item.pub_type)) }}</span>
        </v-tooltip>
      </template>
      <template
        v-for="ig in activeInterestGroups"
        v-slot:[slotName(ig)]="{ item }"
      >
        <span
          v-if="item.interests.loading"
          class="fas fa-spinner fa-spin subdued"
          :key="ig.pk"
        ></span>
        <span v-else :key="ig.pk">
          {{ formatInteger(item.interests[ig.short_name]) }}
        </span>
      </template>
      <template v-slot:item.ratios="{ item }">
        <SimplePie
          size="32"
          :parts="
            Object.values(item.interests).map((item, index) => {
              return { size: item, color: color(index) };
            })
          "
        />
      </template>
      <template v-slot:item.platforms="{ item }">
        <v-tooltip
          v-for="([platform_id, interest], index) of Object.entries(
            item.interests
          )"
          :key="index"
          bottom
          max-width="600px"
        >
          <template #activator="{ on }">
            <div v-on="on">
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

      <template #item.tags="{ item }">
        <TagChip
          v-for="tag in objIdToTags.get(item.pk)"
          :key="tag.pk"
          :tag="tag"
          small
          show-class
        />
      </template>

      <template #no-data v-if="!filtersApplied && !noDataText">
        <NoDataInTableWidget
          scope="title"
          :platform-id="platformId"
          @goto-sushi="$emit('goto-sushi')"
        />
      </template>
    </v-data-table>
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
      orderBy: this.orderInterest ? this.orderInterest : "name",
      orderDesc: !!this.orderInterest,
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
          type: String,
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
          text: this.$i18n.t("title_fields.name"),
          value: "name",
          // class: "auto-width",
          // cellClass: "auto-width",
        },
        {
          text: this.$i18n.t("title_fields.type"),
          value: "pub_type",
          // class: "auto-width",
          // cellClass: "auto-width",
        },
        {
          text: this.$i18n.t("title_fields.isbn"),
          value: "isbn",
          // class: "auto-width",
          // cellClass: "auto-width",
        },
        {
          text: this.$i18n.t("title_fields.issn"),
          value: "issn",
          // class: "auto-width",
          // cellClass: "auto-width",
        },
        {
          text: this.$i18n.t("title_fields.eissn"),
          value: "eissn",
          // class: "auto-width",
          // cellClass: "auto-width",
        },
      ];
      if (this.showDOI) {
        base.push({
          text: this.$i18n.t("title_fields.doi"),
          value: "doi",
          // class: "auto-width",
          // cellClass: "auto-width",
        });
      }
      if (this.titlesOnMultiplePlatforms) {
        base.push({
          text: this.$i18n.t("title_fields.ratios"),
          value: "ratios",
          sortable: false,
          // class: "auto-width",
          // cellClass: "auto-width",
        });
        base.push({
          text: this.$i18n.t("title_fields.platforms"),
          value: "platforms",
          sortable: false,
        });
        base.push({
          text: this.$i18n.t("title_fields.platform_count"),
          value: "platform_count",
        });
        base.push({
          text: this.$i18n.t("title_fields.total_interest"),
          value: "total_interest",
          align: "right",
        });
      } else {
        for (let ig of this.activeInterestGroups) {
          base.push({
            text: ig.name,
            value: "interests." + ig.short_name,
            class: "wrap text-xs-right",
            align: "right",
          });
        }
        base.push({
          text: this.$t("labels.tags"),
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
        let sortBy = this.orderBy;
        if (sortBy) {
          if (sortBy.startsWith("interests.")) {
            sortBy = sortBy.replace("interests.", "");
          }
        }
        let tags = "";
        if (this.selectedTags.length) {
          tags = "&tags=" + this.selectedTags.join(",");
        }
        return (
          this.url +
          `&page_size=${this.itemsPerPage}&order_by=${sortBy}&desc=${
            this.orderDesc
          }&page=${this.page}&q=${this.search ?? ""}&pub_type=${
            this.selectedPubType || ""
          }${tags}`
        );
      }
      return this.url;
    },
    pubTypes() {
      let all = {
        text: this.$t("pub_type.all"),
        value: null,
        icon: "fa-expand",
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
            this.titles.map((item) => item.pk)
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
