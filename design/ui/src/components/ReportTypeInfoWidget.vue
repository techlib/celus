<i18n lang="yaml">
en:
  interest_metrics: Interest defining metrics
  interest_metrics_empty: Report has no interest defining metrics
  specific_dimensions: Dimensions specific to report
  specific_dimensions_empty: Report has no specific dimensions
  standard_dimensions: Standard dimensions
  standard_dimensions_info: These dimensions are available for all reports.
  specific_dimensions_info: These dimensions are explicitly assigned to this report type and are expected in uploaded data as separate columns.
  specific_dimensions_info_raw: These dimensions are specific for this report type and are expected in the uploaded data.
  report_definition: report definition

cs:
  interest_metrics: Metriky definující zájem
  interest_metrics_empty: Report nemá metriky definující zájem
  specific_dimensions: Rozměry specifické pro report
  specific_dimensions_empty: Report nemá specifické dimenze
  standard_dimensions: Standardní rozměry
  standard_dimensions_info: Tyto rozměry jsou dostupné pro všechny reporty.
  specific_dimensions_info: Tyto rozměry jsou explicitně přiřazeny k tomuto typu reportu a jsou očekávány v nahraných datech jako samostatné sloupce.
  specific_dimensions_info_raw: Tyto rozměry jsou specifické pro tento typ reportu a jsou očekávány v nahraných datech.
  report_definition: "- definice reportu"
</i18n>

<template>
  <v-fade-transition leave-absolute>
    <v-card :key="reportType.pk" v-bind="$attrs">
      <v-card-title v-if="!hideTitle">
        <span v-text="reportType.name" :key="reportType.pk"></span>
        <span class="font-weight-light pl-2">{{
          $t("report_definition")
        }}</span>
      </v-card-title>
      <v-card-text>
        <table class="overview">
          <tr v-if="!hideImplicitDimensions" class="mb-2">
            <th>
              <v-tooltip location="bottom">
                <template #activator="{ props }">
                  <strong v-bind="props">
                    {{ $t("standard_dimensions") }}
                    <v-icon size="small">fa fa-info-circle</v-icon>
                  </strong>
                </template>
                {{ $t("standard_dimensions_info") }}
              </v-tooltip>
            </th>
            <td>
              <v-chip
                v-for="dim in standardDimensions"
                :key="reportType.pk + '-' + dim"
                class="mr-1"
                label
              >
                {{ dim }}
              </v-chip>
            </td>
          </tr>
          <tr>
            <th>
              <v-tooltip location="bottom">
                <template #activator="{ props }">
                  <strong v-bind="props">
                    {{ $t("specific_dimensions") }}
                    <v-icon size="small">fa fa-info-circle</v-icon>
                  </strong>
                </template>
                {{
                  isRaw
                    ? $t("specific_dimensions_info_raw")
                    : $t("specific_dimensions_info")
                }}
              </v-tooltip>
            </th>
            <td v-if="specificDimensions.length > 0">
              <v-chip
                v-for="dim in specificDimensions"
                :key="reportType.pk + '-' + dim"
                class="mr-1"
                label
              >
                {{ dim }}
              </v-chip>
            </td>
            <td v-else>
              <i>{{ $t("specific_dimensions_empty") }}</i>
            </td>
          </tr>
          <tr>
            <th v-text="$t('interest_metrics')"></th>
            <td v-if="interestMetrics.length > 0">
              <v-chip
                v-for="dim in interestMetrics"
                :key="reportType.pk + '-' + dim"
                class="mr-1"
                label
              >
                {{ dim }}
              </v-chip>
            </td>
            <td v-else>
              <i>{{ $t("interest_metrics_empty") }}</i>
            </td>
          </tr>
        </table>
      </v-card-text>
    </v-card>
  </v-fade-transition>
</template>

<script>
export default {
  name: "ReportTypeInfoWidget",

  props: {
    reportType: { required: true, type: Object },
    hideTitle: { default: false, type: Boolean },
    hideImplicitDimensions: { default: false, type: Boolean },
    isRaw: { default: false, type: Boolean },
  },

  data() {
    return {
      standardDimensions: ["Metric", "Title"],
    };
  },

  computed: {
    interestMetrics() {
      return this.reportType.interest_metric_set.map(
        (item) => item.metric.name || item.metric.short_name,
      );
    },

    specificDimensionsText() {
      return this.reportType.dimensions_sorted
        .map((item) => item.short_name)
        .join(", ");
    },

    specificDimensions() {
      return this.reportType.dimensions_sorted.map((item) => item.short_name);
    },

    standardDimensionsText() {
      return this.standardDimensions.join(", ");
    },
  },
};
</script>

<style scoped></style>
