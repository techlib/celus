<i18n lang="yaml">
en:
  data_availability_curve: "Data availability curve"
  days_from_month_start: "Days from month start"
  probability: "Probability"
  this_month_so_far: "This month so far. Probability of data availability is {n} %."

cs:
  data_availability_curve: "Křivka dostupnosti dat"
  days_from_month_start: "Dny od začátku měsíce"
  probability: "Pravděpodobnost"
  this_month_so_far: "Tento měsíc doposud. Pravděpodobnost dostupnosti dat je {n} %."
</i18n>

<template>
  <div :style="{ height: height }">
    <v-chart :option="option" autoresize />
  </div>
</template>

<script>
import cancellation from "@/mixins/cancellation";

import LoaderWidget from "@/components/util/LoaderWidget";

/* vue-echarts */
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, ScatterChart } from "echarts/charts";
import {
  TooltipComponent,
  LegendComponent,
  MarkAreaComponent,
  TitleComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import { getDayForProba, getProba } from "@/libs/curve";
use([
  CanvasRenderer,
  TooltipComponent,
  LegendComponent,
  LineChart,
  ScatterChart,
  MarkAreaComponent,
  TitleComponent,
]);
/* ~vue-echarts */

export default {
  name: "SushiArrivalCurve",

  mixins: [cancellation],
  components: {
    VChart,
    LoaderWidget,
  },

  props: {
    stats: {
      required: true,
      type: Object,
    },
    showTitle: {
      default: true,
      type: Boolean,
    },
    highlightProbas: {
      // will show markers at specific probabilities - to be used for planned
      // attempt highlighting
      default: () => [],
      type: Array,
    },
  },

  data() {
    return {
      height: "370px",
    };
  },

  computed: {
    loading() {
      return this.loadingCredentials || this.loadingStats;
    },
    probabs() {
      return this.stats.probabs.map((probab) => Math.round(probab * 100));
    },
    curve() {
      return this.stats.curve;
    },
    dayOfMonth() {
      const date = new Date();
      return date.getDate() + date.getHours() / 24 - 1; // start from 0
    },
    curveData() {
      return this.curve.map((point, index) => {
        return {
          value: [Math.round(100 * point) / 100, this.probabs[index]],
          name: `${this.probabs[index]} %: ${Math.round(10 * point) / 10} days`,
          label: {
            show: true,
            position: "top",
            formatter: "{b}",
            fontSize: 10,
          },
        };
      });
    },
    option() {
      let out = {
        title: {
          text: this.$t("data_availability_curve"),
          show: true,
          textAlign: "center",
          left: "center",
          textStyle: {
            fontFamily: "Roboto",
          },
        },
        xAxis: {
          min: 0,
          name: this.$t("days_from_month_start"),
          nameLocation: "center",
          nameGap: 25,
        },
        yAxis: {
          name: this.$t("probability"),
          nameLocation: "center",
          nameGap: 60,
          axisLabel: {
            formatter: "{value} %",
          },
        },
        series: [
          {
            type: "scatter",
            data: this.curveData,
            smooth: false,
            id: "proba",
            z: 1,
            markLine: {},
            markArea: {
              label: {
                show: false,
              },
              emphasis: {
                disabled: false,
                itemStyle: {
                  color: "rgba(198,255,211,0.4)",
                },
              },
              itemStyle: {
                color: "rgba(198,255,198,0.25)",
              },
              data: [
                [
                  {
                    name: this.$tc(
                      "this_month_so_far",

                      Math.round(1000 * getProba(this.stats, this.dayOfMonth)) /
                        10
                    ),
                    xAxis: 0,
                  },
                  {
                    xAxis: this.dayOfMonth,
                  },
                ],
              ],
            },
          },
          { type: "line", data: this.curveData, symbol: "none", z: 0 },
        ],
        legend: {},
        tooltip: {
          formatter: "{b}",
        },
      };
      if (!this.showTitle) {
        delete out.title;
      }
      if (this.highlightProbas.length > 0) {
        out.series[0].markLine.data = [];
        let i = 1;
        for (let proba of this.highlightProbas) {
          let day = getDayForProba(this.stats, proba);
          out.series[0].markLine.data.push([
            {
              name: `Attempt #${i}: ${100 * proba} %`,
              xAxis: day,
              label: {
                formatter: `Attempt #${i}`,
                position: "start",
                color: "rgba(180,120,0,0.8)",
              },
              itemStyle: {
                color: "rgba(180,120,0,0.8)",
              },
              coord: [day, 0],
            },
            { coord: [day, 100 * proba] },
          ]);
          i++;
        }
      }
      return out;
    },
  },
};
</script>

<style scoped></style>
