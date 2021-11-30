<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml" src="../locales/pub-types.yaml"></i18n>
<i18n lang="yaml">
en:
  columns:
    interest: Interest
  show_doi: Show DOI
  pub_type_filter: Publication type filter
  no_records: No matching titles were found
cs:
  columns:
    interest: Zájem
  show_doi: Zobrazit DOI
  pub_type_filter: Filtr typu publikace
  no_records: Nebyly nalezeny žádné odpovídající tituly
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
          ></v-text-field>
        </v-col>
      </v-row>
    </v-card-title>
    <v-data-table
      :items="filteredTitles"
      :headers="headers"
      :loading="loading"
      :footer-props="{ itemsPerPageOptions: [10, 25, 50, 100] }"
      :server-items-length="totalTitleCount"
      :must-sort="true"
      :items-per-page="25"
      sort-by="name"
      :page="1"
      :options.sync="options"
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
        <span
          v-for="([platform, interest], index) of Object.entries(
            item.interests
          )"
          :key="index"
        >
          <span class="coma" v-if="index > 0">, </span>
          <span :style="{ color: color(index) }">{{ platform }}</span>
          <span class="interest ml-1">{{ interest }}</span>
        </span>
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

export default {
  name: "TitleList",
  components: { ShortenText, SimplePie },
  props: {
    url: { required: true },
    platformId: { required: false },
    orderInterest: { required: false, default: null, type: String },
    interestByPlatform: { default: false, type: Boolean },
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
      pubTypes: [],
      options: {
        sortDesc: [!!this.orderInterest],
        sortBy: [this.orderInterest ? this.orderInterest : "name"],
      },
      cancelTokenSource: null,
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
        },
        {
          text: this.$i18n.t("title_fields.type"),
          value: "pub_type",
        },
        {
          text: this.$i18n.t("title_fields.isbn"),
          value: "isbn",
        },
        {
          text: this.$i18n.t("title_fields.issn"),
          value: "issn",
        },
        {
          text: this.$i18n.t("title_fields.eissn"),
          value: "eissn",
        },
      ];
      if (this.showDOI) {
        base.push({
          text: this.$i18n.t("title_fields.doi"),
          value: "doi",
        });
      }
      if (this.interestByPlatform) {
        base.push({
          text: this.$i18n.t("title_fields.ratios"),
          value: "ratios",
          sortable: false,
        });
        base.push({
          text: this.$i18n.t("title_fields.platforms"),
          value: "platforms",
          sortable: false,
        });
        base.push({
          text: this.$i18n.t("title_fields.nonzero_platforms"),
          value: "nonzero_platform_count",
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
      }
      return base;
    },
    filteredTitles() {
      return this.titles;
    },
    fullUrl() {
      let { sortBy, sortDesc, page, itemsPerPage } = this.options;
      if (this.url) {
        if (!sortBy) {
          sortBy = "";
        } else {
          if (Array.isArray(sortBy)) {
            sortBy = sortBy[0];
          }
          if (sortBy.startsWith("interests.")) {
            sortBy = sortBy.replace("interests.", "");
          }
        }
        if (Array.isArray(sortDesc)) {
          sortDesc = sortDesc[0];
        }
        return (
          this.url +
          `&page_size=${itemsPerPage}&order_by=${sortBy}&desc=${sortDesc}&page=${page}&q=${
            this.search
          }&pub_type=${this.selectedPubType || ""}`
        );
      }
      return this.url;
    },
    palette() {
      return echartPalette;
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
      // it seems there is an issue in i18n that makes this.$i18n undefined after the
      // await call later on. To make i18n work, we store it here and then pass it on
      // to the extractPubTypes method
      const i18n = this.$i18n;
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
          this.loading = false;
        } catch (error) {
          if (axios.isCancel(error)) {
            console.debug("Request cancelled");
          } else {
            this.showSnackbar({
              content: "Error loading title list: " + error,
            });
            this.loading = false;
          }
        } finally {
          // normally, we would do this.loading = false here, but we do not want to do it
          // in case the request was cancelled, as it means there are more data arriving later
          // and this is not the most recent request
        }

        if (!this.selectedPubType) {
          // if we do not filter by pubType, we extract the available pub types here
          this.pubTypes = this.extractPubTypes(i18n);
        }
      }
    },
    extractPubTypes(i18n) {
      let all = {
        text: i18n.t("pub_type.all"),
        value: null,
        icon: "fa-expand",
      };
      return [
        all,
        ...pubTypes.map((item) => {
          return {
            text: i18n.t(item.title),
            icon: item.icon,
            value: item.code,
          };
        }),
      ];
    },
    postprocessData() {},
    slotName: (ig) => "item.interests." + ig.short_name,
    color: (index) => echartPalette[index % echartPalette.length],
  },
  watch: {
    fullUrl() {
      this.loadData();
    },
  },
  mounted() {
    // it seems that watching fullUrl is enough
    //this.loadData()
  },
};
</script>

<style scoped lang="scss">
span.interest {
  font-weight: bold;
  color: #555555;
  font-size: 75%;
}
span.coma {
  color: #999999;
}
div.ddd {
  vertical-align: top;
  //height: 100%;
}
</style>
