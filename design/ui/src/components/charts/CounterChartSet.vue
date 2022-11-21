<i18n lang="yaml" src="@/locales/charts.yaml"></i18n>
<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  mark_my_org: Highlight my organization

cs:
  mark_my_org: Zvýrazni mou organizaci
</i18n>

<template>
  <div v-if="loading" class="pt-2">
    <v-progress-linear indeterminate color="secondary"></v-progress-linear>
  </div>
  <v-container fluid v-else class="pb-0 px-0 px-sm-2">
    <v-row v-if="!(fixedChart && fixedReportView)">
      <v-col
        cols="12"
        md="6"
        lg="4"
        xl="4"
        class="pb-0"
        v-if="!fixedReportView"
      >
        <ReportViewSelector
          v-model="selectedReportView"
          :report-views-url="reportViewsUrl"
          ref="reportViewSelector"
        />
      </v-col>
      <v-col cols="12" md="6" lg="4" xl="4" class="pb-0" v-if="!fixedChart">
        <ChartTypeSelector
          :report-type="selectedReportView"
          :scope="scope"
          v-model="selectedChartType"
          widget="select"
        />
      </v-col>
      <v-col
        cols="12"
        md="6"
        lg="4"
        xl="4"
        class="pb-0"
        v-if="!fixedChart && metricFilterNeeded"
      >
        <v-select
          :items="availableMetrics"
          v-model="selectedMetric"
          item-text="short_name"
          item-value="pk"
          :label="$t('labels.metric')"
          :loading="loadingMetrics"
          outlined
          dense
        ></v-select>
      </v-col>
      <v-col
        cols="auto"
        class="pb-0"
        v-if="primaryDimension === 'organization' && this.organizationSelected"
      >
        <v-switch
          v-model="showMarkLine"
          :label="$t('mark_my_org')"
          dense
          hide-details
          class="mt-2"
        ></v-switch>
      </v-col>
    </v-row>
    <v-row>
      <v-col class="px-0 px-sm-2">
        <APIChart
          v-if="selectedReportView && selectedChartType"
          :type="typeOfChart"
          :report-type-id="selectedReportView.pk"
          :primary-dimension="primaryDimension"
          :secondary-dimension="secondaryDimension"
          :organization="organizationForChart"
          :platform="platformForChart"
          :title="titleId"
          :import-batch="importBatchId"
          :mdu-id="mduId"
          :stack="
            selectedChartType.stack === undefined
              ? selectedChartType.chart_type === 'h-bar'
              : selectedChartType.stack
          "
          :order-by="selectedChartType.ordering"
          :ignore-date-range="!!(importBatchId || mduId)"
          :show-mark-line="showMarkLine"
          :raw-report-type="selectedReportView.is_proxy"
          :metric="selectedMetric"
          :no-coverage="noCoverage"
          ref="chart"
        >
        </APIChart>
        <v-alert
          v-else-if="selectedReportView"
          type="warning"
          border="right"
          colored-border
          elevation="2"
        >
          {{ $t("no_chart_types_available") }}
        </v-alert>
        <v-alert
          v-else
          type="warning"
          border="right"
          colored-border
          elevation="2"
        >
          {{ $t("no_reports_available_for_title") }}
        </v-alert>
      </v-col>
    </v-row>
  </v-container>
</template>
<script>
import APIChart from "./APIChart";
import { mapActions, mapGetters, mapState } from "vuex";
import axios from "axios";
import ChartTypeSelector from "../ChartTypeSelector";
import ReportViewSelector from "@/components/selectors/ReportViewSelector";

