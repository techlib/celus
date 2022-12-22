<template>
  <v-expansion-panel>
    <v-expansion-panel-header class="justify-space-between">
      <h3 class="name flex-grow-0">{{ name }}</h3>
      <h4 class="description">{{ description }}</h4>
      <h2 v-if="dateRangeStart" class="total-value flex-grow-0 me-4">
        <span v-if="allReady">{{ formatInteger(total) }}</span>
        <v-progress-circular v-else indeterminate />
      </h2>
      <h2 v-else class="total-value flex-grow-0 me-4 trouble">
        <v-tooltip bottom>
          <template #activator="{ on }">
            <span v-on="on">
              <v-icon small color="warning" class="me-2"
                >fa-exclamation-triangle</v-icon
              >
              Date range start missing
            </span>
          </template>
          Select a date range with an explicit start date.
        </v-tooltip>
      </h2>
    </v-expansion-panel-header>
    <v-expansion-panel-content>
      <v-sheet v-if="dateRangeStart">
        <table class="overview">
          <tr>
            <th>Source Report</th>
            <td class="pe-2">
              {{ mainReportDefinition.reportType.short_name }}
            </td>
            <td class="px-2 font-weight-light">
              metric={{ mainReportDefinition.metric }}
            </td>
            <td class="px-2 font-weight-light">
              <span
                v-for="(value, name, index) in mainReportDefinition.filters"
                class="me-2"
                :style="{ color: palette[index % palette.length] }"
                :key="name"
              >
                {{ name }}={{ value.toString() }}
              </span>
            </td>
          </tr>
          <tr>
            <th>Fallback Report</th>
            <td v-if="fallbackReportDefinition">
              {{ fallbackReportDefinition.reportType.short_name }}
              <span v-if="subtractFallbackReportDefinition"
                >&minus;
                {{
                  subtractFallbackReportDefinition.reportType.short_name
                }}</span
              >
            </td>
            <td
              v-if="fallbackReportDefinition && fallbackReportDefinition.metric"
              class="px-2 font-weight-light"
            >
              metric={{ fallbackReportDefinition.metric }}
            </td>
            <td v-if="fallbackReportDefinition" class="px-2 font-weight-light">
              <span
                v-for="(value, name, index) in fallbackReportDefinition.filters"
                class="me-2"
                :style="{ color: palette[index % palette.length] }"
                :key="name"
              >
                {{ name }}={{ value }}
              </span>
            </td>
          </tr>
        </table>
        <v-checkbox v-model="nonZeroOnly" label="Non-zero rows only" />
      </v-sheet>
      <v-data-table
        v-if="showDetail && allReady"
        :items="formattedData"
        item-key="pk"
        :headers="tableColumns"
        sort-by="_total"
        sort-desc
      >
        <template #item._fallback="{ item }">
          <span :class="item._fallback ? 'orange--text' : 'green--text'">
            {{
              item._fallback
                ? fallbackReport.reportType.short_name
                : mainReport.reportType.short_name
            }}
          </span>
        </template>
        <template #item._total="{ item }">
          {{ formatInteger(item._total) }}
        </template>
      </v-data-table>
    </v-expansion-panel-content>
  </v-expansion-panel>
</template>
<script>
import cancellation from "@/mixins/cancellation";
import { mapGetters } from "vuex";
import { monthsBetween, ymDateFormat } from "@/libs/dates";
import { formatInteger } from "@/libs/numbers";
import Report from "@/libs/reporting-interface";
import idTranslation from "@/libs/id-translation";
import cloneDeep from "lodash/cloneDeep";

