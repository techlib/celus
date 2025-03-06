<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  tooltip_two_platforms_titles: "{absValue} ({relValue}) {titles} from {platformName1} {is_also_available} from {platformName2}"
  tooltip_two_platforms_interest: "{absValue} ({relValue}) of the interest in titles from <strong>{platformName1}</strong> could also be satisfied on <strong>{platformName2}</strong>"
  is_also_available: is also available | are also available
  titles: title | titles
  absolute_titles: Absolute number of titles
  relative_titles: Relative number of titles in %
  absolute_interest: Absolute interest
  relative_interest: Relative interest in %
  no_overlap_data: There are no overlapping platforms
  platform_titles: "Platform <strong>{platform}</strong> has {value} title | Platform <strong>{platform}</strong> has {value} titles"
  platform_interest: "Total interest on platform <strong>{platform}</strong> is {value}"

cs:
  tooltip_two_platforms_titles: "{absValue} ({relValue}) {titles} z {platformName1} {is_also_available} z {platformName2}"
  tooltip_two_platforms_interest: "{absValue} ({relValue}) zájmu o tituly z <strong>{platformName1}</strong> by mohlo být uspokojeno také na <strong>{platformName2}</strong>"
  is_also_available: "je také dostupný | jsou také dostupné | je také dostupných"
  titles: "titul | tituly | titulů"
  absolute_titles: Absolutní počet titulů
  relative_titles: Relativní počet titulů v %
  absolute_interest: Absolutní zájem
  relative_interest: Relativní zájem v %
  no_overlap_data: Žádné platformy nemají překryv
  platform_titles: "Platforma <strong>{platform}</strong> má {value} titul | Platforma <strong>{platform}</strong> má {value} tituly | Platforma <strong>{platform}</strong> má {value} titulů"
  platform_interest: "Celkový zájem o platformu <strong>{platform}</strong> je {value}"
</i18n>

