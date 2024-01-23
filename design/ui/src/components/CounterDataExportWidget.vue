<i18n lang="yaml" src="@/locales/dialog.yaml"></i18n>

<template>
  <v-btn
    :href="downloadUrl"
    color="primary"
    :disabled="organization.pk < 0 || counterReportType.used === 0"
  >
    <v-icon left small>fa-download</v-icon>
    {{ this.counterReportType.code }}
  </v-btn>
</template>

<script>
import { mapGetters } from "vuex";
import axios from "axios";

export default {
  name: "CounterDataExportWidget",

  props: {
    platform: { type: Object, required: true },
    counterReportType: { type: Object, required: true },
  },

  data() {
    return {};
  },

  computed: {
    ...mapGetters({
      organization: "selectedOrganization",
      dateStart: "dateRangeStartText",
      dateEnd: "dateRangeEndText",
    }),
    downloadUrl() {
      let url = `/api/counter-data-export/${this.counterReportType.id}/download/`;
      url += `?platform=${this.platform.pk}`;
      url += `&organization=${this.organization?.pk || 0}`;
      if (this.dateStart) {
        url += `&start_date=${this.dateStart}`;
      }
      if (this.dateEnd) {
        url += `&end_date=${this.dateEnd}`;
      }
      return url;
    },
  },
  methods: {},
};
</script>

<style scoped></style>