export default {
  name: "SpanishReportLine",

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
    subtractFallbackReportDefinition: {
      // if given, data from this report will be subtracted from the fallback report
      type: Object,
      required: false,
    },
  },

  data() {
    return {
      allReady: false,
      showDetail: true,
      mainReport: null,
      fallbackReport: null,
      subtractFallbackReport: null,
      platformTranslator: new idTranslation("/api/platform/"),
      nonZeroOnly: true,
      palette: [
        "#009900",
        "#990099",
        "#0080FF",
        "#FF0080",
        "#000099",
        "#8000FF",
      ],
    };
  },

  computed: {
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeExplicitEndText",
      organizationObj: "selectedOrganization",
    }),
    canCompute() {
      return !!this.dateRangeStart && !!this.dateRangeEnd;
    },
    organization() {
      return this.organizationObj.pk !== -1 ? this.organizationObj.pk : null;
    },
    dateRangeStr() {
      // this is here just to make the watcher easier to write
      return `${this.dateRangeStart} - ${this.dateRangeEnd}`;
    },
    dateRange() {
      if (!this.canCompute) {
        return [];
      }
      // returns the months between the first and last date as set in the app preferences
      return monthsBetween(this.dateRangeStart, this.dateRangeEnd).map(
        ymDateFormat
      );
    },
    tableColumns() {
      return [
        {
          text: "Platform",
          value: "platform.short_name",
          align: "left",
          sortable: true,
          //cellClass: "font-weight-bold",
        },
        // {
        //   text: "Platform ID",
        //   value: "pk",
        //   align: "right",
        //   sortable: true,
        // },
        {
          text: "Source",
          value: "_fallback",
          sortable: true,
        },
        {
          text: "Total",
          value: "_total",
          align: "right",
          sortable: true,
        },
        ...this.dateRange.map((date) => {
          return {
            text: date,
            value: `grp-${date}-01`,
            align: "right",
            sortable: true,
            cellClass: "font-weight-light",
          };
        }),
      ];
    },
    finalData() {
      // go over the main report data and add the fallback report data
      // if the platform does not have any data in the main report
      // if subtractFallbackReportDefinition is given, subtract the data from
      // the fallback report
      if (!this.canCompute) {
        return [];
      }
      let output = [];
      if (this.fallbackReport) {
        this.mainReport.data.forEach((row) => {
          if (row._total > 0) {
            output.push(row);
          } else {
            // find the fallback report row with the same pk
            const fallbackRow = this.fallbackReport.data.find(
              (r) => r.pk === row.pk
            );
            if (fallbackRow && fallbackRow._total > 0) {
              let fallback = { ...fallbackRow };
              if (this.subtractFallbackReportDefinition) {
                // subtract the fallback report data from the fallback row
                this.subtractFallbackReport.data.forEach((subRow) => {
                  if (subRow.pk === row.pk) {
                    this.dateRange.forEach((date) => {
                      fallback[`grp-${date}-01`] -=
                        subRow[`grp-${date}-01`] || 0;
                    });
                  }
                });
              }
              fallback._fallback = true;
              output.push(fallback);
            } else {
              output.push(row);
            }
          }
        });
      }
      output.forEach((r) => {
        r.platform = this.platformTranslator.translateKey(r.pk);
      });
      if (this.nonZeroOnly) {
        output = output.filter((r) => r._total > 0);
      }
      return output;
    },
    formattedData() {
      let data = cloneDeep(this.finalData);
      data.forEach((r) => {
        this.dateRange.forEach((date) => {
          r[`grp-${date}-01`] = formatInteger(r[`grp-${date}-01`]);
        });
      });
      return data;
    },
    total() {
      let total = 0;
      this.finalData.forEach((item) => {
        this.dateRange.forEach((date) => {
          total += item[`grp-${date}-01`] ?? 0;
        });
      });
      return total;
    },
  },

  methods: {
    formatInteger,
    async prepareTranslator() {
      if (this.mainReport.data.length > 0) {
        const ids = this.mainReport.data.map((r) => r.pk);
        await this.platformTranslator.prepareTranslation(ids);
      }
    },
  },

  async mounted() {
    let promises = [];
    this.mainReport = new Report(
      this.$router,
      this.http,
      this.mainReportDefinition.reportType,
      this.mainReportDefinition.metric,
      this.mainReportDefinition.filters,
      this.dateRangeStart,
      this.dateRangeEnd,
      this.organization
    );
    if (this.fallbackReportDefinition) {
      this.fallbackReport = new Report(
        this.$router,
        this.http,
        this.fallbackReportDefinition.reportType,
        this.fallbackReportDefinition.metric,
        this.fallbackReportDefinition.filters,
        this.dateRangeStart,
        this.dateRangeEnd,
        this.organization
      );
      promises.push(this.fallbackReport.loadAllData());
    }
    if (this.subtractFallbackReportDefinition) {
      this.subtractFallbackReport = new Report(
        this.$router,
        this.http,
        this.subtractFallbackReportDefinition.reportType,
        this.subtractFallbackReportDefinition.metric,
        this.subtractFallbackReportDefinition.filters,
        this.dateRangeStart,
        this.dateRangeEnd,
        this.organization
      );
      promises.push(this.subtractFallbackReport.loadAllData());
    }
    promises.push(this.mainReport.loadAllData());
    await Promise.all(promises);
    await this.prepareTranslator();
    this.allReady = true;
  },

  watch: {
    async dateRangeStr() {
      let promises = [];
      promises.push(
        this.mainReport.changeDateRange(this.dateRangeStart, this.dateRangeEnd)
      );
      if (this.fallbackReport) {
        promises.push(
          this.fallbackReport.changeDateRange(
            this.dateRangeStart,
            this.dateRangeEnd
          )
        );
      }
      if (this.subtractFallbackReport) {
        promises.push(
          this.subtractFallbackReport.changeDateRange(
            this.dateRangeStart,
            this.dateRangeEnd
          )
        );
      }
      this.allReady = false;
      try {
        await Promise.all(promises);
      } finally {
        this.allReady = true;
      }
    },
    async organization() {
      let promises = [];
      promises.push(this.mainReport.changeOrganizationId(this.organization));
      if (this.fallbackReport) {
        promises.push(
          this.fallbackReport.changeOrganizationId(this.organization)
        );
      }
      if (this.subtractFallbackReport) {
        promises.push(
          this.subtractFallbackReport.changeOrganizationId(this.organization)
        );
      }
      this.allReady = false;
      try {
        await Promise.all(promises);
      } finally {
        this.allReady = true;
      }
    },
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
