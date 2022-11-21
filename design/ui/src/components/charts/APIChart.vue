<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<i18n lang="yaml" src="@/locales/charts.yaml"></i18n>

<template>
  <LoaderWidget
    v-if="loading || crunchingData"
    :height="height"
    :text="crunchingData ? crunchingText : $t('chart.loading_data')"
    icon-name="fa-cog"
  />
  <div v-else-if="tooMuchData" :style="{ height: height }" id="loading">
    <div>
      <i class="far fa-frown pb-6"></i>
      <div class="infotext">{{ $t("chart.too_much_data") }}</div>
    </div>
  </div>
  <div
    v-else-if="error"
    :style="{ height: height, color: 'orange' }"
    id="loading"
  >
    <div>
      <i class="fa fa-exclamation-triangle pb-6"></i>
      <div class="infotext pb-4 font-weight-light">
        {{ $t("chart.request_error") }}:
      </div>
      <div class="infotext font-weight-bold">{{ error }}</div>
    </div>
  </div>
  <div
    v-else-if="dataRaw.length === 0"
    :style="{ height: height }"
    id="loading"
  >
    <div>
      <i class="far fa-frown" :style="{ marginTop: '36px' }"></i>
      <div class="infotext">{{ $t("chart.no_data") }}</div>
      <v-alert
        v-if="reportedMetrics.length"
        type="info"
        class="mt-8 d-inline-block text-left"
        outlined
        max-width="960px"
      >
        <div>{{ $t("reported_metrics_empty_data_intro") }}</div>
        <div class="my-3 font-weight-bold">
          {{ $t("reported_metrics_empty_data_info") }}
        </div>
        <div v-html="reportedMetricsText"></div>
      </v-alert>
    </div>
  </div>
  <div v-else>
    <v-container class="pa-0" fluid>
      <v-row class="pb-3 pt-4">
        <v-col v-if="showTableToggle" cols="auto" class="pl-5 py-0">
          <v-btn-toggle v-model="tableView" mandatory borderless>
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn :value="false" small v-on="on">
                  <v-icon small>fa fa-chart-bar</v-icon>
                </v-btn>
              </template>
              <span>{{ $t("chart_view.chart") }}</span>
            </v-tooltip>
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn :value="true" small v-on="on">
                  <v-icon small>fa fa-list</v-icon>
                </v-btn>
              </template>
              <span>{{ $t("chart_view.table") }}</span>
            </v-tooltip>
          </v-btn-toggle>
        </v-col>
        <v-col v-if="showYearToYear" cols="auto" class="pl-5 py-0">
          <v-btn-toggle v-model="yearAsSeries" mandatory borderless>
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn :value="false" small v-on="on">
                  <v-icon x-small>fa fa-chart-line</v-icon>
                </v-btn>
              </template>
              <span>{{ $t("x_axis.linear") }}</span>
            </v-tooltip>
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn
                  :value="true"
                  small
                  v-on="on"
                  :disabled="!showYearToYear"
                >
                  <v-icon x-small>fa fa-calendar-alt</v-icon>
                </v-btn>
              </template>
              <span>{{ $t("x_axis.year_months") }}</span>
            </v-tooltip>
          </v-btn-toggle>
        </v-col>
        <v-col v-if="isStackable" cols="auto" class="py-0">
          <v-btn-toggle v-model="doStack" mandatory borderless>
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn :value="false" small v-on="on">
                  <v-icon x-small>fa fa-ellipsis-h</v-icon>
                </v-btn>
              </template>
              <span>{{ $t("stack.no") }}</span>
            </v-tooltip>
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-btn :value="true" small v-on="on">
                  <v-icon x-small>fa fa-layer-group</v-icon>
                </v-btn>
              </template>
              <span>{{ $t("stack.yes") }}</span>
            </v-tooltip>
          </v-btn-toggle>
        </v-col>
        <v-col
          class="pt-1 pb-1 font-weight-normal ml-4 mr-4 text-center"
          :class="showYearToYear ? 'subtitle-parent' : ''"
        >
          <span
            v-if="showYearToYear"
            class="chart-subtitle pt-2 px-5"
            v-text="
              yearAsSeries ? $t('x_axis.year_months') : $t('x_axis.linear')
            "
          ></span>
        </v-col>
        <v-col
          cols="auto"
          shrink
          class="pr-3 pa-0 pt-1"
          v-if="reportedMetrics.length"
        >
          <v-tooltip bottom>
            <template #activator="{ on }">
              <span v-on="on">
                <v-icon color="info">fa-info-circle</v-icon>
              </span>
            </template>
            <strong>{{ $t("reported_metrics_tooltip") }}</strong>
            <div v-html="reportedMetricsText"></div>
            <span v-if="reportedMetrics.length > 1">{{
              $t("reported_metrics_tooltip_many")
            }}</span>
          </v-tooltip>
        </v-col>
      </v-row>
    </v-container>
    <div :style="{ 'min-height': height }" class="pt-4">
      <v-chart
        v-if="!tableView"
        :option="option"
        :style="{ height: height }"
        :update-options="{
          notMerge: ['series'],
          replaceMerge: ['xAxis', 'yAxis'],
        }"
        autoresize
        @click="click"
      >
      </v-chart>

      <ChartDataTable
        :rows="displayData"
        :columns="[shownPrimaryDimension, ...seriesNames]"
        :primary-dimension="shownPrimaryDimension"
        :items-per-page="dashboardChart ? 8 : 12"
        v-else
      >
      </ChartDataTable>
    </div>
    <v-dialog v-model="showCoverageDialog">
      <v-card>
        <v-card-title>Coverage</v-card-title>
        <v-card-text>
          <CoverageMap
            :organization-id="organization"
            :platform-id="platform"
            :report-type-id="reportTypeId"
            :raw-report-type="rawReportType"
            :start-month="dateRangeStart"
            :end-month="dateRangeEnd"
          />
        </v-card-text>
        <v-card-actions class="pb-4 pr-4">
          <v-spacer></v-spacer>
          <v-btn @click="showCoverageDialog = false">{{
            $t("actions.close")
          }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
<script>
import { mapActions, mapGetters, mapState } from "vuex";
import LoaderWidget from "@/components/util/LoaderWidget";
import { pivot } from "@/libs/pivot";
import cancellation from "@/mixins/cancellation";
import ChartDataTable from "../ChartDataTable";
import { padIntegerWithZeros } from "@/libs/numbers";
import { DEFAULT_VCHARTS_COLORS } from "@/libs/charts";
import CoverageMap from "@/components/charts/CoverageMap";

/* vue-echarts */
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, LineChart } from "echarts/charts";
import {
  TooltipComponent,
  LegendComponent,
  GridComponent,
  ToolboxComponent,
  DataZoomComponent,
  MarkLineComponent,
  DatasetComponent,
  VisualMapComponent,
} from "echarts/components";
import VChart from "vue-echarts";

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  ToolboxComponent,
  DataZoomComponent,
  MarkLineComponent,
  DatasetComponent,
  VisualMapComponent,
]);
/* ~vue-echarts */

