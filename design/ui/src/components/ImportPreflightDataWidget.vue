<i18n lang="yaml">
en:
  output_logs: Generated logs
  imported_months: Data found for months
  overview: Overview
  upload: Upload
  total_hits: Sum of hits
  imported_metrics: Found metrics
  title_count: Title count
  hits: hits
  is_interest_metric: This metric defines interest for this report type
  data_exists: Data for this month already exists.
  metric_create: Metric will be created.
  metric_ready: Metric is valid.
  metric_unknown: Metric was not found.
  metric_check_failed: Invalid metric for report type.
  import_not_allowed: Data import is not possible
  data_exists_for_months: Data are already present for following months
  cant_use_metrics: Following metrics can't be used

cs:
  output_logs: Vygenerované záznamy
  imported_months: Data nalezena pro měsíce
  overview: Přehled
  upload: Nahrát
  total_hits: Součet zásahů
  imported_metrics: Nalezené metriky
  title_count: Počet titulů
  hits: zásahů
  is_interest_metric: Tato metrika definuje zájem pro tento typ reportu
  data_exists: Data za tento měsíc již existují.
  metric_create: Metrika bude vytvořena.
  metric_ready: Metrika je platná.
  metric_unknown: Metrika nebyla nalezena.
  metric_check_failed: Metrika není pro daný report povolená.
  import_not_allowed: Import dat není možný
  data_exists_for_months: Data za následující měsíce již existují
  cant_use_metrics: Následující metriky nemohou být použity
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col cols="auto">
        <v-card hover>
          <v-card-text>
            <h4>{{ $t("output_logs") }}</h4>
            <div class="text-right">{{ preflightData.log_count }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="auto">
        <v-card hover>
          <v-card-text>
            <h4>{{ $t("total_hits") }}</h4>
            <div class="text-right">{{ preflightData.hits_total }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="auto">
        <v-card hover>
          <v-card-text>
            <h4>{{ $t("title_count") }}</h4>
            <div class="text-right">{{ titleCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="auto">
        <v-card hover>
          <v-card-text>
            <h4>{{ $t("imported_months") }}</h4>
            <div class="text-right">
              <table style="width: 100%">
                <tr v-for="rec in monthsSorted" :key="rec.name">
                  <td class="text-left pr-4">
                    {{ rec.name.substring(0, 7) }}

                    <v-tooltip
                      bottom
                      v-if="preflightData.clashing_months.includes(rec.name)"
                    >
                      <template v-slot:activator="{ on }">
                        <v-icon class="ml-1" x-small color="warning" v-on="on">
                          fa fa-exclamation-triangle
                        </v-icon>
                      </template>
                      <span>{{ $t("data_exists") }}</span>
                    </v-tooltip>
                  </td>
                  <td>{{ rec.value }}</td>
                </tr>
              </table>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="auto">
        <v-card hover>
          <v-card-text>
            <h4>{{ $t("imported_metrics") }}</h4>
            <div class="text-right">
              <table>
                <tr v-for="rec in metricsSorted" :key="rec.name">
                  <v-tooltip bottom>
                    <template #activator="{ on }">
                      <td class="text-left">
                        <v-icon
                          v-on="on"
                          class="ml-2"
                          small
                          left
                          :color="metricState(rec.name).color"
                        >
                          {{ metricState(rec.name).icon }}
                        </v-icon>
                      </td>
                    </template>
                    {{ $t(metricState(rec.name).tooltip) }}
                  </v-tooltip>
                  <td class="text-left pr-4">
                    <v-tooltip v-if="isInterestMetric(rec.name)" bottom>
                      <template #activator="{ on }">
                        <span v-on="on">
                          {{ rec.name }}
                          <v-icon class="ml-2" x-small>fa fa-star</v-icon>
                        </span>
                      </template>
                      {{ $t("is_interest_metric") }}
                    </v-tooltip>
                    <span v-else v-text="rec.name"></span>
                  </td>
                  <td>{{ rec.value }}</td>
                </tr>
              </table>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row v-if="clashingMonths.length > 0 || failedMetrics.length > 0">
      <v-col>
        <v-alert type="warning" outlined>
          <h4 class="mb-2 text-h6">{{ $t("import_not_allowed") }}</h4>
          <div v-if="clashingMonths.length > 0" class="mb-2">
            {{ $t("data_exists_for_months") }}:
            <ul class="pt-1">
              <li v-for="month in clashingMonths" :key="month">
                {{ month.substring(0, 7) }}
              </li>
            </ul>
          </div>
          <div v-if="failedMetrics.length > 0" class="mb-2">
            {{ $t("cant_use_metrics") }}:
            <ul class="pt-1">
              <li v-for="metric in failedMetrics" :key="metric.name">
                <span class="font-weight-medium">{{ metric.name }}</span>
                -
                <span class="font-weight-light">{{
                  $t(metricState(metric.name).tooltip)
                }}</span>
              </li>
            </ul>
          </div>
        </v-alert>
      </v-col>
    </v-row>
  </v-container>
</template>
<script>
export default {
  name: "ImportPreflightDataWidget",

  components: {},

  props: {
    preflightData: { required: true, type: Object },
    interestMetrics: { required: false, type: Array, default: () => [] },
    metrics: { required: true, type: Array, default: () => [] },
    usableMetrics: { required: true, type: Array },
    checkMetrics: {
      required: false,
      type: Boolean,
      default: () => false,
    },
    autoCreateMetrics: { required: true, type: Boolean },
  },

  computed: {
    monthsSorted() {
      return Object.entries(this.preflightData.months)
        .map(([key, value]) => {
          return { name: key, value: value };
        })
        .sort((a, b) => a.name.localeCompare(b.name));
    },

    metricsSorted() {
      return Object.entries(this.preflightData.metrics)
        .map(([key, value]) => {
          return { name: key, value: value };
        })
        .sort((a, b) => a.value - b.value);
    },

    titleCount() {
      return this.preflightData.title_count;
    },
    existingMetricsNames() {
      return this.metrics.map((e) => e.short_name);
    },
    failedMetrics() {
      if (!this.checkMetrics) {
        return [];
      }
      return this.metricsSorted.filter(
        (e) => !this.usableMetrics.includes(e.name)
      );
    },
    clashingMonths() {
      return this.preflightData.clashing_months;
    },
  },

  methods: {
    isInterestMetric(metricName) {
      if (this.interestMetrics.indexOf(metricName) > -1) {
        return true;
      }
      return false;
    },
    metricState(metricName) {
      if (this.checkMetrics) {
        if (!this.usableMetrics.includes(metricName)) {
          // Metric check failed
          return {
            icon: "fas fa-exclamation-circle",
            color: "error",
            tooltip: "metric_check_failed",
          };
        }
      }
      if (this.autoCreateMetrics) {
        if (!this.existingMetricsNames.includes(metricName)) {
          return {
            icon: "fas fa-plus-circle",
            color: "info",
            tooltip: "metric_create",
          };
        }
      } else {
        if (!this.existingMetricsNames.includes(metricName)) {
          return {
            icon: "fas fa-exclamation-circle",
            color: "error",
            tooltip: "metric_unknown",
          };
        }
      }
      return {
        icon: "fas fa-check-circle",
        color: "success",
        tooltip: "metric_ready",
      };
    },
  },
};
</script>
<style scoped lang="scss">
ul.no-decoration {
  list-style: none;
}
</style>
