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
</i18n>

<template>
  <v-container>
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
  </v-container>
</template>
<script>
export default {
  name: "ImportPreflightDataWidget",

  components: {},

  props: {
    preflightData: { required: true, type: Object },
    interestMetrics: { required: false, type: Array, default: () => [] },
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
      return Object.keys(this.preflightData.titles).length;
    },
  },

  methods: {
    isInterestMetric(metricName) {
      if (this.interestMetrics.indexOf(metricName) > -1) {
        return true;
      }
      return false;
    },
  },
};
</script>
<style scoped lang="scss">
ul.no-decoration {
  list-style: none;
}
</style>
