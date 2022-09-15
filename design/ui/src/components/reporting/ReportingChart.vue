<i18n lang="yaml" src="../../locales/charts.yaml"></i18n>

<template>
  <v-chart
    :option="option"
    :style="{ height: height }"
    :update-options="{
      replaceMerge: ['xAxis', 'yAxis', 'series'],
    }"
    autoresize
  >
  </v-chart>
</template>
<script>
import { mapActions } from "vuex";
import cancellation from "@/mixins/cancellation";
import { DEFAULT_VCHARTS_COLORS } from "@/libs/charts";

/* vue-echarts */
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, LineChart } from "echarts/charts";
import {
  DatasetComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  ToolboxComponent,
  TooltipComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import { tagText } from "@/libs/tags";

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
]);
/* ~vue-echarts */

export default {
  name: "ReportingChart",
  mixins: [cancellation],
  components: {
    VChart,
  },
  props: {
    type: {
      type: String,
      default: "histogram",
    },
    data: {
      required: true,
    },
    series: {
      type: Object,
      required: true,
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
    maxLabelLength: {
      default: 50,
      type: Number,
    },
    primaryDimension: {
      type: String,
      required: true,
    },
    secondaryDimension: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      doStack: this.stack,
    };
  },
  computed: {
    displayData() {
      // titles may have the same name but differ in isbn, etc.
      // echarts does not handle this well, so we need to make sure that
      // each x-axis label is unique
      let keyToCount = new Map();
      return this.data.map((item) => {
        let newItem = Object.fromEntries(
          Object.keys(this.series).map((k) => [k, item[k]])
        );

        let key = item[this.shownPrimaryDimension];
        if (this.shownPrimaryDimension === "tag" && typeof key === "object") {
          key = tagText(key);
        }
        let count = keyToCount.get(key) || 0;
        if (count > 0) {
          newItem[this.shownPrimaryDimension] = `${key} #${count + 1}`;
        } else {
          newItem[this.shownPrimaryDimension] = key;
        }
        keyToCount.set(key, count + 1);
        return newItem;
      });
    },
    tagToColor() {
      if (this.shownPrimaryDimension === "tag") {
        return Object.fromEntries(
          this.data.map((item) => [
            tagText(item.tag),
            item?.tag?.bg_color || "#666666",
          ])
        );
      } else {
        return {};
      }
    },
    xAxis() {
      if (this.type === "bar") {
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
            // map tags to colors
            color: (value) =>
              this.shownPrimaryDimension === "tag"
                ? this.tagToColor[value]
                : "#000000",
          },
        };
      } else {
        return {
          type: "value",
        };
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
          magicType: {
            show: true,
            title: this.$t("stack"),
            type: ["stack"],
          },
        },
      };
    },
    dataZoom() {
      if (this.zoom) {
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
    shownPrimaryDimension() {
      return this.primaryDimension;
    },
    shownSecondaryDimension() {
      return this.secondaryDimension;
    },
    // new stuff for vue-echarts starts here
    option() {
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
        series: Object.entries(this.series).map(([key, value]) => ({
          id: key,
          name: value,
          type: "bar",
          stack: this.doStack ? "all" : key,
        })),
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
      };
    },
    xValues() {
      let values = this.displayData.map(
        (item) => item[this.shownPrimaryDimension]
      );
      if (this.type === "bar") {
        // to show the values in the same order as in the data table
        values = values.reverse();
      }
      return values;
    },
    seriesNames() {
      return Object.keys(this.series);
    },
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
  },

  watch: {
    stack() {
      this.doStack = this.stack;
    },
  },
};
</script>

<style scoped lang="scss"></style>
