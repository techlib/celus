<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  intro: This page contains several purpose-built reports intended for specific
    use cases - usually to facilitate reporting to a particular funding
    or regulatory body or agency.
  organization_missing: Please select an organization to generate report for from the organization selector at the top of the page.
  select_date_range: Select date range with explicit start date from the selector at the top of the page.
  export_tooltip: Export the report output into an Excel file

cs:
  intro: Tato stránka obsahuje několik speciálních reportů určených pro
    konkrétní účely - obvykle pro reporting financující nebo dohledující
    organizaci nebo státnímu orgánu.
  organization_missing: Prosím vyberte organizaci, pro kterou chcete vytvořit report z výběru organizací na vrchu stránky.
  select_date_range: Vyberte časový rozsah s explicitním počátečním datem z výběru na vrchu stránky.
  export_tooltip: Exportovat výstup reportu do Excel souboru
</i18n>

<template>
  <v-container fluid>
    <v-row class="px-2">
      <v-col>
        <h2>{{ $t("pages.specialized_reports") }}</h2>
      </v-col>
    </v-row>
    <v-row class="px-2">
      <v-col>
        <p>{{ $t("intro") }}</p>
      </v-col>
    </v-row>
    <v-row v-if="!organizationSelected">
      <v-col>
        <v-alert type="warning" outlined>
          {{ $t("organization_missing") }}
        </v-alert>
      </v-col>
    </v-row>
    <v-row v-if="!dateRangeCorrect">
      <v-col>
        <v-alert type="warning" outlined>
          {{ $t("select_date_range") }}
        </v-alert>
      </v-col>
    </v-row>
    <v-row class="px-2">
      <v-col>
        <v-select
          :items="reports"
          v-model="selectedReport"
          item-text="name"
          item-value="name"
          return-object
          :label="$t('labels.select_report')"
          :hint="selectedReport ? selectedReport.description : ''"
          :persistent-hint="!!selectedReport"
        >
          <template #item="{ item }">
            <v-list-item-content>
              <v-list-item-title>
                {{ item.name }}
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ item.description }}
              </v-list-item-subtitle>
            </v-list-item-content>
          </template>
        </v-select>
      </v-col>
      <v-col cols="auto" class="align-self-center">
        <v-btn @click="runReport" color="primary" :disabled="!canRun">
          {{ $t("labels.run_report") }}
        </v-btn>
      </v-col>
      <v-col cols="auto" class="align-self-center">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-btn
              :href="exportUrl"
              color="warning"
              v-on="on"
              :disabled="!canRun"
            >
              {{ $t("labels.export") }}
            </v-btn>
          </template>
          <span>{{ $t("export_tooltip") }}</span>
        </v-tooltip>
      </v-col>
    </v-row>

    <v-row>
      <v-col>
        <SpecializedReport
          v-if="selectedReport"
          :definition="selectedReport"
          ref="output"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import SpecializedReport from "@/components/special/SpecializedReport";
import cancellation from "@/mixins/cancellation";
import { mapGetters } from "vuex";

export default {
  name: "SpecializedReportsPage",

  mixins: [cancellation],

  components: {
    SpecializedReport,
  },

  data() {
    return {
      reports: [],
      selectedReport: null,
    };
  },

  computed: {
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeExplicitEndText",
      organizationObj: "selectedOrganization",
      organizationSelected: "organizationSelected",
    }),
    exportUrl() {
      if (this.selectedReport) {
        return this.$router.resolve({
          path: `/api/reporting/reports/${this.selectedReport.name}/export/`,
          query: {
            start_date: this.dateRangeStart,
            end_date: this.dateRangeEnd,
            organization: this.organizationObj ? this.organizationObj.pk : null,
          },
        }).href;
      }
      return null;
    },
    dateRangeCorrect() {
      return this.dateRangeStart && this.dateRangeEnd;
    },
    canRun() {
      return (
        this.selectedReport &&
        this.dateRangeCorrect &&
        this.organizationSelected
      );
    },
  },

  methods: {
    async fetchReports() {
      let result = await this.http({
        url: "/api/reporting/reports/",
        method: "GET",
      });
      if (!result.error) {
        this.reports = result.response.data;
        if (this.reports.length > 0) this.selectedReport = this.reports[0];
      }
    },
    runReport() {
      if (this.selectedReport) {
        this.$refs.output.runReport();
      }
    },
  },

  created() {
    this.fetchReports();
  },
};
</script>
