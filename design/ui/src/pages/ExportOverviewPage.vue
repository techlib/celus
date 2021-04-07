<i18n src="@/locales/common.yaml" lang="yaml" />
<i18n lang="yaml"></i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2 v-text="$t('pages.exports')"></h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <ExportOverviewTable />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import ExportOverviewTable from "@/components/reporting/ExportOverviewTable";
export default {
  name: "MaintenancePage",
  components: {
    ExportOverviewTable,
  },
};
</script>

<style scoped></style>
