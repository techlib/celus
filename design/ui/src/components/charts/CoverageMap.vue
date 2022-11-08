<template>
  <v-container fluid>
    <v-row no-gutters>
      <v-col :cols="12">
        <LoaderWidget v-if="loading" />
        <div
          v-else-if="coverageData.length > 0"
          :style="{ height: height + 'px' }"
        >
          <v-chart :option="option" autoresize />
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
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import { mapState } from "vuex";

use([
  CanvasRenderer,
  TooltipComponent,
  HeatmapChart,
  GridComponent,
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
  },

  data() {
    return {
      coverageData: [],
      loading: false,
    };
  },

  computed: {
    ...mapState({ organizations: "organizations", lang: "appLanguage" }),
    height() {
      return this.yValues.length * 20 + 200;
    },
    yValues() {
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
      const maxLen = Math.max(...this.yValues.map((item) => item.length));
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
    option() {
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
              item[this.rows],
              item.ratio * 100,
            ]),
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
      if (this.organizationId) {
        params["organization"] = this.organizationId;
      }
      if (this.splitByOrg) {
        params["split_by_org"] = true;
      }
      if (this.splitByPlatform) {
        params["split_by_platform"] = true;
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
          this.coverageData.forEach(
            (item) =>
              (item.organization =
                this.organizations[item.organization_id][`name_${this.lang}`])
          );
        }
      } else {
        this.coverageData = [];
      }
      this.loading = false;
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
