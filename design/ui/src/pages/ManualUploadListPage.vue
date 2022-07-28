<i18n lang="yaml">
en:
  manual_uploads: Manually uploaded data
  upload_data_tooltip: Upload new data from file

cs:
  manual_uploads: Ručně nahraná data
  upload_data_tooltip: Nahrát nová data ze souboru
</i18n>

<template>
  <v-container fluid v-if="allowManualDataUpload">
    <v-row>
      <v-col>
        <h2 v-text="$t('manual_uploads')"></h2>
      </v-col>
      <v-col cols="auto">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">
              <ManualUploadButton color="primary" />
            </span>
          </template>
          <span v-text="$t('upload_data_tooltip')"></span>
        </v-tooltip>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <ManualUploadListTable />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import ManualUploadListTable from "@/components/ManualUploadListTable";
import { mapGetters } from "vuex";
import ManualUploadButton from "@/components/ManualUploadButton";

export default {
  name: "ManualUploadListPage",

  components: {
    ManualUploadListTable,
    ManualUploadButton,
  },

  computed: {
    ...mapGetters({
      allowManualDataUpload: "allowManualDataUpload",
    }),
  },
};
</script>

<style scoped></style>
