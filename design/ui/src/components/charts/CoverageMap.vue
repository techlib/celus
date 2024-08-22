<i18n lang="yaml">
en:
  only_good_below: 100 % coverage below this line

cs:
  only_good_below: Pouze 100 % pokrytí pod touto čárou
</i18n>

<template>
  <v-container fluid>
    <v-row no-gutters>
      <v-col :cols="12">
        <LoaderWidget v-if="loading" />
        <div
          v-else-if="coverageData.length > 0"
          :style="{ height: height + 'px' }"
        >
          <v-chart :option="option" @click="onClick" autoresize />
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import cancellation from "@/mixins/cancellation";
import LoaderWidget from "@/components/util/LoaderWidget";

/* vue-echarts */
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { HeatmapChart } from "echarts/charts";
import {
  GridComponent,
  MarkLineComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import { mapState } from "vuex";
import IdTranslation from "@/libs/id-translation";
import uniqueMapping from "@/libs/unique-mapping";

use([
  CanvasRenderer,
  TooltipComponent,
  HeatmapChart,
  GridComponent,
  MarkLineComponent,
  VisualMapComponent,
]);
/* ~vue-echarts */

export default {
  name: "CoverageMap",

  mixins: [cancellation],

  components: { VChart, LoaderWidget },

  props: {
    reportTypeId: {
      type: Number,
      required: true,
    },
    // does the reportTypeId belong to a real report type
    // (if false, it is report view)
    rawReportType: { type: Boolean, default: false },
    organizationId: {
      type: Number,
      required: false,
    },
    platformId: {
      type: Number,
      required: false,
    },
    titleId: {
      type: Number,
      required: false,
    },
    startMonth: {
      type: String,
      required: false,
    },
    endMonth: {
      type: String,
      required: false,
    },
    rows: {
      type: String,
      default: "organization",
    },
    cols: {
      type: String,
      default: "date",
    },
    sortByCoverage: {
      type: Boolean,
      default: false,
    },
  },

  data() {
    return {
      coverageData: [],
      sumsByRow: new Map(),
      loading: false,
      platformIdMap: {},
    };
  },

  computed: {
    ...mapState({ organizations: "organizations", lang: "appLanguage" }),
    height() {
      return this.yValues.length * 20 + 200;
    },
    yValues() {
      if (this.sortByCoverage) {
        let out = [...this.sumsByRow.entries()];
        out.sort((a, b) => {
          const diff =
            b[1].ib_count / b[1].ib_max - a[1].ib_count / a[1].ib_max;
          if (diff === 0) {
            // if score is the same, sort by name
            return b[0].localeCompare(a[0]);
          }
          return diff;
        });
        return out.map((item) => item[0].toString());
      }
      // sort by name
      return [
        ...new Set(this.coverageData.map((item) => item[this.rows])),
      ].sort((a, b) => b.localeCompare(a));
    },
    xValues() {
      return [
        ...new Set(this.coverageData.map((item) => item[this.cols])),
      ].sort();
    },
    yValuesWidth() {
      const maxLen = Math.max(
        ...this.yValues.map((item) => item.toString().length)
      );
      return maxLen * 5 + 20;
    },
    xAxis() {
      return {
        type: "category",
        axisLabel: {
          rotate: 90,
          fontSize: this.xValues.length > 32 ? 10 : 12,
        },
        data: this.xValues,
        zvalue: 10,
      };
    },
    yAxis() {
      return {
        type: "category",
        splitArea: {
          show: true,
        },
        axisLabel: {
          width: Math.min(300, this.yValuesWidth),
          fontSize: 10,
          overflow: "truncate",
        },
        data: this.yValues,
      };
    },
    firstCompleteYValue() {
      // index of the first row which has 100% coverage
      return (
        this.yValues.findIndex(
          (item) =>
            this.sumsByRow.get(item).ib_count < this.sumsByRow.get(item).ib_max
        ) - 1
      );
    },
    option() {
      let markline = {};
      if (this.sortByCoverage && this.firstCompleteYValue > 0) {
        markline = {
          silent: true,
          data: [
            [
              {
                yAxis: this.yValues[this.firstCompleteYValue],
                xAxis: this.xValues[Math.round(this.xValues.length / 2)],
                symbol: "rect",
                symbolSize: [50, 2],
                label: {
                  formatter: this.$t("only_good_below"),
                  position: "start",
                },
              },
              {
                yAxis:
                  this.yValues[
                    this.firstCompleteYValue > 3
                      ? this.firstCompleteYValue - 3
                      : 0
                  ],
                xAxis: this.xValues[Math.round(this.xValues.length / 2)],
              },
            ],
          ],
          lineStyle: {
            color: "#252525",
            width: 2,
            type: "solid",
          },
        };
      }
      return {
        xAxis: [{ ...this.xAxis }, { ...this.xAxis, position: "top" }],
        yAxis: this.yAxis,
        grid: {
          top: 100,
          bottom: 100,
          left: this.yValuesWidth,
          right: 20,
        },
        series: [
          {
            type: "heatmap",
            data: this.coverageData.map((item) => [
              item[this.cols],
              item[this.rows].toString(),
              item.ratio * 100,
            ]),
            markLine: markline,
          },
        ],
        visualMap: {
          min: 0,
          max: 100,
          inRange: {
            color: ["#ffcccc", "#ccffcc"],
          },
          show: false,
        },
        tooltip: {
          formatter: (item) =>
            `${item.value[0]} ~ ${
              item.value[1]
            }<br><strong>${item.value[2].toFixed(1)} %</strong>`,
        },
      };
    },
    splitByOrg() {
      return this.rows === "organization" || this.cols === "organization";
    },
    splitByPlatform() {
      return this.rows === "platform" || this.cols === "platform";
    },
    dataUrl() {
      let params = {
        start_date: this.startMonth,
        end_date: this.endMonth,
      };
      // the reportTypeId can be either of report type or of report view
      if (this.rawReportType) {
        params["report_type"] = this.reportTypeId;
      } else {
        params["report_view"] = this.reportTypeId;
      }
      if (this.platformId) {
        params["platform"] = this.platformId;
      }
      if (this.titleId) {
        params["title"] = this.titleId;
      }
      if (this.organizationId) {
        params["organization"] = this.organizationId;
      }
      if (this.splitByOrg) {
        params["split_by_org"] = true;
      }
      if (this.splitByPlatform) {
        params["split_by_platform"] = true;
      }
      if (this.splitByOrg && this.splitByPlatform) {
        params["split_by_date"] = false;
      }
      return this.$router.resolve({
        path: "/api/import-batch/data-coverage/",
        query: params,
      }).href;
    },
  },

  methods: {
    async loadCoverageData() {
      this.loading = true;
      const { response, error } = await this.http({
        url: this.dataUrl,
      });
      if (!error) {
        this.coverageData = response.data;
        if (this.splitByOrg) {
          this.coverageData.forEach((item) => {
            const org = this.organizations[item.organization_id];
            item.organization = org[`name_${this.lang}`] || org.name;
          });
        }
        if (this.splitByPlatform) {
          // we need to remap the ids to names, but we have a mechanism for that
          let platformIds = [
            ...new Set(this.coverageData.map((item) => item.platform_id)),
          ];
          let trans = new IdTranslation("/api/platform/");
          await trans.prepareTranslation(platformIds);
          // because platforms are not guaranteed to have unique names, we need to
          // make sure that we have unique names
          let mapping = {};
          this.coverageData.forEach((item) => {
            mapping[item.platform_id] = trans.translateKeyToString(
              item.platform_id
            );
          });
          this.platformIdMap = uniqueMapping(mapping);
          this.coverageData.forEach((item) => {
            item.platform = this.platformIdMap[item.platform_id];
          });
        }
        // prepare sums by rows
        let keyToSum = new Map();
        this.coverageData.forEach((item) => {
          const itemName = item[this.rows];
          let rec = keyToSum.get(itemName) || { ib_count: 0, ib_max: 0 };
          rec.ib_count += item.ib_count;
          rec.ib_max += item.ib_max;
          keyToSum.set(itemName, rec);
        });
        this.sumsByRow = keyToSum;
      } else {
        this.coverageData = [];
      }
      this.loading = false;
    },
    onClick(event) {
      let out = { [this.rows]: event.value[1], [this.cols]: event.value[0] };
      if (out.platform) {
        out.platformId = Object.keys(this.platformIdMap).find(
          (key) => this.platformIdMap[key] === out.platform
        );
      }
      this.$emit("click", out);
    },
    refresh() {
      this.loadCoverageData();
    },
  },

  mounted() {
    this.loadCoverageData();
  },

  watch: {
    dataUrl() {
      this.loadCoverageData();
    },
  },
};
</script>

<style scoped></style>
