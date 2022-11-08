<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  platform_to_report: Platforms ⭢ Report types
  report_to_metrics: Report type ⭢ Metrics
  interest_reports_intro: |
    The following table shows which reports are set to define interest for
    each platform. Only data from the corresponding reports will be considered when computing
    interest from the underlying platform data.
  interest_reports_intro2: |
    More detailed info about used metrics is available on the next tab.
  interest_metrics_intro: |
    The following table shows metrics assigned to individual reports which define the interest
    for that particular report. If a report does not have a metric assigned, no interest will
    be computed from the underlying data.
  interest_metrics_intro2: |
    Metrics are assigned to different interest groups/types. These define for which type of interest
    a metric will be used.

cs:
  platform_to_report: Platformy ⭢ Typy reportů
  report_to_metrics: Typy reportů ⭢ Metriky
  interest_reports_intro: |
    Následující tabulka ukazuje jaké reporty definují zájem pro jednotlivé platformy. Jen data
    z těchto reportů budou použita při výpočtu zájmu z dat pro danou platformu.
  interest_reports_intro2: |
    Podrobnější informace o použitých metrikách jsou dostupné na sousední záložce.
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
          <v-tabs v-model="tab" grow>
            <v-tab to="#reports">{{ $t("platform_to_report") }}</v-tab>
            <v-tab to="#metrics">{{ $t("report_to_metrics") }}</v-tab>
            <v-tab-item value="reports">
              <v-card flat>
                <v-card-text class="pa-8">
                  <p>{{ $t("interest_reports_intro") }}</p>
                  <p>{{ $t("interest_reports_intro2") }}</p>
                  <InterestOverviewReports />
                </v-card-text>
              </v-card>
            </v-tab-item>
            <v-tab-item value="metrics">
              <v-card flat>
                <v-card-text class="pa-8">
                  <p>{{ $t("interest_metrics_intro") }}</p>
                  <p>{{ $t("interest_metrics_intro2") }}</p>
                  <InterestOverviewMetrics />
                </v-card-text>
              </v-card>
            </v-tab-item>
          </v-tabs>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import InterestOverviewReports from "@/components/InterestOverviewReports";
import InterestOverviewMetrics from "@/components/InterestOverviewMetrics";

export default {
  name: "InterestOverview",

  components: { InterestOverviewReports, InterestOverviewMetrics },

  data() {
    return {
      tab: "reports",
    };
  },
};
</script>
