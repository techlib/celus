<template>
  <v-sheet>
    <v-container>
      <v-row>
        <v-col>
          <ReportViewSelector
            v-model="selectedReportView"
            :report-views-url="reportViewsUrl"
            :view-filter="notInterestFilter"
          />
        </v-col>
      </v-row>
      <v-row v-if="selectedReportView">
        <v-col cols="12">
          <CoverageMap
            :report-type-id="selectedReportView.pk"
            :organization-id="organizationId"
            :platform-id="platformId"
            :start-month="dateRangeStart"
            :end-month="dateRangeEnd"
          />
        </v-col>
      </v-row>
    </v-container>
  </v-sheet>
</template>

<script>
import CoverageMap from "@/components/charts/CoverageMap";
import { mapGetters, mapState } from "vuex";
import ReportViewSelector from "@/components/selectors/ReportViewSelector";

export default {
  name: "CoverageOverviewWidget",

  components: { ReportViewSelector, CoverageMap },

  props: {
    platformId: { required: true, type: Number },
  },

  data() {
    return {
      selectedReportView: null,
    };
  },

  computed: {
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
      organizationSelected: "organizationSelected",
    }),
    reportViewsUrl() {
      if (this.selectedOrganizationId && this.platformId) {
        return `/api/organization/${this.selectedOrganizationId}/platform/${this.platformId}/report-views/`;
      }
      return null;
    },
    organizationId() {
      if (this.organizationSelected) {
        return this.selectedOrganizationId;
      }
      return null;
    },
  },

  methods: {
    notInterestFilter(item) {
      return item.short_name !== "interest_view";
    },
  },
};
</script>

<style scoped></style>
