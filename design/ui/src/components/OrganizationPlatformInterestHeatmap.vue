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
          dense
          hide-details
        >
          <template v-slot:thumb-label="{ value }">
            <span v-text="Math.round((100 * value) / autoHeight) + '%'"></span>
          </template>
        </v-slider>
      </v-col>
      <v-col cols="auto">
        <v-btn @click="height = autoHeight" dark color="primary">
          <v-icon small>fa fa-redo-alt</v-icon>
        </v-btn>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col :cols="12">
        <LoaderWidget v-if="loading" />
        <ve-heatmap
          v-else
          :data="chartData"
          :settings="chartSettings"
          :height="`${height}px`"
          :xAxis="xAxis"
        >
        </ve-heatmap>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import VeHeatmap from "v-charts/lib/heatmap.common";
import { mapActions, mapGetters, mapState } from "vuex";
import LoaderWidget from "@/components/util/LoaderWidget";
import http from "@/libs/http";

export default {
  name: "OrganizationPlatformInterestHeatmap",

  components: {
    LoaderWidget,
    VeHeatmap,
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
    columns() {
      return this.loading ? [] : [this.primaryDim, this.secondaryDim, "count"];
    },
    chartData() {
      return {
        columns: this.columns,
        rows: this.rows,
      };
    },
    rows() {
      return this.dataRaw;
    },
    chartSettings() {
      return {
        yAxisList: [
          ...new Set(this.dataRaw.map((item) => item[this.secondaryDim])),
        ].sort((a, b) => -a.localeCompare(b)),
        xAxisList: [
          ...new Set(this.dataRaw.map((item) => item[this.primaryDim])),
        ].sort(),
      };
    },
    xAxis() {
      return {
        type: "category",
        axisLabel: {
          rotate: 90,
        },
        splitArea: {
          show: true,
        },
        data: [
          ...new Set(this.dataRaw.map((item) => item[this.primaryDim])),
        ].sort(),
      };
    },
    autoHeight() {
      const primDimUniqueValues = new Set(
        this.dataRaw.map((item) => item[this.secondaryDim])
      );
      return this.dataRaw.length > 0
        ? primDimUniqueValues.size * 18 + 250
        : 600;
    },
    minHeight() {
      return 200;
    },
    maxHeight() {
      return this.autoHeight * 1.25;
    },
  },
  methods: {
    ...mapActions("interest", ["fetchInterestReportType"]),
    async fetchData() {
      if (!this.request) return;

      this.loading = true;
      const { response } = await http(this.request);
      this.loading = false;

      if (response) {
        this.dataRaw = response.data.data;
        this.height = this.autoHeight;
      }
    },
  },
  mounted() {
    this.fetchInterestReportType();
  },
  watch: {
    request: "fetchData",
  },
};
</script>
