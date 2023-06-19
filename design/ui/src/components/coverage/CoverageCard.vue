<i18n lang="yaml">
en:
  number_of_platforms: Number of platforms using this report in the selected period.
  number_of_organizations: Number of organizations using this report in the selected period.

cs:
  number_of_platforms: Počet platforem používajících tento report ve zvoleném období.
  number_of_organizations: Počet organizací používajících tento report ve zvoleném období.
</i18n>

<template>
  <v-card
    class="pt-4 d-flex flex-column justify-space-between"
    :class="selected ? 'selected' : ''"
    @[clickHandler]="$emit('click', { reportType })"
    :elevation="el"
  >
    <div
      v-if="selected"
      style="position: absolute; top: 4px; right: 4px; z-index: 1"
    >
      <v-icon color="grey lighten-1"
        >fa fa-sync-alt {{ refreshingComputed ? "fa-spin" : "" }}</v-icon
      >
    </div>
    <CoverageScoreGauge
      :value="data ? data.ratio : null"
      :loading="!data || refreshingComputed"
    />
    <v-card-text class="text-center">
      <v-tooltip bottom>
        <template #activator="{ on }">
          <div class="font-weight-bold" v-on="on">
            <span v-if="label">{{ label }}</span>
            <span v-else-if="reportType">
              <span class="font-weight-light"
                >{{
                  reportType.counter_version
                    ? "C" + reportType.counter_version
                    : "non-COUNTER"
                }}
                /</span
              >
              {{ reportType.short_name }}
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
      <v-tooltip bottom v-if="showPlatformCount">
        <template #activator="{ on }">
          <div class="mx-1" v-on="on">
            <v-icon x-small class="pb-1">fa fa-list-alt</v-icon>
            {{ data.platform_count }}
          </div>
        </template>
        <span>{{ $t("number_of_platforms") }}</span>
      </v-tooltip>
      <v-tooltip bottom v-if="showOrganizationCount">
        <template #activator="{ on }">
          <div class="mx-1" v-on="on">
            <v-icon x-small class="pb-1">fa fa-university</v-icon>
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
  },

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
