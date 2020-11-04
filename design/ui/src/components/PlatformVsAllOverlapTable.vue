<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  loading_data: "Please wait while Celus is crunching the data for you. It has to go over all the titles and that takes some time."
  hide_zero: Hide platforms with no overlap
  tooltip_titles_relative: "{value} of titles from {platformName} are also available from other platforms."
  tooltip_titles_absolute: "{value} titles from {platformName} are also available from other platforms."
  tooltip_title_count: There are {value} titles in total on {platformName}.
  tooltip_total_interest: Total interest in titles from {platformName} is {value}.
  tooltip_interest_relative: "Titles also available from other platforms generate {value} of interest on {platformName}."
  tooltip_interest_absolute: "Interest in titles on {platformName} which are also available from other platforms is {value}."

cs:
  loading_data: "Prosíme o chvilku strpení, než Celus přechroupe data. Musí zpracovat záznamy o všech titulech a to nějakou dobu zabere."
  hide_zero: Skrýt platformy bez překryvu
  tooltip_titles_relative: "{value} titulů z {platformName} je také dostupných z jiných platforem."
  tooltip_titles_absolute: "{value} titulů z {platformName} je také dostupných z jiných platforem."
  tooltip_title_count: Celkový počet titulů na platformě {platformName} je {value}.
  tooltip_total_interest: Celkový zájem o tituly na platformě {platformName} je {value}.
  tooltip_interest_relative: "Tituly dostupné i z jiných platforem vytvářejí {value} zájmu o platformu {platformName}."
  tooltip_interest_absolute: "Zájem o tituly na platformě {platformName}, které jsou dostupné i na jiných platformách, je {value}."
</i18n>

<template>
  <div>
    <div>
      <v-switch v-model="hideZero" :label="$t('hide_zero')" />
    </div>
    <LoaderWidget
      v-if="loading || titleCountLoading || platformsLoading"
      height="300"
      :text="$t('loading_data')"
      icon-name="fa-cog"
    />
    <table v-else class="overlap">
      <thead>
        <tr>
          <th></th>
          <th colspan="3" class="text-center font-weight-bold">Title count</th>
          <th></th>
          <th colspan="3" class="text-center font-weight-bold">Interest</th>
        </tr>
        <tr>
          <th></th>
          <th v-text="$t('labels.overlap')"></th>
          <th v-text="$t('labels.total')"></th>
          <th v-text="$t('labels.relative')"></th>
          <th></th>
          <th v-text="$t('labels.overlap')"></th>
          <th v-text="$t('labels.total')"></th>
          <th v-text="$t('labels.relative')"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading || titleCountLoading">
          <th>loading</th>
        </tr>
        <tr v-for="platform of usedPlatforms" :key="`plrow-${platform.pk}`">
          <th>{{ platform.short_name }}</th>

          <td class="font-weight-bold">
            <v-tooltip bottom>
              <template #activator="{ on }">
                <span v-on="on" class="full">
                  {{ overlapValue(platform, false) }}
                </span>
              </template>
              <i18n path="tooltip_titles_absolute" tag="span">
                <template v-slot:value>
                  <strong>
                    {{ overlapValue(platform, false) }}
                  </strong>
                </template>
                <template v-slot:platformName>
                  <strong>{{ platform.short_name }}</strong>
                </template>
              </i18n>
            </v-tooltip>
          </td>

          <td>
            <v-tooltip bottom>
              <template #activator="{ on }">
                <span v-on="on" class="full">
                  {{ titleCountValue(platform) }}
                </span>
              </template>
              <i18n path="tooltip_title_count" tag="span">
                <template v-slot:value>
                  <strong>
                    {{ titleCountValue(platform) }}
                  </strong>
                </template>
                <template v-slot:platformName>
                  <strong>{{ platform.short_name }}</strong>
                </template>
              </i18n>
            </v-tooltip>
          </td>

          <td
            :style="{ backgroundColor: overlapColor(platform) }"
            class="font-weight-bold font-italic"
          >
            <v-tooltip bottom>
              <template #activator="{ on }">
                <span v-on="on" class="full">
                  {{ overlapValue(platform, true) }}
                </span>
              </template>
              <i18n path="tooltip_titles_relative" tag="span">
                <template v-slot:value>
                  <strong>
                    {{ overlapValue(platform, true) }}
                  </strong>
                </template>
                <template v-slot:platformName>
                  <strong>{{ platform.short_name }}</strong>
                </template>
              </i18n>
            </v-tooltip>
          </td>

          <td class="spacer"></td>

          <td class="font-weight-bold">
            <v-tooltip bottom>
              <template #activator="{ on }">
                <span v-on="on" class="full">
                  {{ overlapInterestValue(platform, false) }}
                </span>
              </template>
              <i18n path="tooltip_interest_absolute" tag="span">
                <template v-slot:value>
                  <strong>
                    {{ overlapInterestValue(platform, false) }}
                  </strong>
                </template>
                <template v-slot:platformName>
                  <strong>{{ platform.short_name }}</strong>
                </template>
              </i18n>
            </v-tooltip>
          </td>

          <td>
            <v-tooltip bottom>
              <template #activator="{ on }">
                <span v-on="on" class="full">
                  {{ totalInterestValue(platform) }}
                </span>
              </template>
              <i18n path="tooltip_total_interest" tag="span">
                <template v-slot:value>
                  <strong>
                    {{ totalInterestValue(platform) }}
                  </strong>
                </template>
                <template v-slot:platformName>
                  <strong>{{ platform.short_name }}</strong>
                </template>
              </i18n>
            </v-tooltip>
          </td>

          <td
            :style="{ backgroundColor: overlapInterestColor(platform) }"
            class="font-weight-bold font-italic"
          >
            <v-tooltip bottom>
              <template #activator="{ on }">
                <span v-on="on" class="full">
                  {{ overlapInterestValue(platform, true) }}
                </span>
              </template>
              <i18n path="tooltip_interest_relative" tag="span">
                <template v-slot:value>
                  <strong>{{ overlapInterestValue(platform, true) }}</strong>
                </template>
                <template v-slot:platformName>
                  <strong>{{ platform.short_name }}</strong>
                </template>
              </i18n>
            </v-tooltip>
          </td>
          <!--th class="text-left pl-2">{{ platform.short_name }}</th-->
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import axios from "axios";
import { mapActions, mapGetters, mapState } from "vuex";
import { smartFormatFloat, formatInteger } from "@/libs/numbers";
import LoaderWidget from "@/components/util/LoaderWidget";
import Color from "color";

