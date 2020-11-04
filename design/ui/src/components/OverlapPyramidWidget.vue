<i18n lang="yaml">
en:
  preparing_data: Preparing data. Please wait, it may take a while.
  new_interest: Added interest
  new_titles: Added titles
  new_interest_perc: Added interest %
  cum_interest: Cumulative interest
  new_interest_tt: Interest in titles that this platform adds over the platforms in previous rows
  new_interest_value_tt: "{platform} adds {value} interest to that of previous rows"
  new_interest_value_tt_first: "{platform} adds the most interest ({value}) from all the platforms and therefore it is first"
  new_titles_tt: Unique titles that this platform adds over the platforms in previous rows
  new_interest_perc_tt: Interest added by unique titles on this platform as percentage of the total interest
  cum_interest_tt: Total interest covered by this a previous platforms as percentage of the total interest

cs:
  preparing_data: Připravuji data. Vydržte prosím, může to chvíli trvat.
  new_interest: Přidaný zájem
  new_titles: Přidané tituly
  new_interest_perc: Přidaný zájem %
  cum_interest: Kumulativní zájem
  new_interest_tooltip: Zájem o tituly, která tato platforma přidává oproti platformám na předchozích rádcích
  new_interest_value_tt: "{platform} přidává {value} k zájmu z předchozích řádků"
  new_interest_value_tt_first: "{platform} přidává největší zájem ze všech ({value}) a je proto první"
  new_titles_tt: Unikátní tituly které tato platforma přidává oproti platformám na předchozích řádcích
  new_interest_perc_tt: Zájem přidaný unikátními tituly na této platformě vyjádřený v procentech z celkového zájmu
  cum_interest_tt: Celkový zájem pokrytý touto a předchozími platformami jako procento z celkového zájmu
</i18n>

<template>
  <div>
    <TitleTypeFilterWidget class="mb-6" v-model="selectedPubTypes" />

    <LoaderWidget
      v-if="loading || preparingData"
      :text="$t('preparing_data')"
      show-progress
      :progress="loadingProgress"
    />

    <div v-else>
      <div class="pb-3">
        <span class="font-weight-bold">Total interest</span>:
        {{ formatInteger(this.totalInterest) }}
      </div>

      <table v-if="pyramid" class="pyramid">
        <thead>
          <tr>
            <th></th>
            <th>
              <v-tooltip bottom>
                <template #activator="{ on }">
                  <span v-on="on">{{ $t("new_interest") }}</span>
                </template>
                {{ $t("new_interest_tt") }}
              </v-tooltip>
            </th>
            <th>
              <v-tooltip bottom>
                <template #activator="{ on }">
                  <span v-on="on">{{ $t("new_titles") }}</span>
                </template>
                {{ $t("new_titles_tt") }}
              </v-tooltip>
            </th>
            <th>
              <v-tooltip bottom>
                <template #activator="{ on }">
                  <span v-on="on">{{ $t("new_interest_perc") }}</span>
                </template>
                {{ $t("new_interest_perc_tt") }}
              </v-tooltip>
            </th>

            <th>
              <v-tooltip bottom>
                <template #activator="{ on }">
                  <span v-on="on">{{ $t("cum_interest") }}</span>
                </template>
                {{ $t("cum_interest_tt") }}
              </v-tooltip>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(level, index) in pyramid" :key="level.platform.pk">
            <th>{{ level.platform.short_name }}</th>
            <td class="text-right">
              <v-tooltip bottom max-width="360px">
                <template #activator="{ on }">
                  <span v-on="on">{{ formatInteger(level.score) }}</span>
                </template>
                <i18n
                  :path="
                    index === 0
                      ? 'new_interest_value_tt_first'
                      : 'new_interest_value_tt'
                  "
                  tag="span"
                >
                  <template #platform>
                    {{ level.platform.short_name }}
                  </template>
                  <template #value>
                    {{ formatInteger(level.score) }}
                  </template>
                </i18n>
              </v-tooltip>
            </td>
            <td class="text-right">{{ formatInteger(level.newTitles) }}</td>
            <td class="text-right">{{ level.relativeScoreStr }}</td>
            <td class="borderless pl-2" style="min-width: 100px">
              <v-progress-linear
                color="orange darken-1"
                height="16"
                :buffer-value="100 * level.relativeScoreCum"
                :value="100 * (level.relativeScoreCum - level.relativeScore)"
                dark
              >
                <span class="small contrast">
                  {{ level.relativeScoreCumStr }}
                </span>
              </v-progress-linear>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import axios from "axios";
import { formatFloat, formatInteger } from "@/libs/numbers";
import TitleTypeFilterWidget from "@/components/TitleTypeFilterWidget";
import { pubTypes } from "@/libs/pub-types";
import LoaderWidget from "@/components/util/LoaderWidget";

