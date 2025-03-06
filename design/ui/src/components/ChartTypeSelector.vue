<i18n lang="yaml" src="@/locales/charts.yaml"></i18n>

<template>
  <v-btn-toggle
    v-if="widget === 'buttons'"
    v-model="chartTypeIndex"
    mandatory="force"
    class="flex-wrap"
    density="default"
    variant="outlined"
  >
    <v-btn
      v-for="(chartType, index) in chartTypes"
      text
      :key="chartType.pk"
      :value="index"
    >
      <v-tooltip location="bottom" v-if="chartType.desc">
        <template v-slot:activator="{ props }">
          <span v-bind="props">{{ chartType.name }}</span>
        </template>
        <span>{{ chartType.desc }}</span>
      </v-tooltip>
      <span v-else>{{ chartType.name }}</span>
    </v-btn>
  </v-btn-toggle>
  <v-select
    v-else
    :items="chartTypesFinal"
    item-title="name"
    v-model="chartTypeIndex"
    :label="$t('available_charts')"
    item-value="index"
    variant="outlined"
    density="compact"
  >
    <template v-slot:item="{ item, props }">
      <v-list-item v-bind="props">
        <v-list-item-subtitle v-if="item.raw.desc">
          {{ item.raw.desc }}
        </v-list-item-subtitle>
      </v-list-item>
    </template>
  </v-select>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";
import axios from "axios";

export default {
  name: "ChartTypeSelector",
  props: {
    reportType: { required: true },
    modelValue: { required: false, default: null }, // the selected chart type
    scope: { required: false, default: "" },
    widget: { default: "select" },
  },
  data() {
    return {
      chartTypes: [],
      chartTypeIndex: null,
    };
  },
  computed: {
    ...mapGetters({
      dateRangeStartText: "dateRangeStartText",
      dateRangeEndText: "dateRangeEndText",
    }),
    ...mapState({
      selectedOrganizationId: "selectedOrganizationId",
    }),
    selectedChartType() {
      return this.chartTypes[this.chartTypeIndex];
    },
    chartTypesFinal() {
      return this.chartTypes.map((item, index) => {
        item.index = index;
        return item;
      });
    },
    chartsUrl() {
      const rvid = this.reportType.is_proxy ? -1 : this.reportType.pk;
      return `/api/report-data-view/${rvid}/chart-definitions/`;
    },
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadChartTypes() {
      if (this.reportType !== null) {
        try {
          let response = await axios.get(this.chartsUrl);
          this.chartTypes = response.data.filter(
            (item) => item.scope === "" || item.scope === this.scope,
          );
          if (this.chartTypes.length > 0) {
            this.chartTypeIndex = 0;
          } else {
            this.chartTypeIndex = null;
          }
        } catch (error) {
          this.showSnackbar({
            content: "Error loading chart types: " + error,
            color: "error",
          });
        }
      } else {
        this.chartTypes = [];
        this.chartTypeIndex = null;
      }
    },
  },
  watch: {
    chartTypeIndex() {
      this.$emit("update:modelValue", this.selectedChartType);
    },
    reportType() {
      this.chartTypes = [];
      this.chartTypeIndex = null;
      this.loadChartTypes();
    },
  },
  mounted() {
    this.loadChartTypes();
  },
};
</script>

<style scoped></style>