export default {
  name: "PlatformVsAllOverlapTable",

  components: { LoaderWidget },

  data() {
    return {
      overlapData: [],
      overlapMap: new Map(),
      platforms: new Map(),
      titleCountMap: new Map(),
      loading: false,
      titleCountLoading: false,
      relative: false,
      hideZero: false,
      platformsLoading: false,
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      dateStart: "dateRangeStartText",
      dateEnd: "dateRangeEndText",
    }),
    overlapDataUrl() {
      if (this.selectedOrganizationId) {
        return `/api/organization/${this.selectedOrganizationId}/all-platforms-overlap/?start=${this.dateStart}&end=${this.dateEnd}`;
      }
      return null;
    },
    titleCountUrl() {
      if (this.selectedOrganizationId) {
        return `/api/organization/${this.selectedOrganizationId}/platform/title-count/?start=${this.dateStart}&end=${this.dateEnd}`;
      }
      return null;
    },
    platformListUrl() {
      if (this.selectedOrganizationId) {
        return `/api/organization/${this.selectedOrganizationId}/platform/`;
      }
      return null;
    },
    usedPlatforms() {
      let platformIds = new Set();
      this.overlapData
        .filter((item) => !this.hideZero || item.overlap > 0)
        .forEach((item) => {
          platformIds.add(item.platform);
        });
      let usedPlatforms = [];
      platformIds.forEach((item) =>
        usedPlatforms.push(this.platforms.get(item))
      );
      return usedPlatforms.sort((a, b) =>
        a.short_name.localeCompare(b.short_name)
      );
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async fetchOverlapData() {
      if (!this.overlapDataUrl) {
        return;
      }
      this.loading = true;
      try {
        let result = await axios.get(this.overlapDataUrl);
        this.prepareData(result);
      } catch (error) {
        this.showSnackbar({
          content: "Error getting overlap analysis data " + error,
          color: "error",
        });
      } finally {
        this.loading = false;
      }
    },
    async fetchTitleCountData() {
      if (!this.titleCountUrl) {
        return;
      }
      this.titleCountLoading = true;
      try {
        let result = await axios.get(this.titleCountUrl);
        this.prepareTitleData(result);
      } catch (error) {
        this.showSnackbar({
          content: "Error getting overlap analysis data " + error,
          color: "error",
        });
      } finally {
        this.titleCountLoading = false;
      }
    },
    async fetchPlatformList() {
      if (!this.platformListUrl) {
        return;
      }
      this.platformsLoading = true;
      try {
        let result = await axios.get(this.platformListUrl);
        let platforms = new Map();
        result.data.forEach((item) => platforms.set(item.pk, item));
        this.platforms = platforms;
      } catch (error) {
        this.showSnackbar({
          content: "Error getting platform list " + error,
          color: "error",
        });
      } finally {
        this.platformsLoading = false;
      }
    },
    prepareData(response) {
      this.overlapData = response.data;
      // overlap map
      let overlapMap = new Map();
      this.overlapData.forEach((item) => {
        overlapMap.set(`${item.platform}`, item);
      });
      this.overlapMap = overlapMap;
    },
    prepareTitleData(response) {
      let titleCountMap = new Map();
      response.data.forEach((item) => {
        titleCountMap.set(`${item.platform}`, item.title_count);
      });
      this.titleCountMap = titleCountMap;
    },
    overlapValue(platform, relative = false) {
      let overlapAbs = this.overlapMap.get(`${platform.pk}`);
      if (overlapAbs == null) {
        return "";
      }
      overlapAbs = overlapAbs.overlap;
      if (relative) {
        const platformAbs = this.titleCountMap.get(`${platform.pk}`);
        return smartFormatFloat((100 * overlapAbs) / platformAbs, 1) + "%";
      }
      return formatInteger(overlapAbs);
    },
    overlapInterestValue(platform, relative = false) {
      let overlapAbs = this.overlapMap.get(`${platform.pk}`);
      if (overlapAbs == null) {
        return "";
      }
      if (relative) {
        if (!overlapAbs.total_interest) {
          return "-";
        }
        return (
          smartFormatFloat(
            (100 * overlapAbs.overlap_interest) / overlapAbs.total_interest,
            1
          ) + "%"
        );
      }
      return formatInteger(overlapAbs.overlap_interest, "0");
    },
    totalInterestValue(platform) {
      let overlapAbs = this.overlapMap.get(`${platform.pk}`);
      if (overlapAbs == null) {
        return "";
      }
      return formatInteger(overlapAbs.total_interest, "0");
    },
    titleCountValue(platform) {
      let value = this.titleCountMap.get(`${platform.pk}`);
      if (value == null) {
        return "";
      }
      return formatInteger(value);
    },
    overlapColor(platform) {
      let overlapAbs = this.overlapMap.get(`${platform.pk}`);
      if (overlapAbs == null) {
        return "#ffffff";
      }
      const platformAbs = this.titleCountMap.get(`${platform.pk}`);
      const ratio = overlapAbs.overlap / platformAbs;
      return Color("#00bb66").alpha(Math.sqrt(ratio)).rgb().string();
    },
    overlapInterestColor(platform) {
      let overlapAbs = this.overlapMap.get(`${platform.pk}`);
      if (overlapAbs == null || !overlapAbs.total_interest) {
        return "#ffffff";
      }
      const ratio = overlapAbs.overlap_interest / overlapAbs.total_interest;
      return Color("#00bb66").alpha(Math.sqrt(ratio)).rgb().string();
    },
  },

  mounted() {
    this.fetchOverlapData();
    this.fetchTitleCountData();
    this.fetchPlatformList();
  },

  watch: {
    overlapDataUrl() {
      this.fetchOverlapData();
    },
    platformListUrl() {
      this.fetchPlatformList();
    },
    titleCountUrl() {
      this.fetchTitleCountData();
    },
  },
};
</script>

<style scoped lang="scss">
table.overlap {
  border-collapse: collapse;

  th {
    font-size: 81.25%;
    text-align: right;
    padding-right: 0.5rem;
  }

  thead th {
    text-align: center;
    font-weight: 300;
  }

  td {
    border: solid 1px #ccc;
    text-align: right;
    padding: 3px;
    min-width: 5rem;
    font-size: 81.25%;

    &.spacer {
      border-top: none;
      border-bottom: none;
      width: 1rem;
      max-width: 1rem;
      min-width: 1rem;
    }
  }

  span.full {
    display: inline-block;
    width: 100%;
  }
}
</style>
