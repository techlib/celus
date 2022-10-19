<i18n src="@/locales/common.yaml" lang="yaml" />
<i18n lang="yaml">
en:
  note: Please note that this page only lists finished exports. To export new data, use either the {reports} or {adhoc} functions.

cs:
  note: Tato stránka obsahuje pouze seznam již dokončených exportů. Pro vytvoření nového exportu použijte funkce {reports} nebo {adhoc}.
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2 v-text="$t('pages.exports')"></h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <i18n path="note">
          <template #reports>
            <router-link :to="{ name: 'flexireports' }">{{
              $t("pages.flexi_reports")
            }}</router-link>
          </template>
          <template #adhoc>
            <router-link :to="{ name: 'flexitable' }">{{
              $t("pages.create_report")
            }}</router-link>
          </template>
        </i18n>
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
