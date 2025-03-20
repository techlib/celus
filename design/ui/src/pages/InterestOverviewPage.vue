<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  report_to_metrics: Report type ⭢ Metrics
  interest_metrics_intro: |
    The following table shows metrics assigned to individual reports which define the interest
    for that particular report. If a report does not have a metric assigned, no interest will
    be computed from the underlying data.
  interest_metrics_intro2: |
    Metrics are assigned to different interest groups/types. These define for which type of interest
    a metric will be used.

cs:
  report_to_metrics: Typy reportů ⭢ Metriky
  interest_metrics_intro: |
    Následující tabulka ukazuje metriky přiřazené k jednotlivým reportům, které definují zájem
    pro daný report. Pokud nemá report vybranou žádnou metriku, nebude pro něj vypočítáván zájem.
  interest_metrics_intro2: |
    Metriky mohou být přiřazeny k různým skupinám/typům zájmu. Ty definují pro jaký typ zájmu budou
    data z dané metriky započítána.
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col class="pb-0">
        <h2>{{ $t("pages.interest_overview") }}</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-tabs
            v-model="tab"
            dark
            bg-color="info"
            centered
            align-tabs="center"
            slider-color="#ffffff33"
            slider-size="48"
          >
            <v-tab
              :class="{
                'tab-active': tab === 'metrics',
                'tab-inactive': tab !== 'metrics',
              }"
              value="metrics"
              >{{ $t("report_to_metrics") }}</v-tab
            >
          </v-tabs>
          <v-card-text class="pa-8">
            <v-window v-model="tab">
              <v-window-item value="metrics">
                <v-card flat>
                  <v-card-text>
                    <p>{{ $t("interest_metrics_intro") }}</p>
                    <p class="pb-8 pt-4">{{ $t("interest_metrics_intro2") }}</p>
                    <InterestOverviewMetrics></InterestOverviewMetrics>
                  </v-card-text>
                </v-card>
              </v-window-item>
            </v-window>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import InterestOverviewMetrics from "@/components/InterestOverviewMetrics";

export default {
  name: "InterestOverview",

  components: { InterestOverviewMetrics },

  data() {
    return {
      tab: "metrics",
    };
  },
};
</script>

<style scoped></style>
