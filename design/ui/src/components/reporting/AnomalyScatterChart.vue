<i18n lang="yaml" src="@/locales/common.yaml"></i18n>
<template>
  <v-chart :option="option" autoresize />
</template>

<script setup lang="ts">
import { DEFAULT_VCHARTS_COLORS } from "@/libs/charts";
import type { EChartsOption, ScatterSeriesOption } from "echarts";
import { ScatterChart } from "echarts/charts";
import {
  GridComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
} from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import type { CallbackDataParams } from "echarts/types/dist/shared";
import VChart from "vue-echarts";

import { computed } from "vue";
import { useI18n } from "vue-i18n";

use([
  CanvasRenderer,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  MarkLineComponent,
  MarkAreaComponent,
]);

interface Props {
  history: Record<string, number>;
  median: number;
  lowerBound: number;
  upperBound: number;
}

const props = defineProps<Props>();

defineOptions({
  name: "AnomalyScatterChart",
});

const { t } = useI18n();

const option = computed<EChartsOption>(() => {
  const entries = Object.entries(props.history || {});
  // sort by date ascending, should not be needed, but just in case
  const points = entries.sort((a, b) =>
    a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0,
  );
  const lb = Math.max(0, Number(props.lowerBound));
  const ub = Number(props.upperBound);
  const lastIndex = points.length - 1;

  const scatterSeries: ScatterSeriesOption = {
    type: "scatter",
    symbolSize: 12,
    data: points.map((p, idx) =>
      idx === lastIndex
        ? {
            value: p,
            itemStyle: { color: DEFAULT_VCHARTS_COLORS[2] },
            symbolSize: 16,
          }
        : { value: p },
    ),
    markArea: {
      silent: true,
      itemStyle: {
        color: DEFAULT_VCHARTS_COLORS[0],
        opacity: 0.08,
      },
      data: [
        [
          { xAxis: "min", yAxis: lb },
          { xAxis: "max", yAxis: ub },
        ],
      ],
    },
    markLine: {
      symbol: ["none", "none"],
      silent: true,
      z: 10,
      label: {
        show: true,
        position: "end",
        formatter: () => `Median`,
        color: "#424242",
        fontWeight: "bold",
        backgroundColor: "rgba(255,255,255,0.75)",
        padding: [2, 4],
      },
      lineStyle: {
        color: DEFAULT_VCHARTS_COLORS[1],
        type: "dashed",
        width: 2,
      },
      data: [{ yAxis: props.median }],
    },
  };

  const option: EChartsOption = {
    animation: false,
    grid: { left: 64, right: 64, top: 32, bottom: 32 },
    color: DEFAULT_VCHARTS_COLORS,
    tooltip: {
      trigger: "item",
      formatter: (params: CallbackDataParams | CallbackDataParams[]) => {
        const p = Array.isArray(params) ? params[0] : params;
        const [d, v] = p.value as [string, number];
        return `${t("labels.date")}: ${d}<br/>${t("labels.value")}: ${Number(
          v,
        ).toLocaleString()}`;
      },
    },
    xAxis: {
      type: "time",
      axisLine: { show: true },
      axisTick: { show: true },
      axisLabel: { show: true },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      axisLine: { show: true },
      axisTick: { show: true },
      axisLabel: { show: true },
      splitLine: { show: false },
    },
    series: [scatterSeries],
  };

  return option;
});
</script>
