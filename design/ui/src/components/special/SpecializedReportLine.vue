<i18n lang="yaml" src="@/locales/common.yaml" />
<i18n lang="yaml">
en:
  main_report: Main Report
  fallback_report: Fallback Report

cs:
  main_report: Hlavní report
  fallback_report: Záložní report
</i18n>

<template>
  <v-expansion-panel>
    <v-expansion-panel-header class="justify-space-between">
      <h3 class="name flex-grow-0">
        {{ name }}
        <v-tooltip bottom v-if="implementationNote" max-width="640px">
          <template #activator="{ on }">
            <v-icon color="info" small v-on="on">fa fa-info-circle</v-icon>
          </template>
          <span>{{ implementationNote }}</span>
        </v-tooltip>
      </h3>
      <h4 class="description">{{ description }}</h4>
      <h2 class="total-value flex-grow-0 me-4">
        <v-progress-circular v-if="loading" indeterminate />
        <span v-else-if="allReady">{{ formatInteger(total) }}</span>
        <span v-else>-</span>
      </h2>
    </v-expansion-panel-header>
    <v-expansion-panel-content>
      <v-sheet>
        <table class="overview">
          <tr>
            <th>{{ $t("main_report") }}</th>
            <td>{{ mainReportDefinition.reportType }}</td>
            <td>
              <ReportPartParams :definition="mainReportDefinition" />
            </td>
          </tr>

          <tr>
            <th>{{ $t("fallback_report") }}</th>
            <td v-if="fallbackReportDefinition">
              {{ fallbackReportDefinition.reportType }}
              {{
                subtractedFallbackReportDefinition
                  ? "&minus;" + subtractedFallbackReportDefinition.reportType
                  : ""
              }}
            </td>
            <td v-if="fallbackReportDefinition">
              <ReportPartParams :definition="fallbackReportDefinition" />
            </td>
          </tr>
        </table>
        <v-checkbox v-model="nonZeroOnly" label="Non-zero rows only" />
      </v-sheet>
      <v-data-table
        v-if="showDetail && data.length > 0"
        :items="formattedData"
        item-key="pk"
        :headers="tableColumns"
        sort-by="total"
        sort-desc
      >
        <template #item.total="{ item }">
          {{ formatInteger(item.total) }}
        </template>
        <template #item.used_report_type="{ item }">
          <span
            :class="
              fallbackReportDefinition &&
              item.used_report_type === fallbackReportDefinition.reportType
                ? 'orange--text'
                : 'green--text'
            "
          >
            {{ item.used_report_type }}
          </span>
        </template>
      </v-data-table>
    </v-expansion-panel-content>
  </v-expansion-panel>
</template>
<script>
import cancellation from "@/mixins/cancellation";
import { mapGetters } from "vuex";
import { formatInteger } from "@/libs/numbers";
import cloneDeep from "lodash/cloneDeep";
import ReportPartParams from "@/components/special/ReportPartParams";

export default {
  name: "SpecializedReportLine",
  components: { ReportPartParams },
  mixins: [cancellation],

  props: {
    name: {
      type: String,
      required: false,
    },
    description: {
      type: String,
      required: false,
    },
    mainReportDefinition: {
      type: Object,
      required: true,
    },
    fallbackReportDefinition: {
      type: Object,
      required: false,
    },
    subtractedFallbackReportDefinition: {
      // if given, data from this report will be subtracted from the fallback report
      type: Object,
      required: false,
    },
    implementationNote: {
      type: String,
      required: false,
    },
    data: {
      type: Array,
      required: false,
    },
    loading: {
      type: Boolean,
      required: false,
    },
  },

  data() {
    return {
      showDetail: true,
      nonZeroOnly: true,
    };
  },

  computed: {
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeExplicitEndText",
      organizationObj: "selectedOrganization",
    }),
    allReady() {
      return this.data.length > 0;
    },
    organization() {
      return this.organizationObj.pk !== -1 ? this.organizationObj.pk : null;
    },
    dateRange() {
      if (this.data.length > 0) {
        return Object.keys(this.data[0].monthly_data);
      }
      return [];
    },
    tableColumns() {
      return [
        {
          text: this.$t("labels.platform"),
          value: "primary_obj",
          align: "left",
          sortable: true,
        },
        {
          text: this.$t("labels.source"),
          value: "used_report_type",
          sortable: true,
        },
        {
          text: this.$t("labels.total"),
          value: "total",
          align: "right",
          sortable: true,
        },
        ...this.dateRange.map((date) => {
          return {
            text: date,
            value: `monthly_data.${date}`,
            align: "right",
            sortable: true,
            cellClass: "font-weight-light",
          };
        }),
      ];
    },
    finalData() {
      if (this.nonZeroOnly) {
        return this.data.filter((r) => r.total > 0);
      }
      return this.data;
    },
    formattedData() {
      let data = cloneDeep(this.finalData);
      data.forEach((r) => {
        this.dateRange.forEach((date) => {
          r.monthly_data[date] = formatInteger(r.monthly_data[date]);
        });
      });
      return data;
    },
    total() {
      return this.finalData.reduce((ac, rec) => ac + rec.total, 0);
    },
  },

  methods: {
    formatInteger,
  },
};
</script>

<style lang="scss" scoped>
.description {
  font-weight: normal;
}
.name {
  min-width: 16rem;
  margin-right: 1.5rem;
}
.total-value {
  &.trouble {
    font-size: 1rem;
    font-weight: normal;
    font-style: italic;
  }
}
</style>