const months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

export default {
  name: "APIChart",
  mixins: [cancellation],
  components: {
    CoverageMap,
    ChartDataTable,
    LoaderWidget,
    VChart,
  },
  props: {
    type: {
      type: String,
      default: "histogram",
    },
    organization: {
      required: false,
    },
    platform: {
      required: false,
    },
    primaryDimension: {
      required: true,
    },
    secondaryDimension: {
      required: false,
    },
    reportTypeId: {
      required: true,
    },
    title: {
      // id of the title to filter on
      type: Number,
      required: false,
    },
    importBatch: {
      // id of the Batch
      required: false,
      type: Number,
    },
    mduId: {
      // id of the manual data upload
      required: false,
      type: Number,
    },
    dataURLBase: {
      type: String,
      default: "/api/",
    },
    stack: {
      type: Boolean,
      default: false,
    },
    height: {
      default: "400px",
    },
    zoom: {
      type: Boolean,
      default: true,
    },
    ignoreDateRange: {
      type: Boolean,
      default: false,
    },
    orderBy: {},
    showMarkLine: { default: true },
    rawReportType: {
      default: false,
      type: Boolean,
    },
    maxLabelLength: {
      default: 50,
      type: Number,
    },
    showTableToggle: {
      default: true,
      type: Boolean,
    },
    allowYearAsSeries: {
      default: true,
      type: Boolean,
    },
    dashboardChart: {
      default: false,
      type: Boolean,
    },
    metric: {
      default: null,
      type: Number,
    },
    noCoverage: {
      default: false,
      type: Boolean,
    }, // exclude coverage from chart
  },
  data() {
    return {
      dataRaw: [],
      loading: true,
      crunchingData: false,
      reportedMetrics: [],
      tooMuchData: false,
      displayData: [],
      rawDataLength: 0,
      rawData: null,
      out: null,
      tableView: false,
      yearAsSeries: false, // should each year form a separate series?
      error: null,
      doStack: this.stack,
      coverageData: [],
      showCoverageDialog: false,
    };
  },
  computed: {
    ...mapState({
      user: "user",
    }),
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
      selectedOrganization: "selectedOrganization",
      enableDataCoverage: "enableDataCoverage",
    }),
    monthNames() {
      return months.map((item) =>
        new Date(2020, item - 1, 1).toLocaleString(this.$i18n.locale, {
          month: "short",
        })
      );
    },
    dataURL() {
      if (!this.user) {
        return null;
      }
      let reportTypePart = ""; // used do decide if report type should be part of the URL
      if (this.reportTypeId && this.reportTypeId !== -1) {
        reportTypePart = `${this.reportTypeId}/`;
      }
      let urlStart = this.rawReportType ? "chart-data-raw" : "chart-data";
      let url = `${this.dataURLBase}${urlStart}/${reportTypePart}?prim_dim=${this.primaryDimension}`;
      if (!this.ignoreDateRange) {
        url += `&start=${this.dateRangeStart}&end=${this.dateRangeEnd}`;
      }
      if (this.secondaryDimension) {
        url += `&sec_dim=${this.secondaryDimension}`;
      }
      if (this.platform) url += `&platform=${this.platform}`;
      if (this.organization) url += `&organization=${this.organization}`;
      if (this.title) url += `&target=${this.title}`;
      if (this.importBatch) url += `&import_batch=${this.importBatch}`;
      if (this.mduId) url += `&mdu=${this.mduId}`;
      if (this.dashboardChart) {
        url += "&dashboard=true";
      }
      if (this.metric) {
        url += `&metric=${this.metric}`;
      }
      return url;
    },
    markLine() {
      if (
        this.shownPrimaryDimension === "organization" &&
        this.showMarkLine &&
        this.organizationRow !== null
      ) {
        return {
          silent: true,
          symbol: ["none", "none"],
          data: [
            {
              name: "me",
              yAxis: this.organizationRow,
              lineStyle: {
                color: "#aa0010",
                type: "solid",
                width: 1,
              },
              label: {
                formatter: this.$t("chart.my_org"),
                position: "middle",
              },
            },
          ],
        };
      }
      return {};
    },
    organizationRow() {
      if (!this.selectedOrganization) {
        return null;
      }
      return this.xValues.findIndex(
        (value) => value === this.selectedOrganization.name
      );
    },
    dataYears() {
      let yearSet = new Set();
      this.rawData.forEach((item) => yearSet.add(item.date.substring(0, 4)));
      return [...yearSet].sort();
    },
    xAxis() {
      if (this.regroupByYear) {
        const years = this.dataYears;
        let axis1 = [];
        for (let month of months) {
          for (let year of years) {
            axis1.push(`${month.toString().padStart(2, "0")}-${year}`);
          }
        }
        return [
          {
            data: axis1,
            axisLabel: {
              show: false,
            },
          },
          {
            data: this.monthNames,
            position: "top",
            offset: -30,
            splitLine: {
              show: true,
              lineStyle: {
                color: "#cccccc",
                width: 1,
              },
            },
            splitArea: {
              show: true,
              areaStyle: {
                color: ["#e0efff88", "#fffdee88"],
              },
            },
          },
          {
            data: this.monthNames,
            position: "bottom",
            axisTick: {
              show: true,
              inside: false,
              length: 10,
              lineStyle: {
                color: "#cccccc",
              },
            },
          },
        ];
      } else if (this.type === "bar") {
        // prepare some pieces
        return {
          type: "value",
        };
      } else {
        return {
          type: "category",
          data: this.xValues,
        };
      }
    },
    yAxis() {
      if (this.type === "bar") {
        return {
          type: "category",
          data: this.xValues,
          axisLabel: {
            width: 250,
            fontSize: this.xValues.length > 20 ? 10 : 12, // smaller font for many values
            overflow: "truncate",
          },
        };
      } else {
        if (this.coverageData.length) {
          return [
            {
              type: "value",
            },
            {
              name: this.$t("series.data_coverage"),
              type: "value",
              min: 0,
              max: 100,
              splitLine: {
                show: false,
              },
              axisTick: {
                show: true,
              },
              axisLine: {
                show: true,
              },
            },
          ];
        } else {
          return {
            type: "value",
          };
        }
      }
    },
    toolbox() {
      return {
        feature: {
          saveAsImage: {
            show: true,
            title: this.$t("chart.toolbox.save_as_image"),
            excludeComponents: ["toolbox", "dataZoom"],
          },
          myExportData: {
            show: true,
            title: this.$t("chart.toolbox.export_csv"),
            icon: "path://m 434.57178,114.29929 -83.882,-83.882005 c -9.00169,-9.001761 -21.21063,-14.058933 -33.941,-14.059 H 48.630782 c -26.51,0 -47.9999996,21.49 -47.9999996,48 V 416.35829 c 0,26.51 21.4899996,48 47.9999996,48 H 400.63078 c 26.51,0 48,-21.49 48,-48 v -268.118 c -7e-5,-12.73037 -5.05724,-24.93931 -14.059,-33.941 z m -161.941,-49.941005 v 80.000005 h -128 V 64.358285 Z m -48,152.000005 c -48.523,0 -88,39.477 -88,88 0,48.523 39.477,88 88,88 48.523,0 88,-39.477 88,-88 0,-48.523 -39.477,-88 -88,-88 z",
            onclick: (function (that) {
              return function () {
                window.open(that.dataURL + "&format=csv");
              };
            })(this),
          },
        },
      };
    },
    dataZoom() {
      if (this.zoom && !this.regroupByYear) {
        return [
          {
            type: "slider",
            start: 0,
            end: 100,
            yAxisIndex: this.type === "bar" ? 0 : null,
          },
        ];
      } else {
        return [];
      }
    },
    reportedMetricsText() {
      if (this.reportedMetrics.length > 0) {
        let inside = this.reportedMetrics
          .map((metric) =>
            (metric.name || metric.short_name).replace(/_/g, " ")
          )
          .join("</li><li>");
        return `<ul><li>${inside}</li></ul>`;
      } else {
        return "";
      }
    },
    crunchingText() {
      return this.$tc("chart.crunching_records", this.rawDataLength);
    },
    regroupByYear() {
      return this.yearAsSeries && this.primaryDimension === "date";
    },
    shownPrimaryDimension() {
      if (this.regroupByYear) return "month";
      return this.primaryDimension;
    },
    shownSecondaryDimension() {
      return this.secondaryDimension;
    },
    showYearToYear() {
      return this.allowYearAsSeries && this.primaryDimension === "date";
    },
    // new stuff for vue-echarts starts here
    option() {
      let coverageSeries = [];
      let visualMap = {};
      if (this.coverageData.length && !this.regroupByYear) {
        coverageSeries = [
          {
            name: this.$t("series.data_coverage"),
            type: "line",
            data: this.coverageData.map((item) => item.ratio * 100),
            yAxisIndex: 1,
            tooltip: {
              valueFormatter: (value) => `${value.toFixed(1)} %`,
            },
          },
        ];
        visualMap = {
          visualMap: {
            type: "continuous",
            show: false, // do not show the slider widget
            min: 0,
            max: 100,
            range: [90, 100],
            seriesIndex: 0,
            inRange: {
              symbol: "diamond",
              color: [
                "#ff7777",
                "#ffbb66",
                "#ffbb66",
                "#ffbb66",
                "#ffcc77",
                "#ffcc77",
                "#ffcc77",
                "#cccc77",
                "#cccc77",
                "#cccc77",
                "#cccc77",
                "#77cc77",
              ],
              symbolSize: [5, 3],
              opacity: [0.5, 0.5],
            },
            outOfRange: {
              symbol: "diamond",
              color: ["#ff7777", "#ff7777", "#ffbb66", "#ffcc77"],
              symbolSize: [10, 6],
              opacity: [1, 0.5],
            },
          },
        };
      }

      // the returned object itself
      // type "bar" means horizontal bars - taken from the v-charts library
      return {
        // more space for names when bars are horizontal
        grid: this.type === "bar" ? { left: "25%" } : {},
        xAxis: this.xAxis,
        yAxis: this.yAxis,
        dataset: {
          source: this.displayData,
          dimensions: [this.shownPrimaryDimension, ...this.seriesNames],
        },
        series: [
          ...coverageSeries,
          ...this.seriesNames.map((series, index) => ({
            id: series,
            name: this.shownSecondaryDimension
              ? series
              : this.$t("chart.count"),
            type: "bar",
            stack: this.doStack ? "all" : series,
            // only add markline to the first series
            markLine: index === 0 ? this.markLine : {},
          })),
        ],
        tooltip: {
          trigger: "axis",
          axisPointer: {
            type: "shadow",
          },
        },
        toolbox: this.toolbox,
        dataZoom: this.dataZoom,
        legend: {
          // checkmarks as icons for the series
          icon: "path://M 592,480 H 240 c -26.51,0 -48,-21.49 -48,-48 V 80 c 0,-26.51 21.49,-48 48,-48 h 352 c 26.51,0 48,21.49 48,48 v 352 c 0,26.51 -21.49,48 -48,48 z m -204.686,-98.059 184,-184 c 6.248,-6.248 6.248,-16.379 0,-22.627 l -22.627,-22.627 c -6.248,-6.248 -16.379,-6.249 -22.628,0 L 376,302.745 305.941,232.686 c -6.248,-6.248 -16.379,-6.248 -22.628,0 l -22.627,22.627 c -6.248,6.248 -6.248,16.379 0,22.627 l 104,104 c 6.249,6.25 16.379,6.25 22.628,0 z",
          itemWidth: 16,
          itemGap: 16,
          itemHeight: 16,
        },
        color: DEFAULT_VCHARTS_COLORS,
        ...visualMap,
      };
    },
    xValues() {
      if (this.shownPrimaryDimension === "date" && this.coverageData.length) {
        return this.coverageData.map((item) => item.date.substring(0, 7));
      }
      return this.displayData.map((item) => item[this.primaryDimension]);
    },
    seriesNames() {
      if (this.loading) return [];
      if (this.dataRaw.length === 0) return [];
      if (this.shownSecondaryDimension) {
        let rows = this.displayData;
        return [
          ...Object.keys(rows[0]).filter(
            (item) => item !== this.shownPrimaryDimension
          ),
        ];
      } else {
        return ["count"];
      }
    },
    isStackable() {
      return (
        (this.type === "bar" || this.type === "histogram") &&
        this.shownSecondaryDimension
      );
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async ingestData(rawData) {
      // prepare the data
      this.crunchingData = true;
      // reformat date value to exclude the day component
      // the check for dict.date.substring is there because the date may be a year as a number
      // in some cases
      rawData = rawData.map((dict) => {
        if ("date" in dict && dict.date.substring)
          dict["date"] = dict.date.substring(0, 7);
        return dict;
      });
      // truncate long labels
      this.dataRaw = rawData.map((dict) => {
        let val1 = String(dict[this.primaryDimension]);
        if (val1.length > this.maxLabelLength + 3) {
          dict[this.primaryDimension] =
            val1.substring(0, this.maxLabelLength) + "\u2026";
        }
        if (this.secondaryDimension) {
          let val2 = String(dict[this.secondaryDimension]);
          if (val2.length > this.maxLabelLength + 3) {
            dict[this.secondaryDimension] =
              val2.substring(0, this.maxLabelLength) + "\u2026";
          }
        }
        return dict;
      });
      // extract years when necessary
      if (this.regroupByYear) {
        this.dataRaw.forEach((dict) => {
          dict["year"] = dict["date"].substring(0, 4);
          dict["month"] = dict["date"].substring(5, 7) + "-" + dict.year;
        });
      }
      // secondary dimension
      if (this.shownSecondaryDimension) {
        let now = new Date();
        let out = this.pivot();
        this.out = out;
        console.log("pivot ended", new Date() - now);
        if (this.orderBy) {
          // NOTE: order by sum of values - it does not matter how is the orderBy called
          function sumNonPrimary(rec) {
            // remove value of primary dimension, sum the rest
            return Object.entries(rec)
              .filter(([a, b]) => a !== this.shownPrimaryDimension)
              .map(([a, b]) => b)
              .reduce((x, y) => x + y);
          }

          let sum = sumNonPrimary.bind(this);
          out.sort((a, b) => sum(a) - sum(b));
        }
        if (this.regroupByYear && this.shownPrimaryDimension === "month") {
          // we need to ensure that months for which there are no data are properly populated
          // by empty records, because the display depends on it
          let filled = [];
          const keys = [...Object.keys(out[0])];
          for (let month of months) {
            for (let year of this.dataYears) {
              let found = false;
              const monthStr = `${padIntegerWithZeros(month)}-${year}`;
              for (let rec of out) {
                if (rec.month === monthStr) {
                  filled.push(rec);
                  found = true;
                  break;
                }
              }
              if (!found) {
                let rec = { month: monthStr };
                keys.forEach((key) =>
                  key !== "month" ? (rec[key] = 0) : null
                );
                filled.push(rec);
              }
            }
          }
          out = filled;
          // out.sort((a, b) => a.month > b.month);
        }
        this.displayData = out;
      } else {
        // no secondary dimension
        if (this.orderBy) {
          // order by
          this.dataRaw.sort((a, b) => {
            return a[this.orderBy] - b[this.orderBy];
          });
        }
        this.displayData = this.dataRaw;
        this.displayData.forEach((item) => {
          if (item[this.primaryDimension] === null) {
            item[this.primaryDimension] = this.$t("labels.empty_value");
          }
        });
      }
      this.crunchingData = false;
    },
    async loadData() {
      if (!this.dataURL) return;

      this.dataRaw = [];
      this.tooMuchData = false;
      this.error = null;

      this.loading = true;
      const { response, error } = await this.http({ url: this.dataURL });
      this.loading = false;
      this.error = error;

      if (!response) return;
      if (response.data.too_much_data) {
        this.tooMuchData = true;
        return;
      }
      this.crunchingData = true;
      this.rawDataLength = response.data.data.length;
      this.rawData = response.data.data;
      this.reportedMetrics = response.data.reported_metrics;
      // we use timeout to give the interface time to redraw
      setTimeout(async () => await this.ingestData(response.data.data), 10);
    },
    async loadCoverageData() {
      if (this.enableDataCoverage && this.shownPrimaryDimension === "date") {
        let params = {
          start_date: this.dateRangeStart,
          end_date: this.dateRangeEnd,
        };
        // the reportTypeId can be either of report type or of report view
        if (this.rawReportType) {
          params["report_type"] = this.reportTypeId;
        } else {
          params["report_view"] = this.reportTypeId;
        }
        if (this.platform) {
          params["platform"] = this.platform;
        }
        if (this.organization && this.organization !== -1) {
          params["organization"] = this.organization;
        }
        const { response, error } = await this.http({
          url: "/api/import-batch/data-coverage/",
          params: params,
        });
        if (!error) {
          this.coverageData = response.data;
        } else {
          this.coverageData = [];
        }
      } else {
        this.coverageData = [];
      }
    },
    pivot() {
      return pivot(
        this.dataRaw,
        this.shownPrimaryDimension,
        this.shownSecondaryDimension,
        "count"
      );
    },
    click() {
      if (this.coverageData.length) {
        this.showCoverageDialog = true;
      }
    },
  },
  mounted() {
    this.loadData();
    if (!this.noCoverage) {
      this.loadCoverageData();
    }
  },
  watch: {
    dataURL() {
      this.loadData();
      if (!this.noCoverage) {
        this.loadCoverageData();
      }
    },
    yearAsSeries() {
      this.ingestData(this.rawData);
    },
    stack() {
      this.doStack = this.stack;
    },
  },
};
</script>
<style scoped lang="scss">
.accomp-text {
  font-size: 125%;
  text-align: center;

  &.left {
    padding-right: 0;
  }

  &.right {
    padding-left: 0;
  }
}

.chart {
  margin: 1rem;
}

#loading {
  font-size: 60px;
  color: #1db79a88;
  text-align: center;

  i.fa,
  i.far {
    margin-top: 100px;
  }

  div.infotext {
    font-size: 26px;
  }
}

.chart-subtitle {
  color: #777777;
  letter-spacing: 1.5px;
}

.subtitle-parent {
  border-bottom: solid 1px #dddddd;
  border-top: solid 1px #dddddd;
}
</style>