export default {
  name: "CounterChartSet",
  components: { ReportViewSelector, APIChart, ChartTypeSelector },
  props: {
    platformId: { required: false, type: Number },
    titleId: { required: false, type: Number },
    reportViewsUrl: {},
    importBatchId: { required: false, type: Number },
    mduId: { required: false, type: Number },
    ignoreOrganization: { type: Boolean, default: false },
    scope: { default: "", required: false },
    fixedReportView: { required: false, default: null },
    fixedChart: { required: false, default: null },
    // if `preferFullReport` is true then the full/master report will be selected by default
    preferFullReport: { default: false, type: Boolean },
    noCoverage: { default: false, type: Boolean }, // exclude coverage from chart
  },
  data() {
    return {
      selectedReportView: this.fixedReportView,
      selectedChartType: this.fixedChart,
      selectedMetric: null,
      availableMetrics: [],
      loading: false,
      loadingMetrics: false,
      showMarkLine: true,
    };
  },
  computed: {
    ...mapGetters({
      dateRangeStartText: "dateRangeStartText",
      dateRangeEndText: "dateRangeEndText",
      organizationSelected: "organizationSelected",
    }),
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
      lang: "appLanguage",
    }),
    organizationForChart() {
      /* which organization should be reported to the APIChart component
       * - in case we want to compare organizations, we should not add organization to
       * the filter */
      if (this.ignoreOrganization) {
        return null;
      }
      if (
        this.selectedChartType &&
        this.selectedChartType.ignore_organization
      ) {
        return null;
      }
      if (this.selectedOrganizationId === -1) {
        return null; // we want data for all organizations
      }
      return this.selectedOrganizationId;
    },
    platformForChart() {
      if (this.selectedChartType && this.selectedChartType.ignore_platform) {
        return null;
      }
      return this.platformId;
    },
    primaryDimension() {
      if (this.selectedChartType) {
        if (this.selectedChartType.primary_implicit_dimension) {
          return this.selectedChartType.primary_implicit_dimension;
        } else if (this.selectedChartType.primary_dimension) {
          return this.selectedChartType.primary_dimension.short_name;
        }
      }
      return null;
    },
    secondaryDimension() {
      if (this.selectedChartType) {
        if (this.selectedChartType.secondary_implicit_dimension) {
          return this.selectedChartType.secondary_implicit_dimension;
        } else if (this.selectedChartType.secondary_dimension) {
          return this.selectedChartType.secondary_dimension.short_name;
        }
      }
      return null;
    },
    typeOfChart() {
      if (this.selectedChartType) {
        if (this.selectedChartType.chart_type === "v-bar") return "histogram";
        else if (this.selectedChartType.chart_type === "h-bar") return "bar";
        else return "line";
      }
      return null;
    },
    metricFilterNeeded() {
      if (
        this.selectedChartType &&
        this.selectedReportView.short_name !== "interest_view"
      ) {
        return !(
          this.primaryDimension === "metric" ||
          this.secondaryDimension === "metric"
        );
      }
      return false;
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    reloadChartData() {
      if (this.$refs.chart) {
        this.$refs.chart.loadData();
      }
    },
    async loadAvailableMetrics() {
      this.availableMetrics = [];
      this.selectedMetric = null;
      this.loadingMetrics = true;
      let url = `/api/chart-data/${this.selectedReportView.pk}/metrics/?prim_dim=${this.primaryDimension}`;
      if (!this.mduId && !this.importBatchId) {
        url += `&start=${this.dateRangeStart}&end=${this.dateRangeEnd}`;
      }
      if (this.secondaryDimension) {
        url += `&sec_dim=${this.secondaryDimension}`;
      }
      if (this.platformId) url += `&platform=${this.platformId}`;
      if (this.organization)
        url += `&organization=${this.organizationForChart}`;
      if (this.titleId) url += `&target=${this.titleId}`;
      if (this.importBatch) url += `&import_batch=${this.importBatch}`;
      if (this.mduId) url += `&mdu=${this.mduId}`;

      try {
        let resp = await axios.get(url);
        this.availableMetrics = resp.data;
        if (this.availableMetrics.length > 0) {
          // we want to select preferentially a metric which defined interest
          // and then one with "Requests" in the name (to penalize denial
          // metrics, such as No_License, and Investigation metrics)
          let metrics = [...this.availableMetrics];
          metrics.sort((a, b) =>
            [
              !a.is_interest_metric,
              !a.short_name.includes("Requests"),
              a.short_name,
              a.pk,
            ] >
            [
              !b.is_interest_metric,
              !b.short_name.includes("Requests"),
              b.short_name,
              b.pk,
            ]
              ? 1
              : -1
          );
          this.selectedMetric = metrics[0].pk;
        } else {
          this.selectedMetric = null;
        }
      } catch (error) {
        this.showSnackbar({ content: "Error loading metrics: " + error });
      } finally {
        this.loadingMetrics = false;
      }
    },
  },

  watch: {
    fixedReportView() {
      this.selectedReportView = this.fixedReportView;
    },
    fixedChart() {
      this.selectedChartType = this.fixedChart;
    },
    selectedChartType() {
      this.selectedMetric = null;
      if (this.metricFilterNeeded) {
        this.loadAvailableMetrics();
      }
    },
  },
};
</script>

<style lang="scss">
.v-select-list {
  .v-subheader {
    background-color: #ededed;
  }
}
</style>
