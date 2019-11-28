<i18n lang="yaml">
en:
    interest_metrics: Interest defining metrics
    specific_dimensions: Dimensions specific to report
    standard_dimensions: Standard dimensions

cs:
    interest_metrics: Metriky definující zájem
    specific_dimensions: Rozměry specifické pro report
    standard_dimensions: Standardní rozměry
</i18n>

<template>
    <v-fade-transition leave-absolute>
        <v-card outlined :key="reportType.pk">
            <v-card-title>

                <span v-text="reportType.name" :key="reportType.pk" class="font-weight-light"></span>
            </v-card-title>

            <v-card-text>
                <div class="mb-2">
                    <strong v-text="$t('interest_metrics')"></strong>:
                    <v-chip
                            v-for="dim in interestMetrics"
                            :key="reportType.pk + '-' + dim"
                            v-text="dim"
                            class="mr-1"
                    >
                    </v-chip>
                    <!--span v-text="interestMetrics" :key="reportType.pk"></span-->
                </div>
                <div class="mb-2">
                    <strong v-text="$t('standard_dimensions')"></strong>:
                    <v-chip
                            v-for="dim in standardDimensions"
                            :key="reportType.pk + '-' + dim"
                            v-text="dim"
                            class="mr-1"
                    >
                    </v-chip>
                    <!--span v-text="standardDimensionsText" :key="reportType.pk"></span-->
                </div>
                <div>
                    <strong v-text="$t('specific_dimensions')"></strong>:
                    <v-chip
                            v-for="dim in specificDimensions"
                            :key="reportType.pk + '-' + dim"
                            v-text="dim"
                            class="mr-1"
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
      reportType: {required: true, type: Object},
    },

    data () {
      return {
        standardDimensions: ['Metric', 'Title'],
      }
    },

    computed: {
      interestMetrics () {
        return this.reportType.interest_metric_set.
          map(item => item.metric.name || item.metric.short_name)
      },

      specificDimensionsText () {
        return this.reportType.dimensions_sorted.map(item => item.short_name).join(', ')
      },

      specificDimensions () {
        return this.reportType.dimensions_sorted.map(item => item.short_name)
      },

      standardDimensionsText () {
        return this.standardDimensions.join(', ')
      }

    }
  }
</script>

<style scoped>

</style>
