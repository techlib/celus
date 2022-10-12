<i18n lang="yaml">
en:
  loading_data: "Please wait while Celus is crunching the data for you. It has to go over all the titles and that takes some time."
  tooltip_two_platforms: "{absValue} ({relValue}) {titles} from {platformName1} {is_also_available} from {platformName2}"
  is_also_available: is also available | are also available
  titles: title | titles
  absolute_numbers: Absolute numbers
  relative_numbers: Relative numbers in %
  no_overlap_data: There are no overlapping platforms

cs:
  loading_data: "Prosíme o chvilku strpení, než Celus přechroupe data. Musí zpracovat záznamy o všech titulech a to nějakou dobu zabere."
  tooltip_two_platforms: "{absValue} ({relValue}) {titles} z {platformName1} {is_also_available} z {platformName2}"
  is_also_available: "je také dostupný | jsou také dostupné | je také dostupných"
  titles: "titul | tituly | titulů"
  absolute_numbers: Absolutní čísla
  relative_numbers: Relativní vyjádření v %
  no_overlap_data: Žádné platformy nemají překryv
</i18n>

<template>
  <LoaderWidget
    v-if="loading || platformsLoading"
    height="300"
    :text="$t('loading_data')"
    icon-name="fa-cog"
  />
  <ErrorPlaceholder
    v-else-if="usedPlatforms.length === 0"
    :text="$t('no_overlap_data')"
    color="#33aa33"
    icon="fa fa-info-circle"
  />
  <div v-else class="overflow-auto">
    <table class="overlap">
      <thead>
        <tr>
          <th class="pt-8 bottom">
            <v-btn-toggle v-model="relative" mandatory dense>
              <v-tooltip bottom>
                <template #activator="{ on }">
                  <v-btn :value="false" small v-on="on">123</v-btn>
                </template>
                {{ $t("absolute_numbers") }}
              </v-tooltip>
              <v-tooltip bottom>
                <template #activator="{ on }">
                  <v-btn :value="true" small v-on="on">%</v-btn>
                </template>
                {{ $t("relative_numbers") }}
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
            <v-tooltip bottom v-if="!disableTooltips">
              <template #activator="{ on }">
                <span v-on="on" class="full">
                  {{ overlapValue(platform1, platform2, relative) }}
                </span>
              </template>
              <span v-if="platform1.pk !== platform2.pk">
                <i18n path="tooltip_two_platforms" tag="span">
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
                        overlapValue(platform1, platform2, false)
                      )
                    }}
                  </template>
                  <template v-slot:titles>
                    {{
                      $tc("titles", overlapValue(platform1, platform2, false))
                    }}
                  </template>
                </i18n>
              </span>
              <span v-else>
                <strong>{{ platform1.short_name }}</strong> has
                {{ overlapValue(platform1, platform2, false) }} titles
              </span>
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
        a.short_name.localeCompare(b.short_name)
      );
    },
    disableTooltips() {
      return this.usedPlatforms.length >= 30;
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
        overlapMap.set(`${item.platform1}-${item.platform2}`, item.overlap);
        if (item.platform1 !== item.platform2) {
          // reverse mapping
          overlapMap.set(`${item.platform2}-${item.platform1}`, item.overlap);
        }
      });
      this.overlapMap = overlapMap;
    },
    overlapValue(platform1, platform2, relative = false) {
      let overlapAbs = this.overlapMap.get(`${platform1.pk}-${platform2.pk}`);
      if (overlapAbs == null) {
        return "";
      }
      if (relative) {
        const platformAbs = this.overlapMap.get(
          `${platform1.pk}-${platform1.pk}`
        );
        return smartFormatFloat((100 * overlapAbs) / platformAbs, 1) + "%";
      }
      return overlapAbs;
    },
    overlapColor(platform1, platform2) {
      if (platform1.pk === platform2.pk) {
        return "#dddddd";
      }
      let overlapAbs = this.overlapMap.get(`${platform1.pk}-${platform2.pk}`);
      if (overlapAbs == null) {
        return "#ffffff";
      }
      const platformAbs = this.overlapMap.get(
        `${platform1.pk}-${platform1.pk}`
      );
      const ratio = overlapAbs / platformAbs;
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
    font-size: 81.25%;
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
    font-size: 81.25%;

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
