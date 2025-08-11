<i18n lang="yaml" src="@/locales/common.yaml"></i18n>

<i18n lang="yaml">
en:
  no_data: No data available
  records: "<strong>{n}</strong> record | <strong>{n}</strong> records"
  metrics: "<strong>{n}</strong> metric | <strong>{n}</strong> metrics"

cs:
  no_data: Žádná data k dispozici
  records: "<strong>{n}</strong> záznam | <strong>{n}</strong> záznamy | <strong>{n}</strong> záznamů"
  metrics: "<strong>{n}</strong> metrika | <strong>{n}</strong> metriky | <strong>{n}</strong> metrik"
</i18n>

<template>
  <div v-if="loading" class="d-flex justify-center align-center">
    <v-progress-circular indeterminate class="ma-12" color="primary" />
  </div>
  <div class="d-flex flex-column" v-else>
    <div class="d-flex flex-column mt-6 ml-10" v-if="this.heatmapData.length">
      <span class="mb-2"
        ><strong>{{ $t("labels.metric") }}: </strong
        >{{ uniqueMetrics.join(", ") }}</span
      >
      <span
        ><strong>{{ $t("labels.dimensions") }}: </strong
        >{{ uniqueDimensionsRaw.join(", ") }}</span
      >
    </div>
    <div :style="{ height: height + 'px' }">
      <v-chart :option="option" autoresize></v-chart>
    </div>
  </div>
</template>

<script>
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { HeatmapChart } from "echarts/charts";
import {
  GridComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import cancellation from "@/mixins/cancellation";

use([
  CanvasRenderer,
  TooltipComponent,
  HeatmapChart,
  GridComponent,
  MarkLineComponent,
  TitleComponent,
  VisualMapComponent,
]);

export default {
  name: "MduHeatMap",

  mixins: [cancellation],

  components: {
    VChart,
  },

  props: {
    mduId: { required: true, type: Number },
  },

  data() {
    return {
      heatmapDataRaw: [],
      uniqueMetricsRaw: [],
      uniqueDimensionsRaw: [],
      loading: false,
    };
  },
  methods: {
    async loadHeatmapData() {
      this.loading = true;
      let resp = await this.http({ url: this.heatmapQueryUrl });
      if (!resp.error && resp.response) {
        const { monthly_data, metrics, dimensions } = resp.response.data;
        this.heatmapDataRaw = monthly_data.map((item) => ({
          year: item.year,
          month: item.month - 1,
          value: item.total_value || -1,
          metricCount: item.metric_count || 0,
          recordCount: item.record_count || 0,
          hasData: item.total_value !== null,
        }));

        this.uniqueMetricsRaw = metrics;
        this.uniqueDimensionsRaw = dimensions;
      } else {
        this.heatmapDataRaw = [];
        this.uniqueMetricsRaw = [];
        this.uniqueDimensionsRaw = [];
      }
      this.loading = false;
    },
  },
  computed: {
    uniqueMetrics() {
      return this.uniqueMetricsRaw || [];
    },
    heatmapData() {
      return this.heatmapDataRaw || [];
    },
    xValues() {
      return Array.from({ length: 12 }, (_, i) => {
        return new Date(2000, i).toLocaleDateString(this.$i18n.locale, {
          month: "short",
        });
      });
    },
    yValues() {
      const years = [...new Set(this.heatmapData.map((item) => item.year))];
      return years.sort((a, b) => b - a);
    },
    yValuesWidth() {
      const maxLen = Math.max(
        ...this.yValues.map((item) => item.toString().length),
      );
      return maxLen * 5 + 20;
    },
    height() {
      return Math.max(100, this.yValues.length * 50 + 100);
    },
    maxDataValue() {
      if (!this.heatmapData.length) return 1;
      const actualValues = this.heatmapData
        .filter((item) => item.value >= 0)
        .map((item) => item.value);
      return actualValues.length ? Math.max(...actualValues) : 1;
    },
    xAxis() {
      return {
        type: "category",
        axisLabel: {
          rotate: 0,
          fontSize: this.xValues.length > 32 ? 10 : 12,
        },
        data: this.xValues,
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
          fontSize: 12,
          overflow: "truncate",
        },
        data: this.yValues,
        inverse: true,
      };
    },
    option() {
      if (!this.heatmapData.length) {
        return {
          title: {
            text: this.$t("no_data"),
            left: "center",
            top: "center",
          },
        };
      }

      const seriesData = this.heatmapData.map((item) => {
        const yearIndex = this.yValues.indexOf(item.year);
        const dataPoint = [
          item.month,
          yearIndex,
          item.value,
          item.metricCount,
          item.recordCount,
        ];
        return dataPoint;
      });

      const option = {
        xAxis: { ...this.xAxis, position: "top" },
        yAxis: this.yAxis,
        grid: {
          top: 50,
          bottom: 50,
          left: this.yValuesWidth,
          right: 20,
        },
        series: [
          {
            type: "heatmap",
            data: seriesData,
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowColor: "rgba(0, 0, 0, 0.5)",
              },
            },
          },
        ],
        visualMap: {
          type: "piecewise",
          pieces: [
            { value: -1, color: "#ffcccc" },
            { min: 0, max: 0, color: "#f0fff0" },
            { min: 0.001, max: this.maxDataValue, color: "#ccffcc" },
          ],
          show: false,
          dimension: 2,
        },
        tooltip: {
          formatter: (params) => {
            const [monthIndex, yearIndex, value, metricCount, recordCount] =
              params.value;
            const month = this.xValues[monthIndex];
            const year = this.yValues[yearIndex];

            if (value === -1) {
              return `${month} ${year}<br/><strong>${this.$t(
                "no_data",
              )}</strong>`;
            }

            const recordsText = this.$tc("records", recordCount);
            const metricText = this.$tc("metrics", metricCount);
            return `${month} ${year}<br/>${recordsText}<br/>${metricText}`;
          },
        },
      };

      return option;
    },
    heatmapQueryUrl() {
      return "/api/mdu-heatmap-data/" + this.mduId + "/";
    },
  },

  mounted() {
    this.loadHeatmapData();
  },
};
</script>
