<i18n src="@/locales/common.yaml" lang="yaml"></i18n>

<template>
  <div>
    <table class="map">
      <tr>
        <th></th>
        <th
          v-for="[chpk, chart] of charts.entries()"
          :key="'chart-' + chpk"
          class="rotated"
        >
          <div>
            <span>{{ chart.name }}</span>
          </div>
        </th>
      </tr>
      <tr v-for="[vpk, reportView] of reportViews.entries()" :key="vpk">
        <th class="text-right pr-3">{{ reportView.name }}</th>
        <td
          v-for="[chpk, chart] of charts.entries()"
          :key="vpk + '-' + chpk"
          class="text-center"
        >
          <div v-if="reportViewToChart.has(`${vpk}-${chpk}`)">
            <div class="position" @click="activateLinkEdit(vpk, chpk)">
              {{ reportViewToChart.get(`${vpk}-${chpk}`).position }}
            </div>
          </div>
          <span v-else>
            <span @click="addLink(vpk, chpk)" class="popping">+</span>
          </span>
        </td>
      </tr>
      <tr>
        <th></th>
        <th
          v-for="[chpk, chart] of charts.entries()"
          :key="'b-chart-' + chpk"
          class="rotated-down"
        >
          <div>
            <span>{{ chart.name }}</span>
          </div>
        </th>
      </tr>
    </table>

    <v-dialog v-model="showEditDialog" max-width="1000px">
      <v-card>
        <v-card-title>Edit setting</v-card-title>
        <v-card-text>
          <table>
            <tr>
              <th class="text-left pr-3">{{ $t("labels.report_view") }}:</th>
              <td>{{ editedReportView ? editedReportView.name : "" }}</td>
            </tr>
            <tr>
              <th class="text-left pr-3">{{ $t("labels.chart") }}:</th>
              <td>{{ editedChart ? editedChart.name : "" }}</td>
            </tr>
          </table>

          <v-text-field
            type="number"
            v-model="editedPosition"
            :label="$t('labels.position')"
            class="pt-8"
          ></v-text-field>

          <CounterChartSet
            :fixed-chart="editedChart"
            :fixed-report-view="editedReportView"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showEditDialog = false">{{
            $t("actions.close")
          }}</v-btn>
          <v-btn
            @click="
              storeReportViewToChart(
                editedReportView.pk,
                editedChart.pk,
                editedPosition
              );
              showEditDialog = false;
            "
            :disabled="forbiddenPositions.has(Number.parseInt(editedPosition))"
            color="success"
            >{{ $t("actions.save") }}</v-btn
          >
          <v-btn
            @click="
              removeReportViewToChart(editedReportView.pk, editedChart.pk);
              showEditDialog = false;
            "
            color="error"
          >
            {{ $t("actions.delete") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import axios from "axios";
import { mapActions } from "vuex";
import CounterChartSet from "@/components/charts/CounterChartSet";

export default {
  name: "ReportViewToChartManagementWidget",
  components: { CounterChartSet },
  data() {
    return {
      reportViewToChart: new Map(),
      reportViews: new Map(),
      charts: new Map(),
      reportViewToChartEndpointURL: "/api/report-view-to-chart/",
      showEditDialog: false,
      editedReportView: null,
      editedChart: null,
      editedPosition: 0,
      forbiddenPositions: new Set(),
    };
  },

  methods: {
    ...mapActions({
      showSnackbar: "showSnackbar",
    }),
    async fetchReportViewToChartData() {
      try {
        let result = await axios.get(this.reportViewToChartEndpointURL);
        this.reportViewToChart = new Map();
        for (let rec of result.data) {
          this.reportViewToChart.set(
            `${rec.report_data_view}-${rec.chart_definition}`,
            rec
          );
        }
      } catch (error) {
        this.showSnackbar({
          content: "Could not load report view to chart mappings: " + error,
          color: "error",
        });
      }
    },
    async fetchReportViewData() {
      try {
        let result = await axios.get("/api/report-view/");
        this.reportViews = new Map();
        for (let item of result.data) {
          this.reportViews.set(item.pk, item);
        }
      } catch (error) {
        this.showSnackbar({
          content: "Could not load report views: " + error,
          color: "error",
        });
      }
    },
    async fetchChartDefinitionData() {
      try {
        let result = await axios.get("/api/chart-definition/");
        this.charts = new Map();
        for (let item of result.data) {
          this.charts.set(item.pk, item);
        }
      } catch (error) {
        this.showSnackbar({
          content: "Could not load chart definitions: " + error,
          color: "error",
        });
      }
    },
    async storeReportViewToChart(viewId, chartId, position) {
      let key = `${viewId}-${chartId}`;
      position = Number.parseInt(position);
      if (this.reportViewToChart.has(key)) {
        // this object is already in the database - just patch it
        let link = this.reportViewToChart.get(key);
        try {
          await axios.patch(this.reportViewToChartEndpointURL + link.pk + "/", {
            position: position,
          });
          link.position = position;
          // we need to create a new Map because Vue cannot observe internal changes in Maps
          this.reportViewToChart = new Map(this.reportViewToChart);
        } catch (error) {
          this.showSnackbar({
            content: "Could not save change to existing link: " + error,
            color: "error",
          });
        }
      } else {
        // we need to create a new object
        try {
          let resp = await axios.post(this.reportViewToChartEndpointURL, {
            chart_definition: chartId,
            report_data_view: viewId,
            position: position,
          });
          // we create a new Map instead of just modifying the old one, because Vue
          // does not (yet) support observing Maps :/
          this.reportViewToChart = new Map(
            this.reportViewToChart.set(
              `${resp.data.report_data_view}-${resp.data.chart_definition}`,
              resp.data
            )
          );
        } catch (error) {
          this.showSnackbar({
            content: "Could not create a new link: " + error,
            color: "error",
          });
        }
      }
    },
    async removeReportViewToChart(viewId, chartId) {
      let key = `${viewId}-${chartId}`;
      if (this.reportViewToChart.has(key)) {
        // this object is already in the database - just patch it
        let link = this.reportViewToChart.get(key);
        try {
          await axios.delete(this.reportViewToChartEndpointURL + link.pk + "/");
          this.reportViewToChart.delete(key);
          // we need to create a new Map because Vue cannot observe internal changes in Maps
          this.reportViewToChart = new Map(this.reportViewToChart);
        } catch (error) {
          this.showSnackbar({
            content: "Could not delete existing link: " + error,
            color: "error",
          });
        }
      } else {
        console.warn("Cannot delete non existing object:", viewId, chartId);
      }
    },
    addLink(viewId, chartId) {
      // find a free position
      let maxPosition = Math.max(
        ...Array.from(this.reportViewToChart.values())
          .filter((item) => item.report_data_view == viewId)
          .map((item) => item.position)
      );
      if (maxPosition < 0) {
        // in case of empty array Math.max returns -Infinity, we convert it to -1 here
        maxPosition = -1;
      }
      this.storeReportViewToChart(viewId, chartId, maxPosition + 1);
    },
    activateLinkEdit(viewId, chartId) {
      this.editedReportView = this.reportViews.get(viewId);
      this.editedChart = this.charts.get(chartId);
      this.editedPosition = this.reportViewToChart.get(
        `${viewId}-${chartId}`
      ).position;
      this.forbiddenPositions = new Set(
        Array.from(this.reportViewToChart.values())
          .filter(
            (item) =>
              item.report_data_view == viewId &&
              item.position != this.editedPosition
          )
          .map((item) => item.position)
      );
      this.showEditDialog = true;
    },
  },

  mounted() {
    this.fetchReportViewData();
    this.fetchChartDefinitionData();
    this.fetchReportViewToChartData();
  },
};
</script>

<style scoped lang="scss">
table.map {
  border-collapse: collapse;

  th.rotated {
    white-space: nowrap;
    height: 260px;

    div {
      transform: translate(16px, 110px) rotate(-45deg);
      width: 30px;

      span {
        border-bottom: 1px solid #ccc;
        padding-bottom: 2px;
      }
    }
  }

  th.rotated-down {
    white-space: nowrap;
    height: 260px;

    div {
      transform: translate(3px, -128px) rotate(45deg);
      width: 30px;

      span {
        border-bottom: 1px solid #ccc;
        padding-bottom: 2px;
        padding-left: 30px;
      }
    }
  }

  td {
    border: solid 1px #ccc;
  }
}

span.popping {
  color: #eeeeee;
  display: inline-block;
  font-weight: 900;
  width: 100%;
  padding: 5px 0;

  &:hover {
    color: #333333;
    cursor: pointer;
  }
}

div.position {
  font-weight: 600;
  line-height: 1em;

  &:hover {
    font-weight: 900;
    cursor: pointer;
  }
}
</style>
