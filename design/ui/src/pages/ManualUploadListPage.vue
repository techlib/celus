<i18n lang="yaml">
en:
  manual_uploads: Manually uploaded data
  upload_data_tooltip: Upload new data from file

cs:
  manual_uploads: Ručně nahraná data
  upload_data_tooltip: Nahrát nová data ze souboru
</i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <h2>{{ $t("manual_uploads") }}</h2>
      </v-col>
      <v-col cols="auto">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <span v-bind="props">
              <ManualUploadButton color="primary"></ManualUploadButton>
            </span>
          </template>
          <span>{{ $t("upload_data_tooltip") }}</span>
        </v-tooltip>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <ManualUploadListTable></ManualUploadListTable>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import ManualUploadListTable from "@/components/ManualUploadListTable";
import ManualUploadButton from "@/components/ManualUploadButton";

export default {
  name: "ManualUploadListPage",

  components: {
    ManualUploadListTable,
    ManualUploadButton,
  },
};
</script>

<style scoped></style>
