<i18n lang="yaml">
en:
  out_of: out of
  report_months_present: report-months present
  details: details

cs:
  out_of: z celkového počtu
  report_months_present: report-měsíců přítomno
  details: podrobnosti
</i18n>

<template>
  <div>
    <CoverageScoreGauge :value="ratio" :loading="loading" />

    <div v-if="data" class="mt-6 text-center">
      <div class="text-h5">{{ formatInteger(data.ib_count) }}</div>
      <div class="my-2">{{ $t("out_of") }}</div>
      <div class="text-h5">{{ formatInteger(data.ib_max) }}</div>
      <div class="my-2">{{ $t("report_months_present") }}</div>
      <div>
        <router-link :to="{ name: 'data-coverage-overview' }">
          {{ $t("details") }}
          <v-icon x-small color="primary">fa fa-external-link-alt</v-icon>
        </router-link>
      </div>
    </div>
  </div>
</template>
<script>
import CoverageScoreGauge from "@/components/charts/CoverageScoreGauge.vue";
import cancellation from "@/mixins/cancellation";
import { mapGetters, mapState } from "vuex";
import { formatInteger } from "@/libs/numbers";

export default {
  name: "OverallCoverageDashboardWidget",

  mixins: [cancellation],

  components: { CoverageScoreGauge },

  data() {
    return {
      data: null,
      loading: false,
    };
  },

  computed: {
    ...mapState({
      organizationId: "selectedOrganizationId",
    }),
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
      dateRangeCoverageEndText: "dateRangeCoverageEndText",
      organizationSelected: "organizationSelected",
    }),
    ratio() {
      return this.data?.ratio ?? null;
    },
  },

  methods: {
    async fetchCoverage() {
      this.loading = true;
      let extraParams = {};
      if (this.organizationSelected) {
        extraParams = { organization: this.organizationId };
      }
      let result = await this.http({
        url: "/api/import-batch/total-data-coverage/",
        params: {
          start_date: this.dateRangeStart,
          end_date: this.dateRangeCoverageEndText,
          ...extraParams,
        },
        method: "GET",
      });
      if (!result.error) {
        this.data = result.response.data;
      }
      this.loading = false;
    },
    refetch() {
      this.data = null;
      this.fetchCoverage();
    },
    formatInteger,
  },

  mounted() {
    this.fetchCoverage();
  },

  watch: {
    organizationId() {
      this.refetch();
    },
    dateRangeStart() {
      this.refetch();
    },
    dateRangeEnd() {
      this.refetch();
    },
  },
};
</script>
