<i18n lang="yaml">
en:
  maintenance: Maintenance
cs:
  maintenance: Údržba
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
          <v-card-text>
            <v-tabs v-model="tab">
              <v-tab
                color="primary"
                value="charts"
                :class="{
                  'tab-active': tab === 'charts',
                }"
                >{{ $t("charts") }}
              </v-tab>
            </v-tabs>
            <v-window v-model="tab">
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
import ReportViewToChartManagementWidget from "@/components/admin/ReportViewToChartManagementWidget";
export default {
  name: "MaintenancePage",
  components: {
    ReportViewToChartManagementWidget,
  },
  data() {
    return {
      tab: "charts",
    };
  },
};
</script>

<style scoped>
.tab-inactive {
  color: rgba(0, 0, 0, 0.54);
}
</style>
