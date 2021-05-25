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
        <h2 v-text="$t('maintenance')"></h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col :cols="12">
        <v-card>
          <v-card-text>
            <v-tabs v-model="tab">
              <v-tab href="#no-interest" v-text="$t('no_interest')"> </v-tab>
              <v-tab href="#charts" v-text="$t('charts')"> </v-tab>

              <v-tab-item value="no-interest">
                <UndefinedInterestWidget />
              </v-tab-item>
              <v-tab-item value="charts">
                <ReportViewToChartManagementWidget />
              </v-tab-item>
            </v-tabs>
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

<style scoped></style>
