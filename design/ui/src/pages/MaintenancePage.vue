<i18n lang="yaml">
en:
  maintenance: Maintenance
  no_interest: Platforms without interest definition
cs:
  maintenance: Údržba
  no_interest: Platformy bez definice zájmu
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2>{{ $t("maintenance") }}</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col :cols="12">
        <v-card>
          <v-tabs v-model="tab">
            <v-tab
              color="primary"
              value="no-interest"
              :class="{
                'tab-active': tab === 'no-interest',
                'tab-inactive': tab === 'charts',
              }"
              >{{ $t("no_interest") }}
            </v-tab>
            <v-tab
              color="primary"
              value="charts"
              :class="{
                'tab-inactive': tab === 'no-interest',
                'tab-active': tab === 'charts',
              }"
              >{{ $t("charts") }}
            </v-tab>
          </v-tabs>
          <v-card-text>
            <v-window v-model="tab">
              <v-window-item value="no-interest">
                <UndefinedInterestWidget></UndefinedInterestWidget>
              </v-window-item>
              <v-window-item value="charts">
                <ReportViewToChartManagementWidget></ReportViewToChartManagementWidget>
              </v-window-item>
            </v-window>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import UndefinedInterestWidget from "@/components/UndefinedInterestWidget";
import ReportViewToChartManagementWidget from "@/components/admin/ReportViewToChartManagementWidget";
export default {
  name: "MaintenancePage",
  components: {
    ReportViewToChartManagementWidget,
    UndefinedInterestWidget,
  },
  data() {
    return {
      tab: "no-interest",
    };
  },
};
</script>

<style scoped>
.tab-inactive {
  color: rgba(0, 0, 0, 0.54);
}
</style>
