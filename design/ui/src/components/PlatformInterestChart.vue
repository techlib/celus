<i18n lang="yaml" src="@/locales/charts.yaml"></i18n>

<template>
  <v-container>
    <v-row>
      <v-col cols="auto">
        <v-checkbox
          v-model="logScale"
          :label="$t('chart.log_scale')"
          class="mt-1 ml-4"
        ></v-checkbox>
      </v-col>
      <v-spacer></v-spacer>
      <v-col cols="auto">
        <slot></slot>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col :style="{ height: height }">
        <v-chart :option="option" autoresize />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { mapState } from "vuex";
import { DEFAULT_VCHARTS_COLORS } from "@/libs/charts";

/* vue-echarts */
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart } from "echarts/charts";
import {
  TooltipComponent,
  LegendComponent,
  GridComponent,
  ToolboxComponent,
  DataZoomComponent,
  DatasetComponent,
} from "echarts/components";
import VChart from "vue-echarts";

use([
  CanvasRenderer,
  BarChart,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  ToolboxComponent,
  DataZoomComponent,
  DatasetComponent,
]);
/* ~vue-echarts */

export default {
  name: "PlatformInterestChart",
  components: { VChart },
  props: {
    platforms: { type: Array, required: true },
  },
  data() {
    return {
      logScale: false,
    };
  },
  computed: {
    ...mapState({
      interestGroups: (state) => state.interest.interestGroups,
    }),
    option() {
      return {
        grid: { left: "25%" },
        xAxis: { type: this.logScale ? "log" : "value" },
        yAxis: {
          type: "category",
          axisLabel: {
            width: 250,
            fontSize: 10,
            overflow: "truncate",
          },
        },
        dataset: {
          source: this.rows,
          dimensions: this.columns,
        },
        series: this.interestGroups.map((series, index) => ({
          id: series.pk,
          name: series.name,
          type: "bar",
          stack: !this.logScale,
        })),
        tooltip: {
          trigger: "axis",
          axisPointer: {
            type: "shadow",
          },
        },
        toolbox: this.toolbox,
        dataZoom: {},
        legend: {
          // checkmarks as icons for the series
          icon: "path://M 592,480 H 240 c -26.51,0 -48,-21.49 -48,-48 V 80 c 0,-26.51 21.49,-48 48,-48 h 352 c 26.51,0 48,21.49 48,48 v 352 c 0,26.51 -21.49,48 -48,48 z m -204.686,-98.059 184,-184 c 6.248,-6.248 6.248,-16.379 0,-22.627 l -22.627,-22.627 c -6.248,-6.248 -16.379,-6.249 -22.628,0 L 376,302.745 305.941,232.686 c -6.248,-6.248 -16.379,-6.248 -22.628,0 l -22.627,22.627 c -6.248,6.248 -6.248,16.379 0,22.627 l 104,104 c 6.249,6.25 16.379,6.25 22.628,0 z",
          itemWidth: 16,
          itemGap: 16,
          itemHeight: 16,
        },
        color: DEFAULT_VCHARTS_COLORS,
      };
    },
    columns() {
      return ["name", ...this.interestGroups.map((ig) => ig.short_name)];
    },
    rows() {
      let rows = this.platforms.map((platform) => {
        let interests = { ...platform.interests };
        // we have to remove 0 values from log-scale view
        if (this.logScale) {
          for (let key of Object.keys(interests)) {
            if (interests[key] === 0) {
              interests[key] = null;
            }
          }
        }
        return { name: platform.name, ...interests };
      });
      rows.reverse();
      return rows;
    },
    height() {
      return 160 + this.platforms.length * 18 + "px";
    },
    toolbox() {
      return {
        feature: {
          saveAsImage: {
            show: true,
            title: this.$t("chart.toolbox.save_as_image"),
            excludeComponents: ["toolbox", "dataZoom"],
          },
        },
      };
    },
  },
};
</script>

<style scoped></style>
