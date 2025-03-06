<i18n lang="yaml">
en:
  chart_height: Chart height
cs:
  chart_height: Výška grafu
</i18n>

<template>
  <v-container fluid>
    <v-row no-gutters>
      <v-col cols="auto">
        <slot></slot>
      </v-col>
      <v-spacer></v-spacer>
      <v-col :cols="12" :sm="8" :lg="5" :xl="3" :md="7" class="pt-1">
        <v-slider
          :max="maxHeight"
          :min="minHeight"
          v-model="height"
          :label="$t('chart_height')"
          density="compact"
          hide-details
          thumb-label
          color="primary"
        >
          <template v-slot:thumb-label="{ modelValue }">
            <span
              v-text="Math.round((100 * modelValue) / autoHeight) + '%'"
            ></span>
          </template>
        </v-slider>
      </v-col>
      <v-col cols="auto">
        <v-btn @click="height = autoHeight" dark color="primary">
          <v-icon size="small">fa fa-redo-alt</v-icon>
        </v-btn>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col :cols="12">
        <LoaderWidget v-if="loading"></LoaderWidget>
        <div v-else :style="{ height: height + 'px' }">
          <v-chart
            ref="chart"
            :key="height"
            :option="option"
            autoresize
          ></v-chart>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import LoaderWidget from "@/components/util/LoaderWidget";
import cancellation from "@/mixins/cancellation";
import percentile from "percentile";
import * as echarts from "echarts";

/* vue-echarts */
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { HeatmapChart } from "echarts/charts";
import {
  TooltipComponent,
  GridComponent,
  VisualMapComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import { formatInteger } from "@/libs/numbers";
use([
  CanvasRenderer,
  TooltipComponent,
  HeatmapChart,
  GridComponent,
  VisualMapComponent,
]);
/* ~vue-echarts */

export default {
  name: "OrganizationPlatformInterestHeatmap",

  mixins: [cancellation],

  components: {
    LoaderWidget,
    VChart,
  },
  data() {
    return {
      dataRaw: [],
      loading: false,
      primaryDim: "platform",
      secondaryDim: "organization",
      height: 200,
    };
  },
  computed: {
    ...mapGetters({
      dateRangeStart: "dateRangeStartText",
      dateRangeEnd: "dateRangeEndText",
    }),
    ...mapState("interest", ["interestReportType"]),
    request() {
      return this.reportTypeId
        ? {
            url: `/api/chart-data-raw/${this.reportTypeId}/`,
            params: {
              end: this.dateRangeEnd,
              start: this.dateRangeStart,
              prim_dim: this.primaryDim,
              sec_dim: this.secondaryDim,
            },
          }
        : null;
    },
    reportTypeId() {
      return this.interestReportType ? this.interestReportType.pk : null;
    },
    xAxis() {
      return {
        type: "category",
        axisLabel: {
          rotate: 90,
          fontSize: 10,
        },
        splitArea: {
          show: true,
        },
        data: [
          ...new Set(this.dataRaw.map((item) => item[this.primaryDim])),
        ].sort(),
      };
    },
    yValues() {
      return [
        ...new Set(this.dataRaw.map((item) => item[this.secondaryDim])),
      ].sort((a, b) => -a.localeCompare(b));
    },
    yAxis() {
      return {
        type: "category",
        splitArea: {
          show: true,
        },
        data: this.yValues,
        axisLabel: {
          fontSize: 10,
          overflow: "truncate",
        },
      };
    },
    option() {
      return {
        xAxis: [{ ...this.xAxis }, { ...this.xAxis, position: "top" }],
        yAxis: this.yAxis,
        grid: {
          top: 150,
          bottom: 200,
          left: this.yValuesWidth,
          right: 20,
        },
        series: [
          {
            type: "heatmap",
            data: this.dataRaw.map((item) => [
              item[this.primaryDim],
              item[this.secondaryDim],
              item.count || 0,
            ]),
          },
        ],
        visualMap: {
          min: 0,
          max: this.maxRangeValue,
          calculable: true,
          orient: "horizontal",
          left: "center",
          bottom: "bottom",
          formatter: (value) => formatInteger(value),
        },
        tooltip: {
          formatter: (item) =>
            `${item.value[0]} ~ ${item.value[1]}<br><strong>${formatInteger(
              item.value[2],
            )}</strong>`,
        },
      };
    },
    autoHeight() {
      const primDimUniqueValues = new Set(
        this.dataRaw.map((item) => item[this.secondaryDim]),
      );
      return this.dataRaw.length > 0
        ? primDimUniqueValues.size * 20 + 350
        : 600;
    },
    minHeight() {
      return 200;
    },
    maxHeight() {
      return this.autoHeight * 1.25;
    },
    maxRangeValue() {
      // don't use max, as there are typically outliers which make the rest
      // of the values too small. Rather use a high percentile which gives better
      // visual output
      const counts = this.dataRaw.map((item) => item.count);
      return counts.length > 0 ? percentile(97, counts) : 0;
    },
    yValuesWidth() {
      const maxLen = Math.max(
        ...this.yValues.map((item) => item.toString().length),
      );
      return maxLen * 5 + 20;
    },
  },
  methods: {
    ...mapActions("interest", ["fetchInterestReportType"]),
    async fetchData() {
      if (!this.request) {
        return;
      }

      this.loading = true;
      const { response } = await this.http(this.request);
      this.loading = false;

      if (response) {
        this.dataRaw = response.data.data;
        this.height = this.autoHeight;
      }
    },
  },
  mounted() {
    this.fetchInterestReportType(this._cid);
  },
  activated() {
    this.fetchData();
  },
  watch: {
    request: "fetchData",
  },
};
</script>
