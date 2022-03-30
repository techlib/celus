<i18n lang="yaml" src="../locales/common.yaml"></i18n>
<i18n lang="yaml">
en:
  labels:
    reports: Reports
    report_types: Report types
    metrics: Metrics
    target_metrics: Target metrics
    interest_groups: Interest groups

cs:
  labels:
    reports: Reporty
    report_types: Typy reportů
    metrics: Metriky
    target_metrics: Cílové metriky
    interest_groups: Skupiny zájmu
</i18n>

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
    </template>

    <template #expanded-item="{ headers, item }">
      <td
        :colspan="headers.length"
        v-if="item.interest_metric_set.length > 0"
        class="pa-2"
      >
        <v-sheet class="pl-8">
          <v-simple-table class="ml-8 font-weight-light" dense>
            <thead>
              <tr>
                <th v-text="$t('labels.interest_type')"></th>
                <th v-text="$t('labels.source_metric')"></th>
                <th>
                  {{ $t("labels.interest_metric") }}
                  <v-tooltip bottom>
                    <template #activator="{ on }">
                      <v-icon color="info" small v-on="on"
                        >fa fa-info-circle</v-icon
                      >
                    </template>
                    {{ $t("tt.interest_metric") }}
                  </v-tooltip>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(metric, index) in item.interest_metric_set"
                :key="index"
              >
                <td>
                  {{ metric.interest_group.name }}
                </td>
                <td>{{ metric.metric.short_name }}</td>
                <td v-if="metric.target_metric" class="font-italic">
                  {{ metric.target_metric.name }}
                </td>
                <td v-else>
                  {{ metric.metric.short_name }}
                </td>
              </tr>
            </tbody>
          </v-simple-table>
        </v-sheet>
      </td>
    </template>

            <template v-slot:[`item.short_name`]="{ item }">
              <ReportChip :report="item"></ReportChip>
            </template>

            <template v-slot:[`item.metrics`]="{ item }">
              <MetricChip
                v-for="metric in item.interest_metric_set.flatMap((m) =>
                  m.metric.short_name ? [m.metric] : []
                )"
                :key="metric.pk"
                :lang="lang"
                :metric="metric"
              />
            </template>

            <template v-slot:[`item.target_metrics`]="{ item }">
              {{
                item.interest_metric_set
                  .flatMap((m) =>
                    m.target_metric ? [m.target_metric.name] : []
                  )
                  .join(", ")
              }}
            </template>

            <template v-slot:[`item.interest_groups`]="{ item }">
              {{
                Array.from(
                  new Set(
                    item.interest_metric_set.flatMap((m) =>
                      m.interest_group ? [m.interest_group.name] : []
                    )
                  )
                ).join(", ")
              }}
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
  name: "InterestOverviewMetrics",

  mixins: [cancellation],

  components: { MetricChip, ReportChip },

  data() {
    return {
      items: [],
      expanded: [],
      search: "",
      loading: false,
    };
  },
  computed: {
    lang() {
      return this.$store.state.appLanguage || "en";
    },
    headers() {
      return [
        {
          text: this.$i18n.t("labels.report_types"),
          value: "short_name",
        },
        {
          text: this.$i18n.t("labels.metrics"),
          value: "metrics",
        },
        {
          text: this.$i18n.t("labels.target_metrics"),
          value: "target_metrics",
        },
        {
          text: this.$i18n.t("labels.interest_groups"),
          value: "interest_groups",
        },
        { text: "", value: "data-table-expand" },
      ];
    },
  },
  methods: {
    async fetchReportData() {
      const url = "api/report-interest-metric/";
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
      for (const im of item.interest_metric_set) {
        if (match(im.metric.short_name, search)) {
          return true;
        }
        if (match(im.metric[`name_${this.lang}`], search)) {
          return true;
        }
        if (!!im.target_metric && match(im.target_metric.short_name, search)) {
          return true;
        }
        if (
          !!im.target_metric &&
          match(im.target_metric[`name_${this.lang}`], search)
        ) {
          return true;
        }
        if (!!im.interest_group && match(im.interest_group.name, search)) {
          return true;
        }
      }
      return false;
    },
  },
  mounted() {
    this.fetchReportData();
  },
};
</script>
