<template>
  <v-menu offset-y class="mb-3">
    <template v-slot:activator="{ on }">
      <v-btn color="primary" dark v-on="on" class="elevation-2">
        <v-icon left>fa-download</v-icon>
        Export
      </v-btn>
    </template>
    <v-list>
      <v-list-item :href="url + '&format=xlsx'">
        <v-list-item-title>Raw data Excel</v-list-item-title>
      </v-list-item>
      <v-list-item :href="url + '&format=csv'">
        <v-list-item-title>Raw data CSV</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script>
import { mapGetters, mapState } from "vuex";

export default {
  name: "DataExportWidget",
  props: {
    title: {},
    platform: {},
    reportType: {},
  },
  computed: {
    ...mapState({
      organization: "selectedOrganizationId",
    }),
    ...mapGetters({
      dateStart: "dateRangeStartText",
      dateEnd: "dateRangeEndText",
    }),
    url() {
      let url = `/api/raw-data/?start=${this.dateStart}&end=${this.dateEnd}`;
      if (this.organization) {
        url += `&organization=${this.organization}`;
      }
      if (this.title) {
        url += `&target=${this.title}`;
      }
      if (this.platform) {
        url += `&platform=${this.platform}`;
      }
      if (this.reportType) {
        url += `&report_type=${this.reportType}`;
      }
      return url;
    },
  },
};
</script>

<style scoped></style>
