<template>
  <v-container fluid class="pb-0">
    <v-row class="pb-0">
      <v-col class="pb-0">
        <CounterChartSet
          v-if="mdu"
          :platform-id="mdu.platform.pk"
          :mdu-id="mduId"
          :report-views-url="reportViewsUrl"
          prefer-full-report
          ignore-organization
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import CounterChartSet from "./charts/CounterChartSet";
import axios from "axios";
import { mapActions } from "vuex";
export default {
  name: "MDUChart",
  components: { CounterChartSet },
  props: {
    mduId: { required: true },
  },
  data() {
    return {
      selectedChartType: null,
      mdu: null,
    };
  },
  computed: {
    reportViewsUrl() {
      if (this.mdu) {
        return `/api/report-type/${this.mdu.report_type.pk}/report-views/`;
      }
      return null;
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadDetails() {
      try {
        let response = await axios.get(
          `/api/manual-data-upload/${this.mduId}/`
        );
        this.mdu = response.data;
      } catch (error) {
        this.showSnackbar({
          content: "Error loading manual data upload details: " + error,
        });
      }
    },
  },
  watch: {
    mduId() {
      this.loadDetails();
    },
  },
  mounted() {
    this.loadDetails();
  },
};
</script>

<style scoped></style>
