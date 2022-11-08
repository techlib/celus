<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  no_report_defined: No report is assigned as defining interest for this platform. No interest will be extracted from this platform's data.
  used_metrics: Used metrics
  all: All
  all_long: Show all platforms
  undefined: Without report
  undefined_long: Only platforms without interest report
  report_filter: Report filter

cs:
  no_report_defined: Tato platforma nemá přiřazený žádný report pro výpočet zájmu. Z dat pro tuto platformu nebude vypočítáván zájem.
  used_metrics: Použité metriky
  all: Vše
  all_long: Všechny platformy
  undefined: Bez reportu
  undefined_long: Jen platformy bez reportu definujícího zájem
  report_filter: Filtr podle reportů
</i18n>

<template>
  <v-data-table
    :items="visibleItems"
    :headers="headers"
    :loading="loading"
    :search="search"
    :expanded.sync="expanded"
    show-expand
    item-key="pk"
    expand-icon="fa fa-caret-down"
    :items-per-page="50"
    :footer-props="{ itemsPerPageOptions: [50, 100, -1] }"
    :custom-filter="searchFilter"
  >
    <template #top>
      <v-row>
        <v-col cols="auto">
          <v-select
            v-model="selectedReport"
            :items="usedReports"
            :label="$t('report_filter')"
            item-value="pk"
            item-text="short_name"
          >
            <template #item="{ item }">
              <v-list-item-content :class="item.special ? 'font-italic' : ''">
                <span>{{ item.short_name }}</span>
                <span class="text-caption">{{ item.name }}</span>
              </v-list-item-content>
            </template>
          </v-select>
        </v-col>
        <v-spacer></v-spacer>
        <v-col cols="4">
          <v-text-field
            v-model="search"
            append-icon="fa-search"
            :label="$t('labels.search')"
            single-line
            hide-details
            clearable
          >
          </v-text-field>
        </v-col>
      </v-row>
    </template>
    <template v-slot:expanded-item="{ headers, item }">
      <td :colspan="headers.length">
        <div v-if="item.interest_reports.length > 0">
          <v-list-item v-for="report in item.interest_reports" :key="report.pk">
            <v-list-item-content>
              <v-list-item-title>
                {{ report.short_name }}:
                <span class="font-weight-light">
                  {{ report[`name_${lang}`] }}
                </span>
              </v-list-item-title>
              <v-list-item-subtitle :key="rerenderMetrics">
                <span class="pr-2">{{ $t("used_metrics") }}:</span>
                <MetricChip
                  v-for="im in report.interest_metric_set"
                  :key="im.metric.pk"
                  :metric="im.metric"
                />
              </v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>
        </div>
        <div v-else class="pl-4 text--secondary">
          {{ $t("no_report_defined") }}
        </div>
      </td>
    </template>
    <template v-slot:[`item.reports`]="{ item }">
      <ReportChip
        v-for="(report, index) in item.interest_reports"
        :key="index"
        :report="report"
        :highlight="selectedReport && report.pk === selectedReport"
      >
      </ReportChip>
    </template>
    <template v-slot:[`item.actions`]="{ item }">
      <v-icon small class="mr-2" @click="editItem(item)">fas fa-pen</v-icon>
    </template>
  </v-data-table>
</template>

<script>
import ReportChip from "@/components/reporting/ReportChip";
import MetricChip from "@/components/reporting/MetricChip";
import cancellation from "@/mixins/cancellation";
import { mapState } from "vuex";

export default {
  name: "InterestOverviewReports",

  mixins: [cancellation],

  components: { MetricChip, ReportChip },

  data() {
    return {
      items: [],
      expanded: [],
      search: "",
      loading: false,
      rerenderMetrics: 0,
      selectedReport: null,
      usedReports: [],
    };
  },
  computed: {
    ...mapState({
      lang: "appLanguage",
    }),
    headers() {
      return [
        {
          text: this.$i18n.t("platform"),
          value: "name",
        },
        {
          text: this.$i18n.t("labels.report_type"),
          value: "reports",
          sortable: false,
        },
      ];
    },
    visibleItems() {
      if (this.selectedReport === -1)
        return this.items.filter((item) => item.interest_reports.length === 0);
      if (this.selectedReport) {
        return this.items.filter((item) =>
          item.interest_reports.find((ir) => ir.pk === this.selectedReport)
        );
      }
      return this.items;
    },
  },
  methods: {
    async fetchPlatformData() {
      const url = "api/platform-interest-report/";
      this.loading = true;
      const { response } = await this.http({ url });
      this.loading = false;
      if (response) {
        this.items = response.data;
        this.items.sort((a, b) => a.name.localeCompare(b.name));
        let seenReports = new Map();
        this.items.forEach((item) => {
          item.interest_reports.sort((a, b) =>
            a.short_name.localeCompare(b.short_name)
          );
          item.interest_reports.forEach((ir) => {
            if (!seenReports.has(ir.short_name))
              seenReports.set(ir.short_name, ir);
          });
        });
        let reportsSorted = [...seenReports.values()];
        reportsSorted.sort((a, b) => a.short_name.localeCompare(b.short_name));
        this.usedReports = [
          {
            pk: null,
            short_name: this.$t("all"),
            name: this.$t("all_long"),
            special: true,
          },
          {
            pk: -1,
            short_name: this.$t("undefined"),
            name: this.$t("undefined_long"),
            special: true,
          },
          ...reportsSorted,
        ];
      }
    },
    searchFilter(value, search, item) {
      // Search platform directly
      let match = (value, search) =>
        value && value.toLowerCase().includes(search.toLowerCase());
      if (match(value, search)) {
        return true;
      }
      for (const rt of item.interest_reports) {
        if (match(rt.short_name, search)) {
          return true;
        }
        for (const im of rt.interest_metric_set) {
          if (match(im.metric.short_name, search)) {
            return true;
          }
          if (match(im.metric[`name_${this.lang}`], search)) {
            return true;
          }
        }
      }
      return false;
    },
  },
  mounted() {
    this.fetchPlatformData();
  },
};
</script>
