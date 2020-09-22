<i18n lang="yaml" src="../locales/charts.yaml"></i18n>

<template>
  <v-btn-toggle
    v-if="widget === 'buttons'"
    v-model="chartTypeIndex"
    mandatory
    class="flex-wrap"
    dense
  >
    <v-btn
      v-for="(chartType, index) in chartTypes"
      text
      :value="index"
      :key="chartType.pk"
    >
      <v-tooltip bottom v-if="chartType.desc">
        <template v-slot:activator="{ on }">
          <span v-on="on" v-text="chartType.name"></span>
        </template>
        <span>{{ chartType.desc }}</span>
      </v-tooltip>
      <span v-else v-text="chartType.name"></span>
    </v-btn>
  </v-btn-toggle>
  <v-select
    v-else
    :items="chartTypesFinal"
    item-text="name"
    v-model="chartTypeIndex"
    :label="$t('available_charts')"
    item-value="index"
    outlined
    dense
  >
    <template v-slot:item="{ item }">
      <v-list-item-content>
        <v-list-item-title v-html="item.name"></v-list-item-title>
        <v-list-item-subtitle
          v-if="item.desc"
          v-html="item.desc"
        ></v-list-item-subtitle>
      </v-list-item-content>
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
    value: { required: false, default: null }, // the selected chart type
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
  },
  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async loadChartTypes() {
      if (this.reportType !== null) {
        try {
          let response = await axios.get(
            `/api/report-data-view/${this.reportType.pk}/chart-definitions/`
          );
          this.chartTypes = response.data.filter(
            (item) => item.scope === "" || item.scope === this.scope
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
      this.$emit("input", this.selectedChartType);
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
