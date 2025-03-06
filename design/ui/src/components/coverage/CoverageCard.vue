<i18n lang="yaml">
en:
  number_of_platforms: Number of platforms using this report in the selected period.
  number_of_organizations: Number of organizations using this report in the selected period.
  date_range: Date range

cs:
  number_of_platforms: Počet platforem používajících tento report ve zvoleném období.
  number_of_organizations: Počet organizací používajících tento report ve zvoleném období.
  date_range: Rozmezí dat
</i18n>

<template>
  <v-card
    class="pt-4 d-flex flex-column justify-space-between"
    :class="selected ? 'selected' : ''"
    :elevation="el"
    @[clickHandler]="$emit('click', { reportType })"
  >
    <div
      v-if="selected"
      style="position: absolute; top: 4px; right: 4px; z-index: 1"
    >
      <v-icon color="grey lighten-1"
        >fa fa-sync-alt {{ refreshingComputed ? "fa-spin" : "" }}</v-icon
      >
    </div>
    <v-tooltip location="top">
      <template #activator="{ props }">
        <CoverageScoreGauge
          :loading="!data || refreshingComputed"
          :model-value="data ? data.ratio : null"
          v-bind="props"
        ></CoverageScoreGauge>
      </template>
      <span v-if="selectedDateRange"
        >{{ $t("date_range") }}: {{ selectedDateRange.start }} -
        {{ selectedDateRange.end }}</span
      >
    </v-tooltip>
    <v-card-text class="text-center">
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <div class="font-weight-bold" v-bind="props">
            <span v-if="label">{{ label }}</span>
            <span v-else-if="reportType">
              <span class="font-weight-light"
                >{{
                  reportType.counter_version
                    ? "C" + counterVersionToStr(reportType.counter_version)
                    : "non-COUNTER"
                }}
                /</span
              >
              {{ reportType.counter_code || reportType.short_name }}
            </span>
          </div>
        </template>
        <span>{{ tooltip ? tooltip : reportType.name }}</span>
      </v-tooltip>
    </v-card-text>
    <div
      class="font-weight-light text-caption d-flex justify-space-between"
      v-if="data"
    >
      <v-tooltip location="bottom" v-if="showPlatformCount">
        <template #activator="{ props }">
          <div class="mx-1" v-bind="props">
            <v-icon size="x-small" class="pb-1">fa fa-list-alt</v-icon>
            {{ data.platform_count }}
          </div>
        </template>
        <span>{{ $t("number_of_platforms") }}</span>
      </v-tooltip>
      <v-tooltip location="bottom" v-if="showOrganizationCount">
        <template #activator="{ props }">
          <div class="mx-1" v-bind="props">
            <v-icon size="x-small" class="pb-1">fa fa-university</v-icon>
            {{ data.org_count }}
          </div>
        </template>
        <span>{{ $t("number_of_organizations") }}</span>
      </v-tooltip>
    </div>
  </v-card>
</template>

<script>
import { defineComponent } from "vue";
import CoverageScoreGauge from "@/components/charts/CoverageScoreGauge.vue";
import cancellation from "@/mixins/cancellation";
import { counterVersionToStr } from "@/libs/sushi";

export default defineComponent({
  name: "CoverageCard",

  mixins: [cancellation],

  components: { CoverageScoreGauge },

  props: {
    reportType: {
      type: Object,
      required: false,
    },
    organizationIds: {
      type: Array,
      required: false,
      default: () => [],
    },
    platformIds: {
      type: Array,
      required: false,
      default: () => [],
    },
    startDate: {
      type: String,
      required: false,
    },
    endDate: {
      type: String,
      required: false,
    },
    selectedDateRange: {
      type: Object,
      default: null,
    },
    selected: {
      type: Boolean,
      default: false,
    },
    coverageData: {
      type: Object,
      required: false,
      default: null,
    },
    refreshing: {
      type: Boolean,
      default: false,
    },
    showOrganizationCount: {
      type: Boolean,
      default: false,
    },
    showPlatformCount: {
      type: Boolean,
      default: false,
    },
    standalone: {
      type: Boolean,
      default: false,
    },
    clickable: {
      type: Boolean,
      default: true,
    },
    label: {
      type: String,
      default: null,
    },
    tooltip: {
      type: String,
      default: null,
    },
    elevation: {
      type: Number,
      default: null,
    },
  },

  emits: ["click"],

  data() {
    return {
      data: this.coverageData ? { ...this.coverageData } : {},
      refreshingInternal: false,
    };
  },

  computed: {
    refreshingComputed() {
      return this.refreshing || this.refreshingInternal;
    },
    el() {
      const base = this.$attrs.elevation ?? 2;
      return this.selected ? base + 6 : base;
    },
    clickHandler() {
      return this.clickable ? "click" : null;
    },
  },

  methods: {
    counterVersionToStr(value) {
      return counterVersionToStr(value);
    },
    async fetchCoverage() {
      let extraParams = {};
      if (this.organizationIds.length) {
        extraParams["organization"] = this.organizationIds.join(",");
      }
      if (this.platformIds.length) {
        extraParams["platform"] = this.platformIds.join(",");
      }
      this.refreshingInternal = true;
      let result = await this.http({
        url: "/api/import-batch/data-coverage/",
        params: {
          report_type: this.reportType.pk,
          start_date: this.startDate,
          end_date: this.endDate,
          split_by_date: false,
          ...extraParams,
        },
        method: "GET",
      });
      if (!result.error) {
        this.data = result.response.data[0];
      }
      this.refreshingInternal = false;
    },
    async refresh() {
      await this.fetchCoverage();
    },
  },

  created() {
    if (this.standalone) {
      this.refresh();
    }
  },

  watch: {
    coverageData: {
      handler() {
        this.data = { ...this.coverageData };
      },
      deep: true,
    },
    startDate() {
      if (this.standalone) {
        this.refresh();
      }
    },
    endDate() {
      if (this.standalone) {
        this.refresh();
      }
    },
    organizationIds: {
      handler() {
        if (this.standalone) {
          this.refresh();
        }
      },
      deep: true,
    },
    platformIds: {
      handler() {
        if (this.standalone) {
          this.refresh();
        }
      },
      deep: true,
    },
    reportType: {
      handler() {
        if (this.standalone) {
          this.refresh();
        }
      },
      deep: true,
    },
  },
});
</script>

<style scoped lang="scss"></style>