<template>
  <LoaderWidget
    v-if="loading || platformsLoading"
    height="300"
    :text="$t('overlap_analysis.loading_data')"
  />
  <ErrorPlaceholder
    v-else-if="usedPlatforms.length === 0"
    :text="$t('no_overlap_data')"
    color="#33aa33"
    icon="fa fa-info-circle"
  ></ErrorPlaceholder>
  <div v-else class="overflow-auto">
    <table class="overlap">
      <thead>
        <tr>
          <th class="pt-8 bottom">
            <v-btn-toggle
              v-model="mode"
              mandatory="force"
              density="compact"
              variant="outlined"
              divided
            >
              <v-tooltip location="bottom">
                <template #activator="{ props }">
                  <v-btn value="titles" v-bind="props" size="small">
                    <v-icon size="x-small" :color="iconColor"
                      >fa fa-book</v-icon
                    >
                    123
                  </v-btn>
                </template>
                {{ $t("absolute_titles") }}
              </v-tooltip>
              <v-tooltip location="bottom">
                <template #activator="{ props }">
                  <v-btn value="rel-titles" v-bind="props" size="small">
                    <v-icon size="x-small" :color="iconColor"
                      >fa fa-book</v-icon
                    >
                    %
                  </v-btn>
                </template>
                {{ $t("relative_titles") }}
              </v-tooltip>
              <v-tooltip location="bottom">
                <template #activator="{ props }">
                  <v-btn value="interest" size="small" v-bind="props">
                    <v-icon size="x-small" :color="iconColor"
                      >fa fa-search</v-icon
                    >
                    123
                  </v-btn>
                </template>
                {{ $t("absolute_interest") }}
              </v-tooltip>
              <v-tooltip location="bottom">
                <template #activator="{ props }">
                  <v-btn size="small" v-bind="props" value="rel-interest">
                    <v-icon size="x-small" :color="iconColor"
                      >fa fa-search</v-icon
                    >
                    %</v-btn
                  >
                </template>
                {{ $t("relative_interest") }}
              </v-tooltip>
            </v-btn-toggle>
          </th>
          <th
            v-for="platform of usedPlatforms"
            :key="`plcol-${platform.pk}`"
            class="rotated"
          >
            <div>
              <span>{{ platform.short_name }}</span>
            </div>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading">
          <th>loading</th>
        </tr>
        <tr v-for="platform1 of usedPlatforms" :key="`plrow-${platform1.pk}`">
          <th>{{ platform1.short_name }}</th>
          <td
            v-for="platform2 of usedPlatforms"
            :key="`${platform1.pk}-${platform2.pk}`"
            :class="{ 'self-overlap': platform1.pk === platform2.pk }"
            :style="{ backgroundColor: overlapColor(platform1, platform2) }"
          >
            <v-tooltip
              location="bottom"
              v-if="
                !disableTooltips && overlapValue(platform1, platform2, false)
              "
            >
              <template #activator="{ props }">
                <span v-bind="props" class="full">
                  {{ overlapValue(platform1, platform2, relative) }}
                </span>
              </template>
              <span v-if="platform1.pk !== platform2.pk">
                <span
                  v-if="showInterest"
                  v-html="
                    $t('tooltip_two_platforms_interest', {
                      absValue: overlapValue(platform1, platform2, false),
                      relValue: overlapValue(platform1, platform2, true),
                      platformName1: platform1.short_name,
                      platformName2: platform2.short_name,
                    })
                  "
                ></span>
                <!-- tooltip about titles is more complicated as it requires pluralization -->
                <i18n-t
                  v-else
                  keypath="tooltip_two_platforms_titles"
                  tag="span"
                >
                  <template v-slot:absValue>
                    {{ overlapValue(platform1, platform2, false) }}
                  </template>
                  <template v-slot:relValue>{{
                    overlapValue(platform1, platform2, true)
                  }}</template>
                  <template v-slot:platformName1>
                    <strong>{{ platform1.short_name }}</strong>
                  </template>
                  <template v-slot:platformName2>
                    <strong>{{ platform2.short_name }}</strong>
                  </template>
                  <template v-slot:is_also_available>
                    {{
                      $tc(
                        "is_also_available",
                        overlapValue(platform1, platform2, false),
                      )
                    }}
                  </template>
                  <template v-slot:titles>
                    {{
                      $tc("titles", overlapValue(platform1, platform2, false))
                    }}
                  </template>
                </i18n-t>
              </span>
              <span
                v-else
                v-html="
                  $tc(
                    showInterest ? 'platform_interest' : 'platform_titles',
                    overlapValue(platform1, platform2, false),
                    {
                      platform: platform1.short_name,
                      value: overlapValue(platform1, platform2, false),
                    },
                  )
                "
              ></span>
            </v-tooltip>
            <span v-else>
              {{ overlapValue(platform1, platform2, relative) }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import axios from "axios";
import { mapActions, mapGetters, mapState } from "vuex";
import { smartFormatFloat } from "@/libs/numbers";
import LoaderWidget from "@/components/util/LoaderWidget";
import Color from "color";
import ErrorPlaceholder from "@/components/util/ErrorPlaceholder";

export default {
  name: "PlatformOverlapTable",

  components: { ErrorPlaceholder, LoaderWidget },

  data() {
    return {
      overlapData: [],
      overlapMap: new Map(),
      platforms: new Map(),
      loading: false,
      relative: false,
      showInterest: false,
      platformsLoading: false,
      iconColor: "#666666",
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
    mode: {
      get() {
        if (this.relative) {
          if (this.showInterest) {
            return "rel-interest";
          }
          return "rel-titles";
        }
        if (this.showInterest) {
          return "interest";
        }
        return "titles";
      },
      set(value) {
        switch (value) {
          case "rel-interest":
            this.relative = true;
            this.showInterest = true;
            break;
          case "rel-titles":
            this.relative = true;
            this.showInterest = false;
            break;
          case "interest":
            this.relative = false;
            this.showInterest = true;
            break;
          default:
            this.relative = false;
            this.showInterest = false;
        }
      },
    },
    overlapDataUrl() {
      if (this.selectedOrganizationId) {
        return `/api/organization/${this.selectedOrganizationId}/platform-overlap/?start=${this.dateStart}&end=${this.dateEnd}`;
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
      this.overlapData.forEach((item) => {
        if (item.platform1 !== item.platform2) {
          platformIds.add(item.platform1);
          platformIds.add(item.platform2);
        }
      });
      let usedPlatforms = [];
      platformIds.forEach((item) => {
        if (this.platforms.has(item)) {
          usedPlatforms.push(this.platforms.get(item));
        }
      });
      return usedPlatforms.sort((a, b) =>
        a.short_name.localeCompare(b.short_name),
      );
    },
    disableTooltips() {
      return this.overlapMap.size > 500;
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
        overlapMap.set(`${item.platform1}-${item.platform2}`, {
          overlap: item.overlap,
          interest: item.interest,
        });
      });
      this.overlapMap = overlapMap;
    },
    overlapValue(platform1, platform2, relative) {
      const key = this.showInterest ? "interest" : "overlap";
      let overlapAbs = this.overlapMap.get(`${platform1.pk}-${platform2.pk}`);
      if (overlapAbs == null) {
        return "";
      }
      if (relative) {
        const platformAbs = this.overlapMap.get(
          `${platform1.pk}-${platform1.pk}`,
        );
        return (
          smartFormatFloat((100 * overlapAbs[key]) / platformAbs[key], 1) + "%"
        );
      }
      return overlapAbs[key];
    },
    overlapColor(platform1, platform2) {
      const key = this.showInterest ? "interest" : "overlap";
      if (platform1.pk === platform2.pk) {
        return "#dddddd";
      }
      let overlapAbs = this.overlapMap.get(`${platform1.pk}-${platform2.pk}`);
      if (overlapAbs == null) {
        return "#ffffff";
      }
      const platformAbs = this.overlapMap.get(
        `${platform1.pk}-${platform1.pk}`,
      );
      const ratio = overlapAbs[key] / platformAbs[key];
      return Color("#00bb66").alpha(Math.sqrt(ratio)).rgb().string();
    },
  },

  mounted() {
    this.fetchOverlapData();
    this.fetchPlatformList();
  },

  watch: {
    overlapDataUrl() {
      this.fetchOverlapData();
    },
    platformListUrl() {
      this.fetchPlatformList();
    },
    disableTooltips() {
      this.$emit("disableTooltips", this.disableTooltips);
    },
  },
};
</script>

<style scoped lang="scss">
table.overlap {
  border-collapse: collapse;

  th {
    font-size: 13px;
    text-align: right;
    padding-right: 0.5rem;

    &.rotated {
      white-space: nowrap;
      height: 120px;

      div {
        transform: translate(16px, 40px) rotate(-45deg);
        width: 30px;
      }
    }
  }

  td {
    border: solid 1px #ccc;
    text-align: right;
    padding: 3px;
    min-width: 3rem;
    font-weight: bold;
    font-size: 13px;

    &.self-overlap {
      color: #777777;
      background-color: #eeeeee;
    }
  }

  span.full {
    display: inline-block;
    width: 100%;
  }
}
</style>
