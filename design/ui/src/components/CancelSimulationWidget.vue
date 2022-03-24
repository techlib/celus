<i18n src="@/locales/common.yaml" lang="yaml"></i18n>
<i18n lang="yaml">
en:
  selected_unique_title_count: Number of unique titles in selected platforms
  total_unique_title_count: Total number of unique titles
  selected_titles_interest: Sum of interest for titles available from selected platforms
  total_interest: Total interest for all titles
  unique_title_count: Number of unique titles
  title_interest: Interest in titles
  unique_title_interest: Interest in unique titles
  preparing_data: Preparing data. Please wait, it may take a while.

cs:
  selected_unique_title_count: Počet unikátních titulů na vybraných platformách
  total_unique_title_count: Celkový počet unikátních titulů
  selected_titles_interest: Součet zájmu pro tituly dostupné na vybraných platformách
  total_interest: Celkový zájem pro všechny tituly
  unique_title_count: Počet unikátních titulů
  title_interest: Zájem o tituly
  unique_title_interest: Zájem o unikátní tituly
  preparing_data: Připravuji data. Prosím vyčkejte, může to chvíli trvat.
</i18n>

<template>
  <div>
    <div class="mb-4">
      <TitleTypeFilterWidget v-model="selectedPubTypes" />
    </div>
    <v-alert v-if="selectedPubTypes.length === 0" type="info" outlined>
      {{ $t("warnings.select_one_title_type") }}
    </v-alert>

    <div v-else>
      <div v-if="loading || preparingData">
        <LoaderWidget
          :text="$t('preparing_data')"
          show-progress
          :progress="loadingProgress"
        />
      </div>
      <v-container fluid v-else>
        <v-row no-gutters>
          <v-col cols="12" md="6" lg="4" offset-lg="2">
            <VeGauge
              :data="titleCountChartData"
              :settings="titleCountChartSettings"
              height="200px"
            ></VeGauge>
          </v-col>
          <v-col cols="12" md="6" lg="4">
            <VeGauge
              :data="interestChartData"
              :settings="interestChartSettings"
              height="200px"
            ></VeGauge>
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col
            class="text-center small"
            cols="12"
            md="6"
            lg="4"
            offset-lg="2"
          >
            <v-tooltip bottom>
              <template #activator="{ on }">
                <span class="font-weight-black" v-on="on">{{
                  formatInteger(selectedTitleCount)
                }}</span>
              </template>
              {{ $t("selected_unique_title_count") }}
            </v-tooltip>
            /
            <v-tooltip bottom>
              <template #activator="{ on }">
                <span v-on="on">{{ formatInteger(totalTitleCount) }}</span>
              </template>
              {{ $t("total_unique_title_count") }}
            </v-tooltip>
          </v-col>
          <v-col class="text-center small" cols="12" md="6" lg="4">
            <v-tooltip bottom>
              <template #activator="{ on }">
                <span class="font-weight-black" v-on="on">{{
                  formatInteger(selectedInterest)
                }}</span>
              </template>
              {{ $t("selected_titles_interest") }}
            </v-tooltip>
            /
            <v-tooltip bottom>
              <template #activator="{ on }">
                <span v-on="on">{{ formatInteger(totalInterest) }}</span>
              </template>
              {{ $t("total_interest") }}
            </v-tooltip>
          </v-col>
        </v-row>
      </v-container>

      <v-data-table
        :headers="headers"
        :items="tableData"
        dense
        disable-pagination
        hide-default-footer
        show-select
        v-model="selectedPlatforms"
        item-key="pk"
        v-if="!(loading || preparingData)"
      >
        <template #item.titleCount="{ item }">
          {{ formatInteger(item.titleCount) }}
        </template>
        <template #item.titleInterest="{ item }">
          {{ formatInteger(item.titleInterest) }}
        </template>
        <template #item.uniqueInterest="{ item }">
          {{ formatInteger(item.uniqueInterest) }}
        </template>
        <template #item.uniqueTitleCount="{ item }">
          {{ formatInteger(item.uniqueTitleCount) }}
        </template>
      </v-data-table>
    </div>
  </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import axios from "axios";
