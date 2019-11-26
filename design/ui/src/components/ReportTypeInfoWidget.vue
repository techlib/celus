<i18n>
en:
    interest_metrics: Interest defining metrics
    dimensions: Dimensions

cs:
    interest_metrics: Metriky definující zájem
    dimensions: Rozměry
</i18n>

<template>
    <v-scroll-y-transition leave-absolute>
        <v-card outlined :key="reportType.pk">
            <v-card-title>

                <span v-text="reportType.name" :key="reportType.pk" class="font-weight-light"></span>
            </v-card-title>

            <v-card-text>
                <div>
                    <strong v-text="$t('interest_metrics')"></strong>:
                    <span v-text="interestMetrics" :key="reportType.pk"></span>
                </div>
                <div>
                    <strong v-text="$t('dimensions')"></strong>:
                    <span v-text="dimensions" :key="reportType.pk"></span>
                </div>
            </v-card-text>
        </v-card>
    </v-scroll-y-transition>
</template>

<script>
  export default {
    name: "ReportTypeInfoWidget",

    props: {
      reportType: {required: true, type: Object},
    },

    computed: {
      interestMetrics () {
        return this.reportType.interest_metric_set.
          map(item => item.metric.name || item.metric.short_name).
          join(', ')
      },

      dimensions () {
        return this.reportType.dimensions_sorted.map(item => item.short_name).join(', ')
      }
    }
  }
</script>

<style scoped>

</style>
