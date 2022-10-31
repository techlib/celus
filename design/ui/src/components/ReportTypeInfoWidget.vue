<i18n lang="yaml">
en:
  interest_metrics: Interest defining metrics
  specific_dimensions: Dimensions specific to report
  standard_dimensions: Standard dimensions
  standard_dimensions_info: These dimensions are available for all reports.
  specific_dimensions_info: These dimensions are explicitly assigned to this report type and are expected in uploaded data as separate columns.
  report_definition: report definition

cs:
  interest_metrics: Metriky definující zájem
  specific_dimensions: Rozměry specifické pro report
  standard_dimensions: Standardní rozměry
  standard_dimensions_info: Tyto rozměry jsou dostupné pro všechny reporty.
  specific_dimensions_info: Tyto rozměry jsou explicitně přiřazeny k tomuto typu reportu a jsou očekávány v nahraných datech jako samostatné sloupce.
  report_definition: "- definice reportu"
</i18n>

<template>
  <v-fade-transition leave-absolute>
    <v-card outlined :key="reportType.pk">
      <v-card-title>
        <span v-text="reportType.name" :key="reportType.pk"></span>
        <span class="font-weight-light pl-2">{{
          $t("report_definition")
        }}</span>
      </v-card-title>

      <v-card-text>
        <div class="mb-2">
          <strong v-text="$t('interest_metrics')"></strong>:
          <v-chip
            v-for="dim in interestMetrics"
            :key="reportType.pk + '-' + dim"
            v-text="dim"
            class="mr-1"
            label
          >
          </v-chip>
        </div>
        <div class="mb-2">
          <v-tooltip bottom>
            <template #activator="{ on }">
              <strong v-on="on">
                {{ $t("standard_dimensions") }}
                <v-icon small>fa fa-info-circle</v-icon>
              </strong>
            </template>
            {{ $t("standard_dimensions_info") }} </v-tooltip
          >:
          <v-chip
            v-for="dim in standardDimensions"
            :key="reportType.pk + '-' + dim"
            v-text="dim"
            class="mr-1"
            label
          >
          </v-chip>
        </div>
        <div>
          <v-tooltip bottom>
            <template #activator="{ on }">
              <strong v-on="on">
                {{ $t("specific_dimensions") }}
                <v-icon small>fa fa-info-circle</v-icon>
              </strong>
            </template>
            {{ $t("specific_dimensions_info") }} </v-tooltip
          >:
          <v-chip
            v-for="dim in specificDimensions"
            :key="reportType.pk + '-' + dim"
            v-text="dim"
            class="mr-1"
            label
          >
          </v-chip>
        </div>
      </v-card-text>
    </v-card>
  </v-fade-transition>
</template>

<script>
export default {
  name: "ReportTypeInfoWidget",

  props: {
    reportType: { required: true, type: Object },
  },

  data() {
    return {
      standardDimensions: ["Metric", "Title"],
    };
  },

  computed: {
    interestMetrics() {
      return this.reportType.interest_metric_set.map(
        (item) => item.metric.name || item.metric.short_name
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