import { formatInteger } from "@/libs/numbers";
import VeGauge from "v-charts/lib/gauge.common";
import { pubTypes } from "@/libs/pub-types";
import TitleTypeFilterWidget from "@/components/TitleTypeFilterWidget";
import LoaderWidget from "@/components/util/LoaderWidget";

export default {
  name: "CancelSimulationWidget",

  components: {
    LoaderWidget,
    TitleTypeFilterWidget,
    VeGauge,
  },

  data() {
    return {
      titleInterest: new Map(),
      platformTitles: new Map(),
      platformsList: [],
      platformsInterestSorted: [],
      selectedPlatforms: [],
      loadingPlatforms: null,
      loadingTitleInterest: null,
      loadingPlatformTitles: null,
      preparingData: null,
      selectedPubTypes: [...pubTypes.map((item) => item.code)],
      chartSettingsCommon: {
        dataType: {
          rate: "percent",
        },
        seriesMap: {
          rate: {
            radius: "98%",
            min: 0,
            max: 1,
            axisLine: {
              lineStyle: {
                color: [
                  [0.5, "#af5454"],
                  [0.8, "#4f7fad"],
                  [1, "#529e6d"],
                ],
              },
            },
            axisLabel: { show: false },
            title: {
              fontSize: 12,
              fontWeight: "bold",
            },
            detail: {
              fontSize: 20,
            },
          },
        },
      },
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
    }),
    titleInterestUrl() {
      if (this.selectedOrganizationId && this.pubTypesUrl) {
        return `/api/organization/${this.selectedOrganizationId}/title-interest-brief/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}&pub_type=${this.pubTypesUrl}`;
      }
      return null;
    },
    platformTitlesUrl() {
      if (this.selectedOrganizationId && this.pubTypesUrl) {
        return `/api/organization/${this.selectedOrganizationId}/platform/title-ids-list/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}&pub_type=${this.pubTypesUrl}`;
      }
      return null;
    },
    platformsUrl() {
      if (this.selectedOrganizationId) {
        return `/api/organization/${this.selectedOrganizationId}/platform/?used_only`;
      }
      return null;
    },
    platforms() {
      return this.platformsList;
    },
    totalInterest() {
      let result = 0;
      for (let value of this.titleInterest.values()) {
        result += value;
      }
      return result;
    },
    headers() {
      return [
        {
          text: this.$t("labels.platform"),
          value: "platform",
        },
        {
          text: this.$t("labels.title_count"),
          value: "titleCount",
          align: "right",
        },
        {
          text: this.$t("unique_title_count"),
          value: "uniqueTitleCount",
          align: "right",
        },
        {
          text: this.$t("title_interest"),
          value: "titleInterest",
          align: "right",
        },
        {
          text: this.$t("unique_title_interest"),
          value: "uniqueInterest",
          align: "right",
        },
      ];
    },
    tableData() {
      let out = [];
      for (let platform of this.platforms) {
        // unique titles calculation is used in two following methods, so we do it only once to save time
        const titles = this.platformUniqueTitles(platform);
        out.push({
          pk: platform.pk,
          platform: platform.short_name,
          titleCount: this.platformTitleCount(platform),
          titleInterest: this.platformTitleInterest(platform),
          uniqueTitleCount: this.platformUniqueTitleCount(platform, titles),
          uniqueInterest: this.platformUniqueInterest(platform, titles),
        });
      }
      return out;
    },
    selectedTitles() {
      const selectedPks = new Set(
        this.selectedPlatforms.map((item) => item.pk)
      );
      let selectedTitles = new Set();
      this.platformTitles.forEach((titles, pk) => {
        const pkint = parseInt(pk);
        if (selectedPks.has(pkint)) {
          titles.forEach((title) => selectedTitles.add(title));
        }
      });
      return selectedTitles;
    },
    selectedInterest() {
      let interest = 0;
      this.selectedTitles.forEach((pk) => {
        interest += this.titleInterest.get(pk) ?? 0;
      });
      let distinctInterests = new Map();
      this.platformsList.forEach((platform) =>
        distinctInterests.set(platform.pk, platform.distinctTitleInterest)
      );
      interest += this.selectedPlatforms
        .map((item) => distinctInterests.get(item.pk) ?? 0)
        .reduce((x, y) => x + y, 0);
      return interest;
    },
    selectedTitleCount() {
      let distinctCounts = new Map();
      this.platformsList.forEach((platform) =>
        distinctCounts.set(platform.pk, platform.distinctTitleCount)
      );
      return (
        this.selectedTitles.size +
        this.selectedPlatforms
          .map((item) => distinctCounts.get(item.pk) ?? 0)
          .reduce((x, y) => x + y, 0)
      );
    },
    totalTitleCount() {
      let allTitles = new Set();
      this.platformTitles.forEach((titles, pk) => {
        titles.forEach((title) => allTitles.add(title));
      });
      let count = allTitles.size;
      count += this.platformsList
        .map((platform) => platform.distinctTitleCount)
        .reduce((a, b) => a + b, 0);
      return count;
    },
    interestChartData() {
      return {
        columns: ["type", "value"],
        rows: [
          {
            type: "rate",
            value: this.selectedInterest / this.totalInterest,
          },
        ],
      };
    },
    titleCountChartData() {
      return {
        columns: ["type", "value"],
        rows: [
          {
            type: "rate",
            value: this.selectedTitleCount / this.totalTitleCount,
          },
        ],
      };
    },
    interestChartSettings() {
      return {
        ...this.chartSettingsCommon,
        dataName: {
          rate: this.$t("interest"),
        },
      };
    },
    titleCountChartSettings() {
      return {
        ...this.chartSettingsCommon,
        dataName: {
          rate: this.$t("labels.title_count_short"),
        },
      };
    },
    loading() {
      return (
        this.loadingPlatforms ||
        this.loadingPlatformTitles ||
        this.loadingTitleInterest
      );
    },
    loadingProgress() {
      let progress = 100;
      if (this.loadingPlatforms) {
        progress -= 10;
      }
      if (this.loadingTitleInterest) {
        progress -= 30;
      }
      if (this.loadingPlatformTitles) {
        progress -= 30;
      }
      if (this.preparingData) {
        progress -= 30;
      }
      return progress;
    },
    pubTypesUrl() {
      return this.selectedPubTypes.join(",");
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    formatInteger,
    async fetchTitleInterest() {
      if (!this.titleInterestUrl) {
        return;
      }
      this.loadingTitleInterest = true;
      this.titleInterest = new Map(); // zero-out the current data
      try {
        let result = await axios.get(this.titleInterestUrl);
        let map = new Map();
        for (let rec of result.data) {
          map.set(rec.target_id, rec.interest);
        }
        this.titleInterest = map;
        this.loadingTitleInterest = false;
        await this.prepareData();
      } catch (error) {
        this.showSnackbar({
          text: "Error loading title interest: " + error,
          color: "error",
        });
      } finally {
        this.loadingTitleInterest = false;
      }
    },
    async fetchPlatformTitles() {
      if (!this.platformTitlesUrl) {
        return;
      }
      this.loadingPlatformTitles = true;
      this.platformTitles = new Map(); // zero-out the current data
      try {
        let result = await axios.get(this.platformTitlesUrl);
        let map = new Map();
        for (let [platformId, titles] of Object.entries(result.data)) {
          map.set(parseInt(platformId), titles);
        }
        this.platformTitles = map;
        this.loadingPlatformTitles = false;
        await this.prepareData();
      } catch (error) {
        this.showSnackbar({
          text: "Error loading platform titles: " + error,
          color: "error",
        });
      } finally {
        this.loadingPlatformTitles = false;
      }
    },
    async fetchPlatforms() {
      if (!this.platformsUrl) {
        return;
      }
      this.loadingPlatforms = true;
      this.platformsList = []; // zero-out the current data
      try {
        let result = await axios.get(this.platformsUrl);
        this.platformsList = result.data;
        this.platformsList
          .sort((a, b) => a.name.localeCompare(b.name))
          .forEach((platform) => {
            this.$set(platform, "distinctTitleCount", 0);
            this.$set(platform, "distinctTitleInterest", 0);
          });
        this.selectedPlatforms = this.platformsList.map((item) => {
          return {
            pk: item.pk,
          };
        });
        this.loadingPlatform = false;
        await this.prepareData();
      } catch (error) {
        this.showSnackbar({
          text: "Error loading platforms: " + error,
          color: "error",
        });
      } finally {
        this.loadingPlatforms = false;
      }
    },
    async prepareData() {
      if (!this.loading) {
        // we only do the computation if we have all the necessary data
        console.log("start", new Date());
        this.preparingData = true;
        /*
            We only store the non-unique titles for each platform and for the unique ones we just store the
            title count and interest, because these values do not change during the computation and it saves
            us a lot of iteration not to store them
         */
        for (let platform of this.platformsList) {
          let uniqueTitles = this.platformUniqueTitles(platform, false);
          platform["distinctTitleCount"] =
            this.uniqueTitlesToCount(uniqueTitles);
          platform["distinctTitleInterest"] =
            this.uniqueTitlesToInterest(uniqueTitles);
          let uniqueTitleSet = new Set(uniqueTitles);
          let allTitles = this.platformTitles.get(platform.pk);
          if (allTitles) {
            this.platformTitles.set(
              platform.pk,
              allTitles.filter((item) => !uniqueTitleSet.has(item))
            );
          }
        }
        this.preparingData = false;
        console.log("end", new Date());
      }
    },
    platformTitleCount(platform) {
      let count = platform.distinctTitleCount;
      const titles = this.platformTitles.get(platform.pk);
      if (titles) {
        count += titles.length;
      }
      return count;
    },
    platformTitleInterest(platform) {
      let interest = platform.distinctTitleInterest;
      const titles = this.platformTitles.get(platform.pk);
      if (titles) {
        interest += titles
          .map((pk) => this.titleInterest.get(pk) ?? 0)
          .reduce((a, b) => a + b, 0);
      }
      return interest;
    },
    platformUniqueTitles(platform, selectedOnly = true) {
      // if selectedOnly is true, the calculation is performed only for selected platforms. This is what we want
      // during normal computation. But when preparing data after load, we need to use all platforms,
      // regardless if they are selected
      const selectedPks = new Set(
        this.selectedPlatforms.map((item) => item.pk)
      );
      if (selectedOnly === false || selectedPks.has(platform.pk)) {
        const myTitles = this.platformTitles.get(platform.pk);
        if (!myTitles) {
          return [];
        }
        let otherTitles = new Set();
        this.platformTitles.forEach((titles, pk) => {
          const pkint = parseInt(pk);
          if (
            pkint !== platform.pk &&
            (selectedOnly === false || selectedPks.has(pkint))
          ) {
            titles.forEach((title) => otherTitles.add(title));
          }
        });
        return myTitles.filter((item) => !otherTitles.has(item));
      }
      return null;
    },
    uniqueTitlesToCount(titles) {
      if (titles === null) {
        return null;
      }
      return titles.length;
    },
    uniqueTitlesToInterest(titles) {
      if (titles === null) {
        return null;
      }
      return titles
        .map((title) => this.titleInterest.get(title) ?? 0)
        .reduce((x, y) => x + y, 0);
    },
    platformUniqueTitleCount(platform, uniqueTitles) {
      if (uniqueTitles === null) {
        return null;
      }
      let count = platform.distinctTitleCount;
      count += this.uniqueTitlesToCount(uniqueTitles);
      return count;
    },
    platformUniqueInterest(platform, uniqueTitles) {
      if (uniqueTitles === null) {
        return null;
      }
      let interest = platform.distinctTitleInterest;
      interest += this.uniqueTitlesToInterest(uniqueTitles);
      return interest;
    },
  },

  mounted() {
    this.fetchTitleInterest();
    this.fetchPlatformTitles();
    this.fetchPlatforms();
  },

  watch: {
    platformsUrl() {
      this.fetchPlatforms();
    },
    titleInterestUrl() {
      this.fetchTitleInterest();
    },
    platformTitlesUrl() {
      this.fetchPlatformTitles();
    },
  },
};
</script>

<style scoped lang="scss"></style>