export default {
  name: "OverlapPyramidWidget",
  components: { LoaderWidget, TitleTypeFilterWidget },
  data() {
    return {
      titleInterest: new Map(),
      platformTitles: new Map(),
      platformsList: [],
      platformsInterestSorted: [],
      pyramid: [],
      selectedPubTypes: [...pubTypes.map((item) => item.code)],
      loadingPlatforms: false,
      loadingPlatformTitles: false,
      loadingTitleInterest: false,
      preparingData: false,
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
      if (this.selectedOrganizationId) {
        return `/api/organization/${this.selectedOrganizationId}/title-interest-brief/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}&pub_type=${this.pubTypesUrl}`;
      }
      return null;
    },
    platformTitlesUrl() {
      if (this.selectedOrganizationId) {
        return `/api/organization/${this.selectedOrganizationId}/platform/title-ids-list/?start=${this.dateRangeStart}&end=${this.dateRangeEnd}&pub_type=${this.pubTypesUrl}`;
      }
      return null;
    },
    platformsUrl() {
      if (this.selectedOrganizationId) {
        return `/api/organization/${this.selectedOrganizationId}/platform/`;
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
    pubTypesUrl() {
      return this.selectedPubTypes.join(",");
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
      try {
        let result = await axios.get(this.titleInterestUrl);
        let map = new Map();
        for (let rec of result.data) {
          map.set(rec.target_id, rec.interest);
        }
        this.titleInterest = map;
      } catch (error) {
        this.showSnackbar({
          text: "Error loading title interest: " + error,
          color: "error",
        });
      } finally {
        this.loadingTitleInterest = false;
      }
      this.constructPyramid();
    },
    async fetchPlatformTitles() {
      if (!this.platformTitlesUrl) {
        return;
      }
      this.loadingPlatformTitles = true;
      try {
        let result = await axios.get(this.platformTitlesUrl);
        let map = new Map();
        for (let [platformId, titles] of Object.entries(result.data)) {
          map.set(platformId, titles);
        }
        this.platformTitles = map;
      } catch (error) {
        this.showSnackbar({
          text: "Error loading platform titles: " + error,
          color: "error",
        });
      } finally {
        this.loadingPlatformTitles = false;
      }
      this.constructPyramid();
    },
    async fetchPlatforms() {
      if (!this.platformsUrl) {
        return;
      }
      this.loadingPlatforms = true;
      try {
        let result = await axios.get(this.platformsUrl);
        this.platformsList = result.data;
        this.platformsList.sort((a, b) =>
          a.short_name.localeCompare(b.short_name)
        );
      } catch (error) {
        this.showSnackbar({
          text: "Error loading platforms: " + error,
          color: "error",
        });
      } finally {
        this.loadingPlatforms = false;
      }
      this.constructPyramid();
    },
    platformTitleCount(platformId) {
      const titles = this.platformTitles.get(platformId.toString());
      if (titles) {
        return titles.length;
      }
      return 0;
    },
    platformTitleInterest(platformId) {
      const titles = this.platformTitles.get(platformId.toString());
      if (titles) {
        return titles
          .map((pk) => this.titleInterest.get(pk) ?? 0)
          .reduce((a, b) => a + b);
      }
      return 0;
    },
    constructPyramid() {
      if (
        this.titleInterest.size > 0 &&
        this.platformsList.length > 0 &&
        this.platformTitles.size > 0
      ) {
        this.preparingData = true;
        let platformsToProcess = [...this.platformsList];
        let seenTitles = new Set();
        let pyramid = [];
        let scoreCum = 0;
        while (platformsToProcess.length > 0) {
          let bestPlatform = null;
          let bestValue = -1;
          let bestIndex = 0;
          let i = 0;
          for (let platform of platformsToProcess) {
            const titles = this.platformTitles.get(platform.pk.toString());
            let platformInterest = 0;
            if (titles) {
              platformInterest = titles
                .filter((pk) => !seenTitles.has(pk))
                .map((pk) => this.titleInterest.get(pk) ?? 0)
                .reduce((a, b) => a + b, 0);
            }
            if (platformInterest > bestValue) {
              bestPlatform = platform;
              bestValue = platformInterest;
              bestIndex = i;
            }
            i++;
          }
          scoreCum += bestValue;
          let rec = {
            platform: bestPlatform,
            score: bestValue,
            relativeScore: bestValue / this.totalInterest,
            relativeScoreStr:
              formatFloat((100 * bestValue) / this.totalInterest, 2) + " %",
            scoreCum: scoreCum,
            relativeScoreCum: scoreCum / this.totalInterest,
            relativeScoreCumStr:
              formatFloat((100 * scoreCum) / this.totalInterest, 2) + " %",
          };
          platformsToProcess.splice(bestIndex, 1);
          const titles = this.platformTitles.get(bestPlatform.pk.toString());
          if (titles) {
            rec.newTitles = titles.filter((pk) => !seenTitles.has(pk)).length;
            titles.forEach((pk) => seenTitles.add(pk));
          }
          pyramid.push(rec);
        }
        this.pyramid = pyramid;
        this.preparingData = false;
      } else {
        this.pyramid = [];
      }
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

<style scoped lang="scss">
.pyramid {
  border-collapse: collapse;

  thead {
    th {
      padding: 0 1rem;
      font-size: 81.25%;
    }
  }

  tbody {
    th {
      text-align: right;
      padding-right: 0.5rem;
      font-size: 81.25%;
    }
  }

  td {
    border: solid 1px #999999;
    margin-left: 1rem;
    font-size: 81.25%;
    padding: 3px;

    &.borderless {
      border: none;
    }
  }

  .small {
    font-size: 81.25%;
  }

  .contrast {
    color: #0d5733;
  }
}
</style>
