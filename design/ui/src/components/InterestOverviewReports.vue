<i18n lang="yaml" src="../locales/common.yaml"></i18n>

<template>
  <v-card flat>
    <v-card-text>
      <v-row>
        <v-spacer></v-spacer>
        <v-col cols="4">
          <v-text-field
            v-model="search"
            append-icon="fa-search"
            :label="$t('labels.search')"
            single-line
            hide-details
          >
          </v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-data-table
            :items="items"
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
            <template v-slot:expanded-item="{ headers, item }">
              <td
                :colspan="headers.length"
                v-if="item.interest_reports.length > 0"
              >
                <v-list-item
                  v-for="report in item.interest_reports"
                  :key="report.pk"
                >
                  <v-list-item-content>
                    <v-list-item-title>
                      {{ report.short_name }}
                      <span class="font-weight-thin">
                        {{ report[`name_${lang}`] }}
                      </span>
                    </v-list-item-title>
                    <v-list-item-subtitle :key="rerenderMetrics">
                      <MetricChip
                        v-for="im in report.interest_metric_set"
                        :key="im.metric.pk"
                        :lang="lang"
                        :metric="im.metric"
                      />
                    </v-list-item-subtitle>
                  </v-list-item-content>
                </v-list-item>
              </td>
            </template>
            <template v-slot:[`item.reports`]="{ item }">
              <ReportChip
                v-for="(report, index) in item.interest_reports"
                :key="index"
                :report="report"
              >
              </ReportChip>
            </template>
            <template v-slot:[`item.actions`]="{ item }">
              <v-icon small class="mr-2" @click="editItem(item)"
                >fas fa-pen</v-icon
              >
            </template>
          </v-data-table>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script>
import ReportChip from "@/components/reporting/ReportChip";
import MetricChip from "@/components/reporting/MetricChip";
import cancellation from "@/mixins/cancellation";

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
    };
  },
  computed: {
    lang() {
      return this.$store.state.appLanguage || "en";
    },
    headers() {
      return [
        {
          text: this.$i18n.t("platform"),
          value: "name",
        },
        {
          text: this.$i18n.t("labels.report_type"),
          value: "reports",
        },
        { text: "", value: "data-table-expand" },
      ];
    },
  },
  methods: {
    async fetchPlatformData() {
      const url = "api/platform-interest-report/";
      this.loading = true;
      const { response } = await this.http({ url });
      this.loading = false;
      if (response) this.items = response.data;
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
