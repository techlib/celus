<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  platform_to_report: Platforms ⭢ Report types
  report_to_metrics: Report type ⭢ Metrics

cs:
  platform_to_report: Platformy ⭢ Typy reportů
  report_to_metrics: Typy reportů ⭢ Metriky
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
              <InterestOverviewReports />
            </v-tab-item>
            <v-tab-item value="metrics">
              <InterestOverviewMetrics />
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
