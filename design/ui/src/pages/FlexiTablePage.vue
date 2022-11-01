<i18n src="@/locales/common.yaml" lang="yaml" />
<i18n lang="yaml"></i18n>

<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <FlexiTableEditor :report-id="reportId" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import FlexiTableEditor from "@/components/reporting/FlexiTableEditor";
export default {
  name: "FlexiTablePage",

  components: {
    FlexiTableEditor,
  },

  props: {
    reportId: { required: false, type: Number },
  },
};
</script>

<style scoped></style>
